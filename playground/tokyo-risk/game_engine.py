"""
Tokyo Risk - ゲームエンジン
============================
- 23区の陣取り
- Maps POIデータから算出したスタッツが戦闘・移動に影響
- 自律エージェントがGemini Function Callingで行動判断
"""

import random
import json
from pathlib import Path
from typing import Optional
from ward_data import ADJACENCY, WARDS, WARD_LATLNG

# ルート移動コスト（Routes API キャッシュ）
_route_cache_file = Path(__file__).parent / "route_times_cache.json"
_ROUTE_TIMES: dict = {}
if _route_cache_file.exists():
    with open(_route_cache_file) as _f:
        _ROUTE_TIMES = json.load(_f)

def _movement_cost(from_ward: str, to_ward: str) -> int:
    """2区間の移動コスト（1〜5）。キャッシュがなければ3（デフォルト）"""
    key = "|".join(sorted([from_ward, to_ward]))
    return _ROUTE_TIMES.get(key, {}).get("movement_cost", 3)


# ============================================================
# 定数
# ============================================================
PLAYER   = "player"
AI       = "ai"
NEUTRAL  = "neutral"

STARTING_TROOPS = 3       # 初期駐留兵力
MAX_LOG_ENTRIES = 500     # ゲームログの最大保持件数

TEAM_BUDGET = 100         # チームの合計予算（ゴールド）

# 戦略要所（取得で高ボーナス）
KEY_WARDS: dict[str, int] = {
    "新宿区":  5,   # 交通の要衝
    "渋谷区":  4,
    "千代田区": 5,  # 政治の中心
    "港区":    4,
    "中央区":  3,   # 経済の中心（銀座）
    "豊島区":  3,   # 池袋
    "台東区":  2,   # 浅草・上野
    "文京区":  2,
}

# ============================================================
# ツール（武装）定義
# ============================================================
TOOLS: dict[str, dict] = {
    "rapid_move": {
        "name": "高速移動",
        "cost": 20,
        "description": "移動速度が2倍になる",
        "icon": "🏃",
        "effects": {"speed_multiplier": 2.0}
    },
    "radar": {
        "name": "偵察レーダー",
        "cost": 15,
        "description": "周辺検知範囲が2倍になる",
        "icon": "📡",
        "effects": {"radar_range": 0.10}  # デフォルト0.05 → 0.10
    },
    "attack_boost": {
        "name": "攻撃力強化",
        "cost": 25,
        "description": "攻撃ダメージが1.5倍になる",
        "icon": "⚔️",
        "effects": {"attack_multiplier": 1.5}
    },
    "shield": {
        "name": "防御シールド",
        "cost": 20,
        "description": "受けるダメージを40%軽減",
        "icon": "🛡️",
        "effects": {"defense_pct": 40}   # ダメージを40%カット
    },
    "medkit": {
        "name": "医療キット",
        "cost": 10,
        "description": "毎ターン体力を8回復",
        "icon": "💊",
        "effects": {"regen": 8}
    },
    "comm_boost": {
        "name": "通信ブースター",
        "cost": 10,
        "description": "コマンダーへの報告頻度が上がり、より正確な指示が届く",
        "icon": "📻",
        "effects": {"comm_priority": True}
    },
}


