"""
Tokyo Risk - FastAPI サーバー
起動: uvicorn server:app --port 8766 --reload
"""

import os
import json
import asyncio
import time
import re as _re
from pathlib import Path
import base64
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from google import genai  # noqa: E402
from google.genai import types  # noqa: E402
from ward_data import WARDS, ADJACENCY, WARD_POSITIONS, WARD_LATLNG, load_or_fetch_stats, GEMINI_MODEL  # noqa: E402
from game_engine import GameState, PLAYER, AI, NEUTRAL, TOOLS, TEAM_BUDGET, KEY_WARDS  # noqa: E402
from agent_ai import AgentAI, execute_agent_action  # noqa: E402

# ============================================================
app = FastAPI(title="Tokyo Risk API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# 静的ファイル（アバター画像など）を /static で配信
_static_dir = Path(__file__).parent / "static"
_static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# スタッツ（起動時に1回だけ取得 or キャッシュ）
print("スタッツ初期化中...")
WARD_STATS = load_or_fetch_stats(client)

# ルート移動コスト（Routes API キャッシュ）
ROUTE_CACHE_FILE = Path(__file__).parent / "route_times_cache.json"
ROUTE_TIMES: dict = {}
if ROUTE_CACHE_FILE.exists():
    with open(ROUTE_CACHE_FILE) as f:
        ROUTE_TIMES = json.load(f)
    print(f"  [routes] {len(ROUTE_TIMES)}区間のルートデータ読み込み完了")

# セッションストア
sessions: dict[str, GameState] = {}
# 会話履歴ストア（session_id -> chat_history）
chat_histories: dict[str, list] = {}
# エージェントAIループタスク
agent_tasks: dict[str, asyncio.Task] = {}
# セッション作成時刻（session_id -> unix timestamp）
session_created_at: dict[str, float] = {}

SESSION_TTL_SECONDS = 3600  # 1時間でセッションを自動削除


def _cleanup_session(session_id: str) -> None:
    """セッションに関連する全リソースを解放する"""
    if session_id in agent_tasks:
        task = agent_tasks.pop(session_id)
        if not task.done():
            task.cancel()
    # セッションのエージェントに紐づくグローバル追跡辞書も削除
    state = sessions.get(session_id)
    if state:
        for aid in list(state.agents.keys()):
            _last_combat.pop(aid, None)
            _last_regen.pop(aid, None)
            _last_sos.pop(aid, None)
    sessions.pop(session_id, None)
    chat_histories.pop(session_id, None)
    session_created_at.pop(session_id, None)

# デフォルトプロンプト
DEFAULT_PLAYER_PROMPT = """あなたは東京23区の陣取りゲームの兵士です。
目標: 敵の区を占領し、味方の支配領域を拡大する。
味方と協力し、戦略的に行動してください。"""

DEFAULT_AI_PROMPT = """あなたは東京23区の陣取りゲームのAI兵士です。
目標: プレイヤーの区を占領し、AI支配領域を拡大する。
効率的に行動し、防御と攻撃のバランスを取ってください。"""

# ============================================================
# リクエストモデル
# ============================================================
class StartRequest(BaseModel):
    player_ward: str = "新宿区"
    player_prompts: Optional[list[str]] = None        # 10個のプロンプト
    player_tools: Optional[list[list[str]]] = None    # 10体それぞれのツールIDリスト
    arch_mode: Optional[str] = "flat"                 # flat | hierarchical | squad | swarm

# ============================================================
# エンドポイント
# ============================================================
@app.post("/game/start")
async def start_game(req: StartRequest):
    import random
    session_id = f"game_{int(time.time() * 1000)}_{random.randint(1000,9999)}"
    state = GameState(WARD_STATS)

    # AI の開始位置: プレイヤーから最も遠い区
    player_pos = WARD_POSITIONS[req.player_ward]
    ai_ward = max(
        [w for w in WARDS if w != req.player_ward],
        key=lambda w: (WARD_POSITIONS[w][0] - player_pos[0])**2 + (WARD_POSITIONS[w][1] - player_pos[1])**2
    )
    state.setup_starting_positions(req.player_ward, ai_ward)

    # エージェント初期化
    player_prompts = req.player_prompts or [DEFAULT_PLAYER_PROMPT] * 10
    ai_prompts = [DEFAULT_AI_PROMPT] * 10

    # プレイヤーのツール設定を検証（予算オーバーはエラー）
    player_tools = req.player_tools or [[] for _ in range(10)]
    total_cost = sum(
        TOOLS[t]["cost"]
        for agent_tools in player_tools
        for t in agent_tools
        if t in TOOLS
    )
    if total_cost > TEAM_BUDGET:
        raise HTTPException(400, f"予算オーバー: {total_cost}G > {TEAM_BUDGET}G")

    # AIのツール配分（ランダム戦略）
    ai_tools = _build_ai_tools()

    state.setup_agents(player_prompts, ai_prompts, req.player_ward, ai_ward,
                       player_tools=player_tools, ai_tools=ai_tools)
    state.arch_mode = req.arch_mode or "flat"
    state._log(f"⚙️ アーキテクチャ: {state.arch_mode.upper()} | Gemini FC: player_001-003 | Rule-based: 004-010 + AI")

    sessions[session_id] = state
    session_created_at[session_id] = time.time()

    # 会話履歴初期化
    chat_histories[session_id] = []

    # 既存タスクがあればキャンセルしてから新しいループを起動
    if session_id in agent_tasks and not agent_tasks[session_id].done():
        agent_tasks[session_id].cancel()
    task = asyncio.create_task(run_agent_ai_loop(session_id))
    agent_tasks[session_id] = task

    return {
        "session_id": session_id,
        "player_start": req.player_ward,
        "ai_start": ai_ward,
        "game_state": state.serialize(),
    }


@app.get("/game/state/{session_id}")
def get_state(session_id: str):
    state = sessions.get(session_id)
    if not state:
        raise HTTPException(404, "セッションが見つかりません")
    return state.serialize()


@app.get("/map/data")
def get_map_data():
    """フロントエンドに23区の座標・隣接情報・スタッツを返す"""
    return {
        "wards": WARDS,
        "positions": WARD_POSITIONS,
        "latlng": WARD_LATLNG,
        "adjacency": ADJACENCY,
        "stats": WARD_STATS,
        "routes": ROUTE_TIMES,
        "key_wards": KEY_WARDS,
    }


@app.post("/command/natural")
async def natural_language_command(request: dict):
    """自然言語コマンドをエージェントへの命令として設定"""
    user_input = request.get("command")
    session_id = request.get("session_id")

    if not user_input:
        raise HTTPException(400, "コマンドを入力してください")

    if session_id not in sessions:
        raise HTTPException(404, "セッションが見つかりません")

    game_state = sessions[session_id]
    game_state.commander_order = user_input
    game_state._log(f"📡 コマンダー命令: {user_input}")

    return {
        "success": True,
        "message": f"命令を設定しました: {user_input}",
        "state": game_state.serialize()
    }


@app.post("/ai/chat")
async def chat_with_ai_commander(request: dict):
    """AIコマンダー（副官）と対話する"""
    import re
    user_message = request.get("message")
    session_id = request.get("session_id")

    if not user_message:
        raise HTTPException(400, "メッセージを入力してください")

    if session_id not in sessions:
        raise HTTPException(404, "セッションが見つかりません")

    game_state = sessions[session_id]

    if session_id not in chat_histories:
        chat_histories[session_id] = []
    chat_history = chat_histories[session_id]

    # 各エージェントの詳細状況（current_wardはAgentに存在しないためtarget_wardで代替）
    player_agent_lines = []
    for aid, agent in sorted(game_state.agents.items()):
        if agent.owner == PLAYER:
            ward = getattr(agent, "target_ward", None) or "移動中"
            hp = getattr(agent, "health", 100)
            st = getattr(agent, "state", "idle")
            alive_mark = "✓" if agent.is_alive else "✗"
            player_agent_lines.append(f"  {alive_mark} {aid}: HP{hp} [{st}] @{ward}")

    ai_agent_lines = []
    for aid, agent in sorted(game_state.agents.items()):
        if agent.owner == AI:
            ward = getattr(agent, "target_ward", None) or "移動中"
            hp = getattr(agent, "health", 100)
            st = getattr(agent, "state", "idle")
            alive_mark = "✓" if agent.is_alive else "✗"
            ai_agent_lines.append(f"  {alive_mark} {aid}: HP{hp} [{st}] @{ward}")

    player_agents_str = "\n".join(player_agent_lines) if player_agent_lines else "  なし"
    ai_agents_str = "\n".join(ai_agent_lines) if ai_agent_lines else "  なし"

    system_instruction = f"""あなたは東京23区陣取りゲーム「Tokyo Risk」のAI副司令官です。
プレイヤーを「司令官」と呼び、戦略的なアドバイスと支援を提供します。

【現在の戦況】
- ターン: {game_state.turn}
- プレイヤー支配区: {sorted(game_state.player_wards)} ({len(game_state.player_wards)}区)
- AI支配区: {sorted(game_state.ai_wards)} ({len(game_state.ai_wards)}区)
- 現在の命令: {game_state.commander_order or "なし"}

【味方エージェント状況】
{player_agents_str}

【敵エージェント状況】
{ai_agents_str}

【あなたの役割】
1. 司令官との会話から作戦意図を読み取る
2. 状況に応じて具体的な行動命令を味方エージェントに発令する
3. 危険な状況を警告し、戦略的アドバイスを提供する

【命令抽出ルール — 重要】
会話の末尾に必ず以下のいずれかを出力してください:
- 具体的な命令がある場合: [ORDER: <具体的な命令文（日本語）>]
  例: [ORDER: 新宿区と渋谷区を優先的に制圧せよ]
  例: [ORDER: 敵エージェントを包囲して撃破せよ]
  例: [ORDER: 防衛ラインを東側に構築せよ]
- 命令なし（雑談・状況確認など）: [ORDER: なし]

【口調】丁寧で軍隊的（「はい、司令官！」「了解しました」）、簡潔明瞭"""

    try:
        full_history = []
        for msg in chat_history:
            full_history.append({"role": "user", "parts": [{"text": msg["user"]}]})
            full_history.append({"role": "model", "parts": [{"text": msg["assistant"]}]})
        full_history.append({"role": "user", "parts": [{"text": user_message}]})

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=full_history,  # type: ignore[arg-type]
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.7
            )
        )

        raw_response = response.text if response.text else "応答できませんでした"

        # [ORDER: ...] タグを抽出してcommander_orderに反映
        issued_order = None
        order_match = re.search(r'\[ORDER:\s*(.+?)\]', raw_response)
        if order_match:
            extracted = order_match.group(1).strip()
            if extracted != "なし":
                issued_order = extracted
                if extracted != game_state.commander_order:
                    game_state._log(f"🎖️ [副司令官命令] {extracted}")
                game_state.commander_order = extracted

        # タグを表示テキストから除去
        display_response = re.sub(r'\s*\[ORDER:.*?\]', '', raw_response).strip()

        chat_history.append({"user": user_message, "assistant": display_response})
        if len(chat_history) > 10:
            chat_history = chat_history[-10:]
            chat_histories[session_id] = chat_history

        return {
            "success": True,
            "ai_response": display_response,
            "issued_order": issued_order,
            "state": None
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"エラーが発生しました: {str(e)}"
        }


