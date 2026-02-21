"""
agent_ai モジュールのユニットテスト
====================================
AgentAI クラスと execute_agent_action 関数をテスト。
google.genai は conftest.py でモック済み。
"""

import pytest
from unittest.mock import MagicMock


# ============================================================
# ヘルパー: Gemini レスポンスモック生成
# ============================================================

def _make_response(func_name=None, func_args=None, text=None):
    """Gemini レスポンスのモックを生成"""
    resp = MagicMock()
    part = MagicMock()

    if func_name:
        fc = MagicMock()
        fc.name = func_name
        fc.args = func_args or {}
        part.function_call = fc
        part.text = None
        resp.text = None
    else:
        part.function_call = None
        part.text = text
        resp.text = text

    resp.candidates = [MagicMock()]
    resp.candidates[0].content.parts = [part]
    return resp


def _make_empty_response():
    """空レスポンス（candidates なし）"""
    resp = MagicMock()
    resp.candidates = []
    resp.text = None
    return resp


# ============================================================
# TestParseResponse
# ============================================================

class TestParseResponse:
    """AgentAI._parse_response のテスト"""

    @pytest.fixture
    def agent_ai(self, game_state_with_agents, mock_genai_client):
        from agent_ai import AgentAI
        agent = list(game_state_with_agents.agents.values())[0]
        return AgentAI(mock_genai_client, agent, game_state_with_agents)

    def test_move_to_location_returns_move_action(self, agent_ai):
        resp = _make_response("move_to_location", {"lat": 35.7, "lng": 139.7})
        result = agent_ai._parse_response(resp)
        assert result["action"] == "move"
        assert result["params"]["lat"] == 35.7
        assert result["params"]["lng"] == 139.7

    def test_move_to_ward_returns_move_to_ward_action(self, agent_ai):
        resp = _make_response("move_to_ward", {"ward": "渋谷区"})
        result = agent_ai._parse_response(resp)
        assert result["action"] == "move_to_ward"
        assert result["params"]["ward"] == "渋谷区"

    def test_patrol_area_returns_patrol_action(self, agent_ai):
        resp = _make_response("patrol_area", {"radius": 0.02})
        result = agent_ai._parse_response(resp)
        assert result["action"] == "patrol"

    def test_ask_commander_returns_ask_commander_action(self, agent_ai):
        resp = _make_response("ask_commander", {"question": "どこへ向かいますか？"})
        result = agent_ai._parse_response(resp)
        assert result["action"] == "ask_commander"
        assert result["params"]["question"] == "どこへ向かいますか？"

    def test_attack_enemy_returns_attack_action(self, agent_ai):
        resp = _make_response("attack_enemy", {"target_agent_id": "ai_001"})
        result = agent_ai._parse_response(resp)
        assert result["action"] == "attack"
        assert result["params"]["target_agent_id"] == "ai_001"

    def test_unknown_function_returns_idle(self, agent_ai):
        resp = _make_response("unknown_func", {})
        result = agent_ai._parse_response(resp)
        assert result["action"] == "idle"

    def test_text_only_response_returns_ask_commander(self, agent_ai):
        resp = _make_response(text="新宿区へ向かうべきでしょうか？")
        result = agent_ai._parse_response(resp)
        assert result["action"] == "ask_commander"
        assert "新宿区" in result["params"]["question"]

    def test_empty_candidates_returns_idle(self, agent_ai):
        resp = _make_empty_response()
        result = agent_ai._parse_response(resp)
        assert result["action"] == "idle"

    def test_empty_parts_returns_idle(self, agent_ai):
        resp = MagicMock()
        resp.candidates = [MagicMock()]
        resp.candidates[0].content.parts = []
        resp.text = None
        result = agent_ai._parse_response(resp)
        assert result["action"] == "idle"


# ============================================================
# TestGetNearbyAgents
# ============================================================

