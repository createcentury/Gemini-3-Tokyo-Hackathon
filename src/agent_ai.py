"""
Agent AI System
===============
各エージェントが独立してGemini APIを呼び出し、行動を決定する
"""

import time
from google.genai import types
from ward_data import WARDS, WARD_LATLNG, GEMINI_MODEL
from game_engine import TOOLS

_AGENT_MAX_RETRIES = 3
_AGENT_RETRY_DELAY = 1.0  # 秒（倍増バックオフ）


# Gemini Function Calling 定義
AGENT_FUNCTIONS = [
    {
        "name": "move_to_location",
        "description": "指定した緯度経度に移動する",
        "parameters": {
            "type": "object",
            "properties": {
                "lat": {"type": "number"},
                "lng": {"type": "number"},
                "reason": {"type": "string", "description": "移動理由"}
            },
            "required": ["lat", "lng"]
        }
    },
    {
        "name": "move_to_ward",
        "description": "指定した区に向かって移動する",
        "parameters": {
            "type": "object",
            "properties": {
                "ward": {"type": "string", "enum": WARDS},
                "reason": {"type": "string"}
            },
            "required": ["ward"]
        }
    },
    {
        "name": "patrol_area",
        "description": "現在地周辺を巡回する",
        "parameters": {
            "type": "object",
            "properties": {
                "radius": {"type": "number", "description": "巡回半径（度）"}
            }
        }
    },
    {
        "name": "ask_commander",
        "description": "コマンダーに質問・報告する",
        "parameters": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "質問内容"}
            },
            "required": ["question"]
        }
    },
    {
        "name": "attack_enemy",
        "description": "近くの敵エージェントを攻撃する",
        "parameters": {
            "type": "object",
            "properties": {
                "target_agent_id": {"type": "string"}
            },
            "required": ["target_agent_id"]
        }
    },
    {
        "name": "send_message",
        "description": "味方エージェント全員に自分の行動計画・発見情報をブロードキャストする",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "例: '渋谷区へ向かいます' / '敵3体が新宿区に集結中'"}
            },
            "required": ["message"]
        }
    }
]


class AgentAI:
    def __init__(self, client, agent, game_state):
        self.client = client
        self.agent = agent
        self.game_state = game_state

    def decide_action(self) -> dict:
        """
        このエージェントの次の行動を決定

        Returns:
            {
                "action": "move" | "attack" | "patrol" | "ask_commander" | "idle",
                "params": {...},
                "question_to_commander": "..." (optional)
            }
        """
        # ゲーム状況の要約
        situation = self._get_situation_summary()

        # 周辺の他エージェント情報
        nearby_agents = self._get_nearby_agents()

        # 装備ツール説明
        tool_desc = ""
        if hasattr(self.agent, 'tools') and self.agent.tools:
            parts = []
            for tid in self.agent.tools:
                t = TOOLS.get(tid)
                if t:
                    parts.append(f"  - {t['icon']} {t['name']}: {t['description']}")
            tool_desc = "## あなたの装備\n" + "\n".join(parts) + "\n"

        # ステータス情報（存在する場合のみ）
        stats_info = ""
        if hasattr(self.agent, 'attack') and hasattr(self.agent, 'defense_pct'):
            stats_info = f"攻撃力: {self.agent.attack} / ダメージ軽減: {self.agent.defense_pct}%\n"

        # コマンダー命令
        order_section = ""
        if self.agent.owner == "player":
            order = getattr(self.game_state, "commander_order", "")
            if order:
                order_section = f"\n## コマンダーからの命令\n{order}\n上記命令を最優先で実行してください。\n"

        # 味方からの最新メッセージ
        ally_messages = self._get_ally_messages()

        current_location = self._latlng_to_ward(self.agent.lat, self.agent.lng)

        prompt = f"""
{self.agent.system_prompt}

## 現在の状況
あなたのID: {self.agent.id}
現在位置: {current_location}
状態: {self.agent.state}
体力: {self.agent.health}
{stats_info}{tool_desc}{order_section}
## 周辺の味方
{nearby_agents['allies']}

## 周辺の敵
{nearby_agents['enemies']}

## 味方からの最新メッセージ
{ally_messages}

## 全体戦況
{situation}

装備・命令・戦略プロンプトをすべて踏まえ、次の行動を決定してください。
行動前に必ず send_message で作戦意図を味方に伝えてください（例：「〇〇区を確保します」「敵エージェント発見、交戦します」）。
send_message の位置表現は必ず区名・駅名などの地名を使い、緯度経度の数値は絶対に使わないでください。
"""

        last_error: Exception | None = None
        for attempt in range(_AGENT_MAX_RETRIES):
            try:
                # Gemini Function Calling
                response = self.client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        tools=[types.Tool(function_declarations=[
                            types.FunctionDeclaration(**func) for func in AGENT_FUNCTIONS  # type: ignore[arg-type]
                        ])],
                        temperature=0.5
                    )
                )
                # 関数呼び出し結果を解析
                return self._parse_response(response)

            except Exception as e:
                last_error = e
                if attempt < _AGENT_MAX_RETRIES - 1:
                    wait = _AGENT_RETRY_DELAY * (2 ** attempt)
                    print(f"  [AgentAI] {self.agent.id} リトライ {attempt + 1}/{_AGENT_MAX_RETRIES - 1}: {e}")
                    time.sleep(wait)

        print(f"  [AgentAI] {self.agent.id} 決定失敗 (全{_AGENT_MAX_RETRIES}回): {last_error}")
        return {"action": "idle", "params": {}}

    def _get_situation_summary(self) -> str:
        """ゲーム全体の状況を要約"""
        from game_engine import PLAYER, AI

        player_wards = [w for w, o in self.game_state.owner.items() if o == PLAYER]
        ai_wards = [w for w, o in self.game_state.owner.items() if o == AI]

        return f"""
- プレイヤー支配: {len(player_wards)}区 ({', '.join(player_wards[:3])}...)
- AI支配: {len(ai_wards)}区
- ターン: {self.game_state.turn}
"""

    def _latlng_to_ward(self, lat: float, lng: float) -> str:
        """緯度経度を最寄りの区名に変換"""
        best, best_d = "移動中", float("inf")
        for ward, (wlat, wlng) in WARD_LATLNG.items():
            d = ((lat - wlat)**2 + (lng - wlng)**2)**0.5
            if d < best_d:
                best_d, best = d, ward
        return best

    def _get_nearby_agents(self, radius: float | None = None) -> dict:
        """周辺のエージェント情報（デフォルトはagentのradar_range）"""
        allies = []
        enemies = []
        if radius is None:
            radius = self.agent.radar_range

        for aid, agent in self.game_state.agents.items():
            if aid == self.agent.id:
                continue

            dist = ((agent.lat - self.agent.lat)**2 +
                   (agent.lng - self.agent.lng)**2)**0.5

            if dist < radius:
                loc = self._latlng_to_ward(agent.lat, agent.lng)
                info = f"{aid}: {loc}, {agent.state}"
                if agent.owner == self.agent.owner:
                    allies.append(info)
                else:
                    enemies.append(info)

        return {
            "allies": "\n".join(allies) if allies else "なし",
            "enemies": "\n".join(enemies) if enemies else "なし"
        }

    def _get_ally_messages(self, limit=5) -> str:
        """味方チームの直近メッセージを取得"""
        msgs = self.game_state.agent_messages.get(self.agent.owner, [])
        recent = msgs[-limit:]
        if not recent:
            return "なし"
        return "\n".join(f"[{m['from']}]: {m['text']}" for m in recent)

    def _parse_response(self, response) -> dict:
        """Geminiのレスポンスを解析して行動辞書に変換"""
        if not response.candidates:
            return {"action": "idle", "params": {}}
        content = response.candidates[0].content
        if not content or not content.parts:
            return {"action": "idle", "params": {}}

        action_map = {
            "move_to_location": "move",
            "move_to_ward": "move_to_ward",
            "patrol_area": "patrol",
            "ask_commander": "ask_commander",
            "attack_enemy": "attack"
        }

        result = {"action": "idle", "params": {}}

        for part in response.candidates[0].content.parts:
            if not part.function_call:
                continue
            fc = part.function_call
            if fc.name == "send_message":
                result["broadcast"] = fc.args.get("message", "")
            else:
                result["action"] = action_map.get(fc.name, "idle")
                result["params"] = dict(fc.args)

        # function_call があった場合はその結果を返す
        if result["action"] != "idle" or "broadcast" in result:
            return result

        # テキストのみの応答: コマンダーへの質問として扱う
        if response.text:
            return {
                "action": "ask_commander",
                "params": {"question": response.text}
            }

        return {"action": "idle", "params": {}}