@app.get("/ai/analysis/{session_id}")
async def get_ai_analysis(session_id: str):
    """AIによる戦況分析"""
    if session_id not in sessions:
        raise HTTPException(404, "セッションが見つかりません")

    game_state = sessions[session_id]

    # 戦況分析プロンプト
    analysis_prompt = f"""
東京23区陣取りゲーム「Tokyo Risk」の戦況を分析してください。

【現在の状況】
- ターン: {game_state.turn}
- プレイヤー支配区: {list(game_state.player_wards)} ({len(game_state.player_wards)}区)
- AI支配区: {list(game_state.ai_wards)} ({len(game_state.ai_wards)}区)

各区の兵力:
{dict(list(game_state.troops.items()))}

【分析項目】
1. **危険な区**: プレイヤーの支配区で防衛が手薄な場所（兵力が少ない、AIの隣接区が多い）
2. **攻撃チャンス**: AIの弱点（兵力が少ない区、孤立している区）
3. **戦略的要所**: 制圧すると有利になる区（複数の区に隣接、高いステータス）
4. **推奨行動**: 次のターンで取るべき行動を3つ（優先順位付き）

簡潔に、軍事報告の口調で回答してください。
"""

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=analysis_prompt,
            config=types.GenerateContentConfig(temperature=0.5)
        )

        return {
            "analysis": response.text if response.text else "分析できませんでした",
            "turn": game_state.turn
        }

    except Exception as e:
        raise HTTPException(500, f"分析エラー: {str(e)}")