# ============================================================
# Agent エンティティ
# ============================================================
class Agent:
    """自律的に行動するAIエージェント（兵士）"""
    def __init__(self, agent_id: str, owner: str, system_prompt: str,
                 tools: Optional[list[str]] = None):
        self.id = agent_id              # "player_001" ~ "player_010", "ai_001" ~ "ai_010"
        self.owner = owner              # PLAYER or AI
        self.system_prompt = system_prompt  # ユーザーが設定した戦略プロンプト
        self.tools: list[str] = tools or []  # 装備ツールIDのリスト

        # 位置情報
        self.lat = 35.6938
        self.lng = 139.7036
        self.destination: Optional[dict] = None  # {"lat": ..., "lng": ..., "ward": "渋谷区"}
        self.speed = 0.014              # 1フレームあたりの移動量（緯度経度）- デモ用高速

        # ステータス（ツール適用前のベース値）
        self.attack = 10          # 攻撃力（ダメージ量）
        self.defense_pct = 0      # ダメージ軽減率 0-100%
        self.radar_range = 0.05   # 周辺検知範囲（度）
        self.regen = 0            # 毎tick体力回復量
        self.comm_priority = False
        self.is_alive = True      # 撃破されるとFalse

        # 状態
        self.state = "idle"             # idle, moving, attacking, defending, patrolling
        self.health = 100
        self.target_ward: Optional[str] = None  # 目標とする区

        self.last_action_time: float = 0.0  # 初回から即座に行動判断させる

        # 思考可視化
        self.thought: str = ""          # 現在の思考・行動理由
        self.thought_time: float = 0.0  # thought が設定された時刻

        # ツール効果を適用
        self._apply_tools()

    def _apply_tools(self):
        """装備ツールのボーナスをステータスに反映"""
        for tool_id in self.tools:
            tool = TOOLS.get(tool_id)
            if not tool:
                continue
            effects = tool["effects"]
            if "speed_multiplier" in effects:
                self.speed *= effects["speed_multiplier"]
            if "radar_range" in effects:
                self.radar_range = effects["radar_range"]
            if "attack_multiplier" in effects:
                self.attack = int(self.attack * effects["attack_multiplier"])
            if "defense_pct" in effects:
                self.defense_pct = min(80, self.defense_pct + effects["defense_pct"])
            if "regen" in effects:
                self.regen += effects["regen"]
            if "comm_priority" in effects:
                self.comm_priority = True

    def take_damage(self, raw_damage: int) -> int:
        """ダメージを受ける。実際のダメージ量を返す"""
        actual = max(1, int(raw_damage * (1 - self.defense_pct / 100)))
        self.health -= actual
        if self.health <= 0:
            self.health = 0
            self.is_alive = False
            self.state = "dead"
        return actual

    def update_position(self, delta_time: float = 0.1):
        """目的地に向かって移動"""
        if not self.destination or self.state != "moving":
            return

        dest_lat = self.destination["lat"]
        dest_lng = self.destination["lng"]

        # 目的地に到達したか確認
        dist = ((self.lat - dest_lat)**2 + (self.lng - dest_lng)**2)**0.5
        if dist < self.speed * 2:
            self.lat = dest_lat
            self.lng = dest_lng
            self.state = "idle"
            self.destination = None
            return

        # 目的地に向かって移動
        direction_lat = (dest_lat - self.lat) / dist
        direction_lng = (dest_lng - self.lng) / dist

        self.lat += direction_lat * self.speed
        self.lng += direction_lng * self.speed

    def set_destination(self, lat: float, lng: float, ward: Optional[str] = None):
        """目的地を設定して移動開始"""
        self.destination = {"lat": lat, "lng": lng, "ward": ward}
        self.state = "moving"
        self.target_ward = ward

    def to_dict(self):
        return {
            "id": self.id,
            "owner": self.owner,
            "lat": self.lat,
            "lng": self.lng,
            "destination": self.destination,
            "state": self.state,
            "health": self.health,
            "target_ward": self.target_ward,
            "tools": self.tools,
            "attack": self.attack,
            "defense_pct": self.defense_pct,
            "radar_range": self.radar_range,
            "regen": self.regen,
            "is_alive": self.is_alive,
            "thought": self.thought,
        }