class TestGetNearbyAgents:
    """AgentAI._get_nearby_agents のテスト"""

    @pytest.fixture
    def setup(self, game_state_with_agents, mock_genai_client):
        from game_engine import PLAYER, AI
        agents = list(game_state_with_agents.agents.values())
        # player agent と ai agent を取得
        player_agent = next(a for a in agents if a.owner == PLAYER)
        ai_agent = next(a for a in agents if a.owner == AI)
        return player_agent, ai_agent, game_state_with_agents, mock_genai_client

    def test_no_agents_in_radius_returns_none_strings(self, setup):
        from agent_ai import AgentAI
        player_agent, ai_agent, state, client = setup
        # 全エージェントをプレイヤーエージェントから遠い位置に移動
        for a in state.agents.values():
            if a.id != player_agent.id:
                a.lat = player_agent.lat + 1.0  # 1度以上離れた場所
                a.lng = player_agent.lng + 1.0
        agent_ai = AgentAI(client, player_agent, state)
        result = agent_ai._get_nearby_agents(radius=0.05)
        assert result["allies"] == "なし"
        assert result["enemies"] == "なし"

    def test_nearby_ally_detected(self, setup):
        from agent_ai import AgentAI
        from game_engine import PLAYER
        player_agent, ai_agent, state, client = setup
        # 別のプレイヤーエージェントを近くに配置
        other_player = next(
            a for a in state.agents.values()
            if a.owner == PLAYER and a.id != player_agent.id
        )
        other_player.lat = player_agent.lat + 0.001
        other_player.lng = player_agent.lng + 0.001
        # 敵は遠ざける
        for a in state.agents.values():
            if a.owner != PLAYER:
                a.lat = player_agent.lat + 1.0

        agent_ai = AgentAI(client, player_agent, state)
        result = agent_ai._get_nearby_agents(radius=0.05)
        assert other_player.id in result["allies"]
        assert result["enemies"] == "なし"

    def test_nearby_enemy_detected(self, setup):
        from agent_ai import AgentAI
        from game_engine import AI
        player_agent, ai_agent, state, client = setup
        # AIエージェントを近くに配置
        ai_agent.lat = player_agent.lat + 0.001
        ai_agent.lng = player_agent.lng + 0.001
        # 他のAIは遠ざける
        for a in state.agents.values():
            if a.owner == AI and a.id != ai_agent.id:
                a.lat = player_agent.lat + 1.0

        agent_ai = AgentAI(client, player_agent, state)
        result = agent_ai._get_nearby_agents(radius=0.05)
        assert ai_agent.id in result["enemies"]

    def test_self_not_in_results(self, setup):
        from agent_ai import AgentAI
        player_agent, ai_agent, state, client = setup
        agent_ai = AgentAI(client, player_agent, state)
        result = agent_ai._get_nearby_agents(radius=10.0)  # 全エージェント範囲内
        assert player_agent.id not in result["allies"]
        assert player_agent.id not in result["enemies"]


# ============================================================
# TestDecideActionIntegration
# ============================================================

class TestDecideAction:
    """AgentAI.decide_action の統合テスト（Gemini はモック）"""

    def test_decide_action_returns_dict_with_action_key(
        self, game_state_with_agents, mock_genai_client
    ):
        from agent_ai import AgentAI
        agent = list(game_state_with_agents.agents.values())[0]
        mock_genai_client.models.generate_content.return_value = _make_response(
            "move_to_ward", {"ward": "渋谷区"}
        )
        agent_ai = AgentAI(mock_genai_client, agent, game_state_with_agents)
        result = agent_ai.decide_action()
        assert "action" in result
        assert "params" in result

    def test_decide_action_api_error_returns_idle(
        self, game_state_with_agents, mock_genai_client
    ):
        from agent_ai import AgentAI
        agent = list(game_state_with_agents.agents.values())[0]
        mock_genai_client.models.generate_content.side_effect = Exception("API Error")
        agent_ai = AgentAI(mock_genai_client, agent, game_state_with_agents)
        result = agent_ai.decide_action()
        assert result["action"] == "idle"
        # side_effect をリセット
        mock_genai_client.models.generate_content.side_effect = None

    def test_commander_order_included_for_player_agent(
        self, game_state_with_agents, mock_genai_client
    ):
        """player エージェントにはコマンダー命令がプロンプトに含まれる"""
        from agent_ai import AgentAI
        from game_engine import PLAYER
        game_state_with_agents.commander_order = "新宿区を守れ！"
        agent = next(
            a for a in game_state_with_agents.agents.values()
            if a.owner == PLAYER
        )
        mock_genai_client.models.generate_content.return_value = _make_response(
            "patrol_area", {}
        )
        agent_ai = AgentAI(mock_genai_client, agent, game_state_with_agents)

        called_prompt = None

        def capture_call(*args, **kwargs):
            nonlocal called_prompt
            called_prompt = kwargs.get("contents") or (args[1] if len(args) > 1 else "")
            return _make_response("patrol_area", {})

        mock_genai_client.models.generate_content.side_effect = capture_call
        agent_ai.decide_action()
        mock_genai_client.models.generate_content.side_effect = None
        assert called_prompt is not None
        assert "新宿区を守れ" in called_prompt