@app.get("/route/{from_ward}/{to_ward}")
def get_route(from_ward: str, to_ward: str):
    """2区間のルート情報を返す"""
    # キーは辞書順でソート済み
    key = "|".join(sorted([from_ward, to_ward]))
    route_data = ROUTE_TIMES.get(key)

    if not route_data:
        # ルートデータがない場合は基本情報のみ
        return {
            "from": from_ward,
            "to": to_ward,
            "has_data": False,
            "estimated_minutes": 15
        }

    return {
        "from": from_ward,
        "to": to_ward,
        "has_data": True,
        "seconds": route_data.get("seconds", 900),
        "minutes": route_data.get("seconds", 900) // 60,
        "movement_cost": route_data.get("movement_cost", 3),
        "polyline": route_data.get("polyline", None)
    }


@app.get("/game/tools")
def get_tools():
    """利用可能なツール一覧と予算を返す"""
    return {
        "budget": TEAM_BUDGET,
        "tools": TOOLS
    }


def _build_ai_tools() -> list[list[str]]:
    """AIの予算100G内でランダムにツールを配分する"""
    import random
    tool_ids = list(TOOLS.keys())
    budget = TEAM_BUDGET
    ai_tools: list[list[str]] = [[] for _ in range(10)]

    # ランダムにツールを購入してエージェントに割り当て
    remaining = budget
    while remaining > 0:
        affordable = [t for t in tool_ids if TOOLS[t]["cost"] <= remaining]
        if not affordable:
            break
        chosen_tool = random.choice(affordable)
        chosen_agent = random.randint(0, 9)
        # 同じツールの重複を避ける
        if chosen_tool not in ai_tools[chosen_agent]:
            ai_tools[chosen_agent].append(chosen_tool)
            remaining -= TOOLS[chosen_tool]["cost"]

    return ai_tools