def execute_agent_action(agent, decision: dict, game_state):
    """エージェントの行動を実行"""
    from game_engine import PLAYER

    # ブロードキャストメッセージの処理（アクションと独立して実行）
    broadcast = decision.get("broadcast")
    if broadcast:
        msgs = game_state.agent_messages[agent.owner]
        msgs.append({"from": agent.id, "text": broadcast})
        if len(msgs) > 20:
            game_state.agent_messages[agent.owner] = msgs[-20:]
        icon = "🔵" if agent.owner == PLAYER else "🔴"
        game_state._log(f"{icon}📡 [{agent.id}]: {broadcast}")
        agent.thought = f"📡 {broadcast[:25]}"

    action = decision.get("action", "idle")
    params = decision.get("params", {})

    if action == "move":
        # 緯度経度指定の移動
        lat = params.get("lat")
        lng = params.get("lng")
        if lat and lng:
            agent.set_destination(lat, lng)
            agent.thought = params.get("reason", "📍 移動中")

    elif action == "move_to_ward":
        # 区への移動
        ward = params.get("ward")
        if ward and ward in WARD_LATLNG:
            lat, lng = WARD_LATLNG[ward]
            agent.set_destination(lat, lng, ward)
            agent.thought = f"🎯 {ward}へ向かう"

    elif action == "patrol":
        # 巡回（ランダムな近傍地点へ移動）
        import random
        radius = params.get("radius", 0.01)
        lat = agent.lat + random.uniform(-radius, radius)
        lng = agent.lng + random.uniform(-radius, radius)
        agent.set_destination(lat, lng)
        agent.thought = "🔍 周辺を巡回中"

    elif action == "ask_commander":
        # コマンダーへの質問（ログに記録）
        question = params.get("question", "")
        game_state._log(f"🤖 {agent.id}: {question}")

    elif action == "attack":
        target_id = params.get("target_agent_id")
        target = game_state.agents.get(target_id)
        if target and target.owner != agent.owner and target.is_alive:
            dist = ((target.lat - agent.lat)**2 + (target.lng - agent.lng)**2)**0.5
            if dist < agent.radar_range:
                actual = target.take_damage(agent.attack)
                game_state._log(
                    f"⚔️ {agent.id} → {target_id}: {actual}ダメージ (HP:{target.health})"
                )
                if not target.is_alive:
                    game_state._log(f"💀 {target_id} 撃破！")
            agent.thought = f"⚔️ {target_id}を攻撃"

    else:
        # idle: 何もしない
        pass