# ============================================================
# TestExecuteAgentAction
# ============================================================

class TestExecuteAgentAction:
    """execute_agent_action 関数のテスト"""

    def test_move_action_sets_destination(self, game_state_with_agents):
        from agent_ai import execute_agent_action
        agent = list(game_state_with_agents.agents.values())[0]
        decision = {"action": "move", "params": {"lat": 35.7, "lng": 139.7}}
        execute_agent_action(agent, decision, game_state_with_agents)
        assert agent.destination is not None
        assert agent.destination["lat"] == pytest.approx(35.7)
        assert agent.destination["lng"] == pytest.approx(139.7)

    def test_move_to_ward_action_sets_destination(self, game_state_with_agents):
        from agent_ai import execute_agent_action
        from ward_data import WARD_LATLNG
        agent = list(game_state_with_agents.agents.values())[0]
        decision = {"action": "move_to_ward", "params": {"ward": "渋谷区"}}
        execute_agent_action(agent, decision, game_state_with_agents)
        expected_lat, expected_lng = WARD_LATLNG["渋谷区"]
        assert agent.destination is not None
        assert agent.destination["lat"] == pytest.approx(expected_lat)
        assert agent.destination["lng"] == pytest.approx(expected_lng)
        assert agent.target_ward == "渋谷区"

    def test_move_to_invalid_ward_does_nothing(self, game_state_with_agents):
        from agent_ai import execute_agent_action
        agent = list(game_state_with_agents.agents.values())[0]
        # idleのエージェントはdestination=Noneのはず
        agent.destination = None
        agent.state = "idle"
        decision = {"action": "move_to_ward", "params": {"ward": "架空区"}}
        execute_agent_action(agent, decision, game_state_with_agents)
        assert agent.destination is None  # 無効な区名なので変化なし

    def test_patrol_action_sets_nearby_destination(self, game_state_with_agents):
        from agent_ai import execute_agent_action
        agent = list(game_state_with_agents.agents.values())[0]
        original_lat = agent.lat
        original_lng = agent.lng
        decision = {"action": "patrol", "params": {"radius": 0.01}}
        execute_agent_action(agent, decision, game_state_with_agents)
        # 巡回先は元の位置から半径内
        assert agent.destination is not None
        assert abs(agent.destination["lat"] - original_lat) <= 0.01
        assert abs(agent.destination["lng"] - original_lng) <= 0.01

    def test_ask_commander_appends_to_log(self, game_state_with_agents):
        from agent_ai import execute_agent_action
        agent = list(game_state_with_agents.agents.values())[0]
        initial_log_len = len(game_state_with_agents.log)
        decision = {
            "action": "ask_commander",
            "params": {"question": "戦況はどうですか？"}
        }
        execute_agent_action(agent, decision, game_state_with_agents)
        assert len(game_state_with_agents.log) == initial_log_len + 1
        assert "戦況はどうですか？" in game_state_with_agents.log[-1]

    def test_idle_action_does_nothing(self, game_state_with_agents):
        from agent_ai import execute_agent_action
        agent = list(game_state_with_agents.agents.values())[0]
        # idleエージェントの現在位置を記録
        original_lat = agent.lat
        original_lng = agent.lng
        agent.destination = None
        initial_log_len = len(game_state_with_agents.log)
        decision = {"action": "idle", "params": {}}
        execute_agent_action(agent, decision, game_state_with_agents)
        assert agent.lat == original_lat
        assert agent.lng == original_lng
        assert agent.destination is None  # destination が設定されていない
        assert len(game_state_with_agents.log) == initial_log_len

    def test_attack_action_deals_damage(self, game_state_with_agents):
        """攻撃アクション: レーダー範囲内の敵にダメージ"""
        from agent_ai import execute_agent_action
        from game_engine import PLAYER, AI
        agents = list(game_state_with_agents.agents.values())
        attacker = next(a for a in agents if a.owner == PLAYER)
        target = next(a for a in agents if a.owner == AI)

        # 攻撃者と標的を隣接させる
        target.lat = attacker.lat + 0.001
        target.lng = attacker.lng + 0.001
        initial_hp = target.health

        decision = {"action": "attack", "params": {"target_agent_id": target.id}}
        execute_agent_action(attacker, decision, game_state_with_agents)

        assert target.health < initial_hp

    def test_attack_action_out_of_radar_range_no_damage(self, game_state_with_agents):
        """レーダー範囲外の敵にはダメージなし"""
        from agent_ai import execute_agent_action
        from game_engine import PLAYER, AI
        agents = list(game_state_with_agents.agents.values())
        attacker = next(a for a in agents if a.owner == PLAYER)
        target = next(a for a in agents if a.owner == AI)

        # レーダー範囲 (0.05°) を超えた距離に配置
        target.lat = attacker.lat + 1.0
        target.lng = attacker.lng + 1.0
        initial_hp = target.health

        decision = {"action": "attack", "params": {"target_agent_id": target.id}}
        execute_agent_action(attacker, decision, game_state_with_agents)

        assert target.health == initial_hp

    def test_attack_friendly_fire_no_damage(self, game_state_with_agents):
        """味方への攻撃はダメージなし"""
        from agent_ai import execute_agent_action
        from game_engine import PLAYER
        agents = list(game_state_with_agents.agents.values())
        player_agents = [a for a in agents if a.owner == PLAYER]
        attacker, target = player_agents[0], player_agents[1]

        # 近くに配置
        target.lat = attacker.lat + 0.001
        target.lng = attacker.lng + 0.001
        initial_hp = target.health

        decision = {"action": "attack", "params": {"target_agent_id": target.id}}
        execute_agent_action(attacker, decision, game_state_with_agents)

        assert target.health == initial_hp  # 友軍には効果なし

    def test_attack_kills_enemy_logs_defeat(self, game_state_with_agents):
        """攻撃で撃破した場合ログに💀が記録される"""
        from agent_ai import execute_agent_action
        from game_engine import PLAYER, AI
        agents = list(game_state_with_agents.agents.values())
        attacker = next(a for a in agents if a.owner == PLAYER)
        target = next(a for a in agents if a.owner == AI)

        # HPを1にして一撃で倒せるようにする
        target.health = 1
        target.lat = attacker.lat + 0.001
        target.lng = attacker.lng + 0.001

        decision = {"action": "attack", "params": {"target_agent_id": target.id}}
        execute_agent_action(attacker, decision, game_state_with_agents)

        assert not target.is_alive
        assert any("💀" in log for log in game_state_with_agents.log)

    def test_attack_nonexistent_target_does_nothing(self, game_state_with_agents):
        from agent_ai import execute_agent_action
        from game_engine import PLAYER
        attacker = next(
            a for a in game_state_with_agents.agents.values()
            if a.owner == PLAYER
        )
        initial_log_len = len(game_state_with_agents.log)
        decision = {"action": "attack", "params": {"target_agent_id": "ghost_999"}}
        execute_agent_action(attacker, decision, game_state_with_agents)
        assert len(game_state_with_agents.log) == initial_log_len