class CommanderOrderRequest(BaseModel):
    order: str


@app.post("/game/commander-order/{session_id}")
def set_commander_order(session_id: str, req: CommanderOrderRequest):
    """コマンダーからエージェント全体への命令を設定"""
    state = sessions.get(session_id)
    if not state:
        raise HTTPException(404, "セッションが見つかりません")
    state.commander_order = req.order
    state._log(f"📡 コマンダー命令: {req.order}")
    return {"ok": True}


@app.get("/game/agents/{session_id}")
def get_agents_state(session_id: str, since: int = 0):
    """全エージェントの現在位置・ログ・勝利判定を返す"""
    state = sessions.get(session_id)
    if not state:
        raise HTTPException(404, "セッションが見つかりません")

    victory = state.check_victory()
    player_count = sum(1 for a in state.agents.values() if a.owner == PLAYER)
    ai_count     = sum(1 for a in state.agents.values() if a.owner == AI)
    new_logs = state.log[since:]

    return {
        "agents":        {aid: a.to_dict() for aid, a in state.agents.items()},
        "victory":       victory,
        "player_agents": player_count,
        "ai_agents":     ai_count,
        "logs":          new_logs,
        "log_count":     len(state.log),
        "owner":         dict(state.owner),
        "ward_count": {
            PLAYER:  sum(1 for o in state.owner.values() if o == PLAYER),
            AI:      sum(1 for o in state.owner.values() if o == AI),
            NEUTRAL: sum(1 for o in state.owner.values() if o == NEUTRAL),
        },
    }


# ============================================================
# 座標 → 地名変換ユーティリティ
# ============================================================
_LANDMARKS: dict[str, tuple[float, float]] = {
    "新宿駅前": (35.6896, 139.7006),
    "渋谷駅前": (35.6580, 139.7016),
    "池袋駅前": (35.7295, 139.7109),
    "東京駅前": (35.6812, 139.7671),
    "上野駅前": (35.7141, 139.7774),
    "品川駅前": (35.6284, 139.7387),
    "秋葉原":   (35.6984, 139.7731),
    "六本木":   (35.6627, 139.7311),
    "表参道":   (35.6654, 139.7120),
    "銀座":     (35.6717, 139.7649),
    "浅草":     (35.7147, 139.7967),
    "有楽町":   (35.6753, 139.7628),
    "恵比寿":   (35.6467, 139.7100),
    "錦糸町":   (35.6963, 139.8145),
    "北千住":   (35.7498, 139.8026),
    "赤羽":     (35.7783, 139.7208),
}

def _latlng_to_location(lat: float, lng: float) -> str:
    best, best_d = "不明地点", float("inf")
    for name, (la, lo) in _LANDMARKS.items():
        d = ((lat - la)**2 + (lng - lo)**2)**0.5
        if d < best_d:
            best_d, best = d, name
    for ward, (la, lo) in WARD_LATLNG.items():
        d = ((lat - la)**2 + (lng - lo)**2)**0.5
        if d < best_d:
            best_d, best = d, ward + "付近"
    return best

def _replace_coords(text: str) -> str:
    """テキスト中の緯度経度パターンを地名に置換"""
    def _sub(m: _re.Match) -> str:
        return _latlng_to_location(float(m.group(1)), float(m.group(2)))
    return _re.sub(r'\(?(3[45]\.\d+),\s*(1[34][0-9]\.\d+)\)?', _sub, text)

# ============================================================
COMBAT_RANGE    = 0.010   # 自動戦闘が発生する距離（度）≒ 1km
CAPTURE_RANGE   = 0.012   # 区を占領できる距離（度）≒ 1.2km（デモ用に広め）
COMBAT_INTERVAL = 1.5     # 自動戦闘のインターバル（秒）
REGEN_INTERVAL  = 3.0     # HP回復のインターバル（秒）
SOS_HP_THRESHOLD = 30     # このHP以下でSOS発報
SOS_INTERVAL     = 10.0   # 同じエージェントのSOS発報間隔（秒）
_last_combat: dict[str, float] = {}   # agent_id -> last combat time
_last_regen:  dict[str, float] = {}   # agent_id -> last regen time
_last_sos:    dict[str, float] = {}   # agent_id -> last SOS time