# ============================================================
# ゲーム状態
# ============================================================
class GameState:
    def __init__(self, stats: dict[str, dict]):
        self.stats = stats          # ward_name -> {ATK, DEF, SPD, INC, REC}
        self.owner: dict[str, str] = {}     # ward_name -> PLAYER/AI/NEUTRAL
        self.troops: dict[str, int] = {}    # ward_name -> 兵力数
        self.income: dict[str, int] = {PLAYER: 10, AI: 10}  # 各ターンの収入
        self.turn = 1
        self.log: list[str] = []

        # 新規: エージェント管理
        self.agents: dict[str, Agent] = {}  # agent_id -> Agent
        self.commander_order: str = ""       # プレイヤーからエージェントへの現在の命令
        self.agent_messages: dict[str, list] = {PLAYER: [], AI: []}
        # 各エントリ: {"from": "player_001", "text": "渋谷区へ向かいます"}

        # 初期化: 全区NEUTRAL
        for w in WARDS:
            self.owner[w] = NEUTRAL
            self.troops[w] = STARTING_TROOPS

    def setup_starting_positions(self, player_ward: str, ai_ward: str):
        """プレイヤーとAIの初期領地を設定"""
        self.owner[player_ward] = PLAYER
        self.owner[ai_ward]     = AI
        self.troops[player_ward] = 5
        self.troops[ai_ward]     = 5

    def setup_agents(self, player_prompts: list[str], ai_prompts: list[str],
                     player_ward: str, ai_ward: str,
                     player_tools: Optional[list[list[str]]] = None,
                     ai_tools: Optional[list[list[str]]] = None):
        """10体ずつのエージェントを初期化

        player_tools: 各エージェントのツールIDリスト（10要素）
                      例: [["rapid_move"], ["shield", "medkit"], [], ...]
        """
        player_pos = WARD_LATLNG[player_ward]
        ai_pos = WARD_LATLNG[ai_ward]
        player_tools = player_tools or [[] for _ in range(10)]
        ai_tools = ai_tools or [[] for _ in range(10)]

        # プレイヤーのエージェント
        for i in range(10):
            agent_id = f"player_{i+1:03d}"
            prompt = player_prompts[i] if i < len(player_prompts) else player_prompts[0]
            tools = player_tools[i] if i < len(player_tools) else []
            agent = Agent(agent_id, PLAYER, prompt, tools=tools)
            agent.lat, agent.lng = player_pos[0], player_pos[1]
            self.agents[agent_id] = agent

        # AIのエージェント
        for i in range(10):
            agent_id = f"ai_{i+1:03d}"
            prompt = ai_prompts[i] if i < len(ai_prompts) else ai_prompts[0]
            tools = ai_tools[i] if i < len(ai_tools) else []
            agent = Agent(agent_id, AI, prompt, tools=tools)
            agent.lat, agent.lng = ai_pos[0], ai_pos[1]
            self.agents[agent_id] = agent

    # --------------------------------------------------------
    # スタッツ取得
    # --------------------------------------------------------
    def _log(self, msg: str) -> None:
        """ログを追記し、上限を超えた古いエントリを削除する"""
        self.log.append(msg)
        if len(self.log) > MAX_LOG_ENTRIES:
            del self.log[:len(self.log) - MAX_LOG_ENTRIES]

    # --------------------------------------------------------
    def get_stat(self, ward: str, key: str) -> int:
        return self.stats.get(ward, {}).get(key, 5)

    @property
    def player_wards(self):
        """プレイヤーが支配している区のリスト"""
        return [w for w, o in self.owner.items() if o == PLAYER]

    @property
    def ai_wards(self):
        """AIが支配している区のリスト"""
        return [w for w, o in self.owner.items() if o == AI]

    def ward_info(self, ward: str) -> dict:
        s = self.stats.get(ward, {})
        return {
            "name":  ward,
            "owner": self.owner[ward],
            "troops": self.troops[ward],
            "stats": s,
            "neighbors": ADJACENCY[ward],
        }

    # --------------------------------------------------------
    # 勝利判定
    # --------------------------------------------------------
    def check_victory(self) -> str | None:
        counts = {PLAYER: 0, AI: 0, NEUTRAL: 0}
        for o in self.owner.values():
            counts[o] += 1
        # 全23区を制圧（中立なし）かつ多い方が勝利
        if counts[NEUTRAL] == 0:
            if counts[PLAYER] > counts[AI]:
                print(f"  [VICTORY] PLAYER wins: P={counts[PLAYER]} AI={counts[AI]} N={counts[NEUTRAL]}")
                return PLAYER
            elif counts[AI] > counts[PLAYER]:
                print(f"  [VICTORY] AI wins: P={counts[PLAYER]} AI={counts[AI]} N={counts[NEUTRAL]}")
                return AI
        # 過半数（12区以上）制圧で勝利
        if counts[PLAYER] >= 12:
            print(f"  [VICTORY] PLAYER majority: P={counts[PLAYER]} AI={counts[AI]} N={counts[NEUTRAL]}")
            return PLAYER
        if counts[AI] >= 12:
            print(f"  [VICTORY] AI majority: P={counts[PLAYER]} AI={counts[AI]} N={counts[NEUTRAL]}")
            return AI
        return None

    def serialize(self) -> dict:
        """フロントエンド向けにシリアライズ"""
        player_wards = [w for w, o in self.owner.items() if o == PLAYER]
        ai_wards = [w for w, o in self.owner.items() if o == AI]

        return {
            "turn":   self.turn,
            "owner":  dict(self.owner),
            "troops": dict(self.troops),
            "income": dict(self.income),
            "log":    self.log[-10:],  # 直近10件
            "stats":  self.stats,
            "victory": self.check_victory(),
            "player_wards": player_wards,
            "ai_wards": ai_wards,
            "ward_count": {
                PLAYER:  sum(1 for o in self.owner.values() if o == PLAYER),
                AI:      sum(1 for o in self.owner.values() if o == AI),
                NEUTRAL: sum(1 for o in self.owner.values() if o == NEUTRAL),
            },
            "agents": {aid: a.to_dict() for aid, a in self.agents.items()}
        }


