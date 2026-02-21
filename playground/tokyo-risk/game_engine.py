"""
Tokyo Risk - ゲームエンジン
============================
- 23区の陣取り
- Maps POIデータから算出したスタッツが戦闘・移動に影響
- Gemini 3 が AI対戦相手の戦略を生成
"""

import random, json
from pathlib import Path
from ward_data import ADJACENCY, WARDS, STAT_LABELS

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
INCOME_RATIO    = 0.5     # INC スタッツ → 毎ターン増加する兵力の比率
REINFORCE_COST  = 2       # 兵力1増やすのに必要な収入


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

    # --------------------------------------------------------
    # スタッツ取得
    # --------------------------------------------------------
    def get_stat(self, ward: str, key: str) -> int:
        return self.stats.get(ward, {}).get(key, 5)

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
    # 戦闘解決
    # --------------------------------------------------------
    def resolve_attack(self, attacker_ward: str, defender_ward: str, attacker: str) -> dict:
        """
        attacker_ward → defender_ward への攻撃を解決する

        戦闘式:
          攻撃力 = 攻撃側兵力 × ATK / 10
          防御力 = 防御側兵力 × DEF / 10 (+ 自領地ボーナス ×1.3)
          ランダム要素 ±20%
        """
        if defender_ward not in ADJACENCY[attacker_ward]:
            return {"success": False, "reason": "隣接していない区です"}

        if self.owner[attacker_ward] != attacker:
            return {"success": False, "reason": "自分の区ではありません"}

        if self.troops[attacker_ward] <= 1:
            return {"success": False, "reason": "兵力が不足しています（最低1必要）"}

        atk_troops = self.troops[attacker_ward] - 1  # 1は防衛に残す
        def_troops = self.troops[defender_ward]

        # ルート移動コスト: 渋滞が多いほど攻撃力低下（コスト5→60%, コスト1→100%）
        route_cost = _movement_cost(attacker_ward, defender_ward)
        route_penalty = 1.0 - (route_cost - 1) * 0.1  # 1→1.0, 3→0.8, 5→0.6

        atk_power = atk_troops * self.get_stat(attacker_ward, "ATK") / 10 * route_penalty
        def_power = def_troops * self.get_stat(defender_ward, "DEF") / 10

        # 自領地防衛ボーナス
        defender = self.owner[defender_ward]
        if defender != NEUTRAL:
            def_power *= 1.3

        # ランダム要素
        atk_roll = atk_power * random.uniform(0.8, 1.2)
        def_roll = def_power * random.uniform(0.8, 1.2)

        won = atk_roll > def_roll
        losses_atk = max(1, int(atk_troops * 0.3)) if won else max(1, int(atk_troops * 0.6))
        losses_def = max(1, int(def_troops * 0.5)) if won else max(1, int(def_troops * 0.2))

        route_minutes = _ROUTE_TIMES.get("|".join(sorted([attacker_ward, defender_ward])), {}).get("seconds", 0) // 60
        msg_parts = [
            f"{'✅ 制圧成功' if won else '❌ 攻撃失敗'}",
            f"{attacker_ward}({atk_troops}兵) → {defender_ward}({def_troops}兵)",
            f"攻撃力:{atk_roll:.1f} vs 防御力:{def_roll:.1f}",
            f"[道路{route_minutes}分/渋滞補正{route_penalty:.0%}]",
        ]

        if won:
            self.owner[defender_ward] = attacker
            self.troops[attacker_ward] -= losses_atk
            self.troops[defender_ward] = max(1, atk_troops - losses_atk)
            msg_parts.append(f"残存兵力: {self.troops[defender_ward]}")
        else:
            self.troops[attacker_ward] = max(1, self.troops[attacker_ward] - losses_atk)
            self.troops[defender_ward] = max(1, self.troops[defender_ward] - losses_def)

        msg = " | ".join(msg_parts)
        self.log.append(msg)

        # SPDボーナス: 攻撃側のSPDが高いと追加行動チャンス
        bonus_turn = self.get_stat(attacker_ward, "SPD") >= 8

        return {
            "success": True,
            "won": won,
            "message": msg,
            "losses_attacker": losses_atk,
            "losses_defender": losses_def,
            "bonus_turn": bonus_turn and won,
        }

    # --------------------------------------------------------
    # ターン終了処理
    # --------------------------------------------------------
    def end_turn(self, side: str):
        """
        ターン終了時:
        - 各所有区のINCから収入を得る
        - REC スタッツが高い区は自動回復
        """
        total_income = 0
        for ward, owner in self.owner.items():
            if owner == side:
                inc = self.get_stat(ward, "INC")
                total_income += max(1, inc // 2)
                # REC: 回復力が高い区は兵力自動回復
                rec = self.get_stat(ward, "REC")
                if rec >= 7:
                    self.troops[ward] = min(15, self.troops[ward] + 1)

        self.income[side] = self.income.get(side, 0) + total_income
        return total_income

    def reinforce(self, ward: str, side: str, amount: int = 1) -> dict:
        """収入を使って指定区の兵力を増強"""
        cost = amount * REINFORCE_COST
        if self.income.get(side, 0) < cost:
            return {"success": False, "reason": f"収入不足（必要: {cost}、所持: {self.income[side]}）"}
        if self.owner[ward] != side:
            return {"success": False, "reason": "自分の区ではありません"}

        self.income[side] -= cost
        self.troops[ward] += amount
        msg = f"🔧 {ward} に {amount} 兵力増強（残収入: {self.income[side]}）"
        self.log.append(msg)
        return {"success": True, "message": msg}

    # --------------------------------------------------------
    # 勝利判定
    # --------------------------------------------------------
    def check_victory(self) -> str | None:
        counts = {PLAYER: 0, AI: 0, NEUTRAL: 0}
        for o in self.owner.values():
            counts[o] += 1
        if counts[NEUTRAL] == 0:
            if counts[PLAYER] > counts[AI]:
                return PLAYER
            elif counts[AI] > counts[PLAYER]:
                return AI
        # 主要5区（山手線内）を全制圧で勝利
        key_wards = ["千代田区", "港区", "新宿区", "渋谷区", "豊島区"]
        for side in [PLAYER, AI]:
            if all(self.owner[w] == side for w in key_wards):
                return side
        return None

    def serialize(self) -> dict:
        """フロントエンド向けにシリアライズ"""
        return {
            "turn":   self.turn,
            "owner":  dict(self.owner),
            "troops": dict(self.troops),
            "income": dict(self.income),
            "log":    self.log[-10:],  # 直近10件
            "stats":  self.stats,
            "victory": self.check_victory(),
            "ward_count": {
                PLAYER:  sum(1 for o in self.owner.values() if o == PLAYER),
                AI:      sum(1 for o in self.owner.values() if o == AI),
                NEUTRAL: sum(1 for o in self.owner.values() if o == NEUTRAL),
            }
        }


# ============================================================
# AI 対戦相手
# ============================================================
class GeminiAI:
    def __init__(self, client):
        self.client = client

    def decide_action(self, state: GameState) -> dict:
        """
        Gemini 3 が盤面を分析して最善手を決定する
        （戦略的思考 = Gemini 3 の推論能力を活用）
        """
        ai_wards = [w for w, o in state.owner.items() if o == AI]
        neutral_wards = [w for w, o in state.owner.items() if o == NEUTRAL]
        player_wards = [w for w, o in state.owner.items() if o == PLAYER]

        # 攻撃可能な区を列挙
        attackable = []
        for w in ai_wards:
            for neighbor in ADJACENCY[w]:
                if state.owner[neighbor] != AI and state.troops[w] > 1:
                    attackable.append({"from": w, "to": neighbor, "owner": state.owner[neighbor]})

        if not attackable:
            return {"action": "pass", "reason": "攻撃可能な区なし"}

        prompt = f"""東京23区の陣取りゲームでAI側の最善手を1つ選んでください。

現在の盤面:
- AI所有区: {ai_wards}（計{len(ai_wards)}区）
- プレイヤー所有区: {player_wards}（計{len(player_wards)}区）
- 中立区: {neutral_wards}（計{len(neutral_wards)}区）
- AI収入: {state.income.get(AI, 0)}

攻撃可能な選択肢:
{attackable}

各区のスタッツ（ATK/DEF/SPD/INC/REC 各1〜10）:
{json_snippet(state.stats, attackable)}

戦略的に最善の1手を以下のJSON形式のみで返してください:
{{"action": "attack", "from": "XX区", "to": "YY区", "reason": "理由を20文字以内"}}
または
{{"action": "reinforce", "ward": "XX区", "reason": "理由を20文字以内"}}
"""
        try:
            from google.genai import types
            response = self.client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=100,
                )
            )
            import re, json as _json
            m = re.search(r'\{.*?\}', response.text, re.DOTALL)
            if m:
                return _json.loads(m.group())
        except Exception as e:
            print(f"  [AI] Gemini決定失敗: {e}")

        # フォールバック: 最も弱い隣接区を攻撃
        best = min(attackable, key=lambda x: state.troops[x["to"]])
        return {"action": "attack", "from": best["from"], "to": best["to"], "reason": "兵力最小を狙う"}


def json_snippet(stats: dict, attackable: list) -> str:
    """攻撃対象の区のスタッツだけ抜粋"""
    import json
    wards = set()
    for a in attackable:
        wards.add(a["from"])
        wards.add(a["to"])
    return json.dumps({w: stats.get(w, {}) for w in wards}, ensure_ascii=False)