def _process_tick(state) -> None:
    """毎ループ呼ばれる: regen / 自動戦闘 / 区占領"""
    import time as _time
    now = _time.time()

    alive_agents = {aid: a for aid, a in state.agents.items() if a.is_alive}

    # ① regen
    for aid, agent in alive_agents.items():
        if agent.regen > 0 and now - _last_regen.get(aid, 0) >= REGEN_INTERVAL:
            agent.health = min(100, agent.health + agent.regen)
            _last_regen[aid] = now

    # ② 区占領チェック（idleになった瞬間 + 区の中心付近）
    for aid, agent in alive_agents.items():
        if agent.state != "idle" or not agent.target_ward:
            continue
        ward = agent.target_ward
        if ward not in WARD_LATLNG:
            continue
        wlat, wlng = WARD_LATLNG[ward]
        dist = ((agent.lat - wlat)**2 + (agent.lng - wlng)**2)**0.5
        if dist < CAPTURE_RANGE:
            prev_owner = state.owner.get(ward, NEUTRAL)
            if prev_owner != agent.owner:
                state.owner[ward] = agent.owner
                icon = "🔵" if agent.owner == PLAYER else "🔴"
                state._log(f"{icon} {agent.id} が {ward} を占領！")
            agent.target_ward = None   # 占領済みフラグをリセット

    # ③ 自動戦闘（接近した敵同士が自動的に戦う）
    player_agents = [a for a in alive_agents.values() if a.owner == PLAYER]
    ai_agents     = [a for a in alive_agents.values() if a.owner == AI]

    for pa in player_agents:
        for aa in ai_agents:
            dist = ((pa.lat - aa.lat)**2 + (pa.lng - aa.lng)**2)**0.5
            if dist > COMBAT_RANGE:
                continue

            # 両者ともクールダウン済みのときだけ戦闘
            pa_ready = now - _last_combat.get(pa.id, 0) >= COMBAT_INTERVAL
            aa_ready = now - _last_combat.get(aa.id, 0) >= COMBAT_INTERVAL
            if not (pa_ready and aa_ready):
                continue

            # プレイヤーエージェント → AI エージェント
            dmg_to_ai = aa.take_damage(pa.attack)
            # AIエージェント → プレイヤーエージェント
            dmg_to_p  = pa.take_damage(aa.attack)

            state._log(
                f"⚔️ {pa.id}({pa.health}HP) ⟺ {aa.id}({aa.health}HP) "
                f"[{dmg_to_p}/{dmg_to_ai}ダメージ]"
            )
            _last_combat[pa.id] = now
            _last_combat[aa.id] = now

            if not pa.is_alive:
                state._log(f"💀 {pa.id} 撃破！")
            if not aa.is_alive:
                state._log(f"💀 {aa.id} 撃破！")

    # ④ SOS チェック（プレイヤー側エージェントが低HP）
    for aid, agent in alive_agents.items():
        if agent.owner != PLAYER:
            continue
        if agent.health <= SOS_HP_THRESHOLD:
            if now - _last_sos.get(aid, 0) >= SOS_INTERVAL:
                location = agent.target_ward or f"({agent.lat:.3f}, {agent.lng:.3f})"
                state._log(f"🆘📡 [{aid}]: 被弾、HP{agent.health}！{location}付近で支援要請！")
                _last_sos[aid] = now

    # ⑤ 撃破されたエージェントを除去（ログは残す）
    dead = [aid for aid, a in state.agents.items() if not a.is_alive]
    for aid in dead:
        del state.agents[aid]
        _last_combat.pop(aid, None)
        _last_regen.pop(aid, None)
        _last_sos.pop(aid, None)


# FC エージェントID（Gemini API を使う3体のみ）
_FC_AGENT_IDS = {"player_001", "player_002", "player_003"}


def _rule_based_decide(agent, state) -> dict:
    """ルールベースのヒューリスティック行動決定（FC以外の全エージェント用）"""
    # すでに移動中なら何もしない
    if agent.state == "moving":
        return {"action": "idle", "params": {}}

    best_ward = None
    best_score = -1.0

    for ward, (wlat, wlng) in WARD_LATLNG.items():
        owner = state.owner.get(ward, NEUTRAL)
        if owner == agent.owner:
            continue  # 自陣はスキップ

        dist = ((agent.lat - wlat) ** 2 + (agent.lng - wlng) ** 2) ** 0.5

        # 基本スコア: 敵区 > 中立区（戦略的価値）
        base = 3.0 if owner != NEUTRAL else 2.0

        # 距離が近いほど高スコア
        score = base / (dist + 0.001)

        # 他の味方がすでに向かっている区は低優先
        for other in state.agents.values():
            if other.owner == agent.owner and other.target_ward == ward:
                score *= 0.3
                break

        if score > best_score:
            best_score = score
            best_ward = ward

    if best_ward and best_ward in WARD_LATLNG:
        return {"action": "move_to_ward", "params": {"ward": best_ward}}
    return {"action": "idle", "params": {}}


async def run_agent_ai_loop(session_id: str):
    """各エージェントが定期的に行動判断を行う"""
    import time

    if session_id not in sessions:
        return

    state = sessions[session_id]
    print(f"  [AgentAI] ループ開始: {session_id}")

    loop_count = 0
    MAX_LOOPS = 108000  # 0.1s × 108000 = 3時間で強制終了
    try:
        while not state.check_victory() and session_id in sessions and loop_count < MAX_LOOPS:
            loop_count += 1

            # 全エージェントの位置を更新
            for agent in list(state.agents.values()):
                agent.update_position(delta_time=0.1)

            # regen / 戦闘 / 占領 処理
            _process_tick(state)

            # 10ループごとにログ出力
            if loop_count % 10 == 0:
                moving_count = sum(1 for a in state.agents.values() if a.state == 'moving')
                print(f"  [AgentAI] Loop {loop_count}: {moving_count} agents moving")

            # ── エージェント行動判断 ─────────────────────────────────────
            arch = state.arch_mode  # flat | hierarchical | squad | swarm
            swarm_interval = 1.5   # SWARM: 高頻度サイクル
            fc_interval    = 3.0   # その他FC: 標準サイクル
            rb_interval    = 5.0   # Rule-based: 低頻度で十分

            fc_targets: list = []   # Gemini FC エージェント（player_001-003）
            rb_targets: list = []   # Rule-based エージェント（004-010 + AI）

            for agent_id, agent in list(state.agents.items()):
                if not agent.is_alive:
                    continue
                is_fc = agent_id in _FC_AGENT_IDS
                interval = (swarm_interval if arch == "swarm" else fc_interval) if is_fc else rb_interval
                if time.time() - agent.last_action_time < interval:
                    continue
                if is_fc:
                    fc_targets.append((agent_id, agent))
                else:
                    rb_targets.append((agent_id, agent))

            # ① Rule-based エージェント（同期実行・API呼び出しなし）
            for aid, agent in rb_targets:
                decision = _rule_based_decide(agent, state)
                execute_agent_action(agent, decision, state)
                agent.last_action_time = time.time()

            # ② Gemini FC エージェント（アーキテクチャに応じた実行モデル）
            if fc_targets:
                async def _gemini_decide(agent_id, agent):
                    try:
                        agent_ai = AgentAI(client, agent, state)
                        ev = asyncio.get_event_loop()
                        decision = await ev.run_in_executor(None, agent_ai.decide_action)
                        execute_agent_action(agent, decision, state)
                    except Exception as e:
                        print(f"  [AgentAI] {agent_id} エラー: {e}")
                    agent.last_action_time = time.time()

                if arch == "flat":
                    # ⋯ FLAT: 全FC並列（独立分散）
                    await asyncio.gather(*[_gemini_decide(aid, a) for aid, a in fc_targets])

                elif arch == "hierarchical":
                    # ▲ HIERARCHY: leader(001)先行 → broadcast → followers(002-003)並列
                    leader    = [(aid, a) for aid, a in fc_targets if aid == "player_001"]
                    followers = [(aid, a) for aid, a in fc_targets if aid != "player_001"]
                    if leader:
                        print(f"  [HIERARCHY] leader {leader[0][0]} deciding first...")
                        await _gemini_decide(*leader[0])
                    if followers:
                        print(f"  [HIERARCHY] followers {[aid for aid,_ in followers]} receiving orders...")
                        await asyncio.gather(*[_gemini_decide(aid, a) for aid, a in followers])

                elif arch == "squad":
                    # ◎ SQUAD: 厳密なシーケンシャルパイプライン 001→002→003
                    for aid, a in sorted(fc_targets, key=lambda x: x[0]):
                        print(f"  [SQUAD] pipeline → {aid}")
                        await _gemini_decide(aid, a)

                elif arch == "swarm":
                    # ∿ SWARM: 短サイクル(1.5s)での並列分散協調
                    await asyncio.gather(*[_gemini_decide(aid, a) for aid, a in fc_targets])

                else:
                    # フォールバック: flat と同じ
                    await asyncio.gather(*[_gemini_decide(aid, a) for aid, a in fc_targets])

            await asyncio.sleep(0.1)

    except Exception as e:
        print(f"  [AgentAI] ループエラー: {e}")
    finally:
        if loop_count >= MAX_LOOPS:
            print(f"  [AgentAI] 最大ループ数到達 ({MAX_LOOPS})、セッションを終了: {session_id}")
            _cleanup_session(session_id)
        else:
            print(f"  [AgentAI] ループ終了: {session_id}")


@app.delete("/game/session/{session_id}")
def delete_session(session_id: str):
    """セッションを明示的に削除してリソースを解放する"""
    if session_id not in sessions:
        raise HTTPException(404, "セッションが見つかりません")
    _cleanup_session(session_id)
    return {"ok": True, "deleted": session_id}


@app.on_event("startup")
async def start_session_cleanup_task():
    """起動時に期限切れセッションを定期削除するタスクを起動"""
    async def _cleanup_loop():
        while True:
            await asyncio.sleep(600)  # 10分ごとに確認
            now = time.time()
            expired = [
                sid for sid, created in list(session_created_at.items())
                if now - created > SESSION_TTL_SECONDS
            ]
            for sid in expired:
                print(f"  [cleanup] 期限切れセッションを削除: {sid}")
                _cleanup_session(sid)

    asyncio.create_task(_cleanup_loop())


@app.websocket("/ws/live/{session_id}")
async def live_voice_ws(websocket: WebSocket, session_id: str):
    """Gemini Live API 音声プロキシ"""
    await websocket.accept()
    print(f"  [LiveWS] 接続: {session_id}")

    state = sessions.get(session_id)
    if not state:
        print(f"  [LiveWS] セッション未発見: {session_id}")
        await websocket.send_json({"type": "error", "data": "セッションが見つかりません"})
        await websocket.close()
        return

    # エージェント装備ブリーフィングを生成
    tool_lines = []
    for aid, agent in state.agents.items():
        if agent.owner == PLAYER and agent.tools:
            tools_str = "・".join(
                f"{TOOLS[t]['icon']}{TOOLS[t]['name']}" for t in agent.tools if t in TOOLS
            )
            tool_lines.append(f"{aid}: {tools_str}")
    tool_briefing = "\n".join(tool_lines) if tool_lines else "装備なし"

    player_ward_list = sorted(state.player_wards)
    ai_ward_list     = sorted(state.ai_wards)

    system_instruction = f"""あなたは東京リスク作戦の副司令官です。

【2つのモード】
■ モード1 — 兵士通信の読み上げ
  「読み上げてください:」または「緊急SOS！読み上げてください:」で始まるメッセージを受け取ったとき:
  毎回必ず「こちら副司令官。」と名乗ってから内容をそのまま読み上げる。
  SOSは緊迫した声で読む。解説・コメント不要。

■ モード2 — 司令官との音声対話
  司令官（ユーザー）から直接音声で話しかけられたとき:
  副司令官として戦況を踏まえながら会話し、作戦意図を読み取って命令を発令する。
  会話の末尾に必ず以下を付ける:
  - 具体的な命令がある場合: [ORDER: <命令文>]
  - 命令なし: [ORDER: なし]

【現在の戦況（接続時点）】
- プレイヤー支配区: {player_ward_list} ({len(player_ward_list)}区)
- AI支配区: {ai_ward_list} ({len(ai_ward_list)}区)
- 現在の命令: {state.commander_order or "なし"}

【プレイヤー部隊の装備一覧】
{tool_briefing}

各エージェントの特性を把握し実況に活かす。（例: 高速移動持ちは「スプリンターの○○が急行」）
テキストでの返答は禁止。音声のみで応答すること。"""

    live_config = types.LiveConnectConfig(  # type: ignore[attr-defined]
        response_modalities=["AUDIO"],  # type: ignore[list-item]
        system_instruction=system_instruction,
        output_audio_transcription=types.AudioTranscriptionConfig(),  # ORDER抽出用テキスト書き起こし
    )

    stop_event = asyncio.Event()

    try:
        print("  [LiveWS] Gemini Live API 接続中...")
        async with client.aio.live.connect(
            model="gemini-2.5-flash-native-audio-preview-12-2025",
            config=live_config
        ) as live_session:
            print("  [LiveWS] Gemini Live API 接続完了")

            import re as _re2
            import time as _time

            # ユーザー/モデルの状態フラグ
            _user_last_audio = [0.0]
            _model_last_audio = [0.0]
            _mic_active = [False]  # マイクON中はinjectorを完全停止

            async def send_to_gemini():
                audio_count = 0
                try:
                    while not stop_event.is_set():
                        msg = await websocket.receive_json()
                        t = msg.get("type")
                        if t == "audio":
                            data = base64.b64decode(msg["data"])
                            await live_session.send_realtime_input(
                                audio={"data": data, "mime_type": "audio/pcm;rate=16000"}
                            )
                            _user_last_audio[0] = _time.time()
                            audio_count += 1
                            if audio_count % 50 == 0:
                                print(f"  [LiveWS] 音声送信 {audio_count}チャンク")
                        elif t == "mic_start":
                            _mic_active[0] = True
                            print("  [LiveWS] マイクON → injector停止")
                        elif t == "mic_stop":
                            _mic_active[0] = False
                            _user_last_audio[0] = _time.time()  # 直後のinjector発火防止
                            print("  [LiveWS] マイクOFF → injector再開待機")
                        elif t == "text":
                            print(f"  [LiveWS] テキスト送信: {msg['data'][:50]}")
                            await live_session.send_realtime_input(text=msg["data"])
                except Exception as e:
                    print(f"  [LiveWS] send_to_gemini エラー: {e}")
                finally:
                    stop_event.set()

            async def receive_from_gemini():
                # 公式ドキュメントのパターン: while True + turn = session.receive() でマルチターン対応
                audio_count = 0
                try:
                    while not stop_event.is_set():
                        turn = live_session.receive()
                        async for response in turn:
                            if stop_event.is_set():
                                break
                            sc = response.server_content
                            if not sc:
                                continue

                            # オーディオチャンク
                            if sc.model_turn:
                                for part in sc.model_turn.parts:
                                    if part.inline_data and part.inline_data.data:
                                        data = bytes(part.inline_data.data)
                                        b64 = base64.b64encode(data).decode()
                                        await websocket.send_json({"type": "audio", "data": b64})
                                        _model_last_audio[0] = _time.time()
                                        audio_count += 1
                                        if audio_count % 10 == 0:
                                            print(f"  [LiveWS] 音声受信 {audio_count}チャンク → ブラウザ送信")

                            # テキスト書き起こし（output_audio_transcription経由）
                            if hasattr(sc, 'output_transcription') and sc.output_transcription:
                                raw_text = getattr(sc.output_transcription, 'text', None)
                                if raw_text:
                                    om = _re2.search(r'\[ORDER:\s*(.+?)\]', raw_text)
                                    if om:
                                        extracted = om.group(1).strip()
                                        if extracted != "なし" and extracted != state.commander_order:
                                            state.commander_order = extracted
                                            state._log(f"🎖️ [副司令官命令] {extracted}")
                                            print(f"  [LiveWS] ORDER抽出: {extracted}")
                                    clean_text = _re2.sub(r'\s*\[ORDER:.*?\]', '', raw_text).strip()
                                    if clean_text:
                                        await websocket.send_json({"type": "transcript", "data": clean_text})
                                        print(f"  [LiveWS] transcript: {clean_text[:60]}")
                except Exception as e:
                    print(f"  [LiveWS] receive_from_gemini エラー: {e}")
                finally:
                    stop_event.set()

            async def agent_message_injector():
                last_idx = len(state.log)
                game_over_announced = False
                try:
                    while not stop_event.is_set():
                        await asyncio.sleep(6.0)  # 6秒間隔

                        # ゲーム終了
                        victory = state.check_victory()
                        if victory and not game_over_announced:
                            game_over_announced = True
                            end_msg = ("作戦完了！プレイヤー部隊が東京23区を制圧しました！ミッション、成功です！"
                                       if victory == PLAYER else
                                       "作戦失敗…プレイヤー部隊が全滅しました。敵の勝利です。交信を終了します。")
                            print(f"  [LiveWS] 勝利アナウンス: {end_msg}")
                            await live_session.send_realtime_input(text=end_msg)
                            break
                        if victory:
                            break

                        now = _time.time()
                        # マイクON中 → 完全停止（ユーザーとの会話を優先）
                        if _mic_active[0]:
                            continue
                        # ユーザーが5秒以内に話していた or モデルが3秒以内に応答中 → スキップ
                        if now - _user_last_audio[0] < 5.0:
                            continue
                        if now - _model_last_audio[0] < 3.0:
                            continue

                        new_logs = state.log[last_idx:]
                        last_idx = len(state.log)
                        for msg_text in new_logs:
                            if "🆘" in msg_text:
                                clean = _replace_coords(
                                    msg_text.replace("🆘", "").replace("📡", "").replace("🔵", "").strip()
                                )
                                print(f"  [LiveWS] SOS注入: {clean[:60]}")
                                await live_session.send_realtime_input(
                                    text=f"緊急SOS！読み上げてください: {clean}"
                                )
                                await asyncio.sleep(0.3)
                            elif "📡" in msg_text:
                                clean = _replace_coords(
                                    msg_text.replace("🔵", "").replace("🔴", "").replace("📡", "").strip()
                                )
                                print(f"  [LiveWS] 兵士通信注入: {clean[:60]}")
                                await live_session.send_realtime_input(
                                    text=f"読み上げてください: {clean}"
                                )
                                await asyncio.sleep(0.3)
                except Exception as e:
                    print(f"  [LiveWS] injector エラー: {e}")

            await asyncio.gather(
                send_to_gemini(),
                receive_from_gemini(),
                agent_message_injector(),
                return_exceptions=True
            )

    except WebSocketDisconnect:
        print(f"  [LiveWS] 切断: {session_id}")
    except Exception as e:
        print(f"  [LiveWS] エラー: {type(e).__name__}: {e}")
    finally:
        print(f"  [LiveWS] 終了: {session_id}")
        try:
            await websocket.close()
        except Exception:
            pass


@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    html = (Path(__file__).parent / "index.html").read_text(encoding="utf-8")
    gmaps_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    return html.replace("__GMAPS_API_KEY__", gmaps_key)
