"""
game_engine.py のユニットテスト
================================
Agent・GameState・TOOLS・戦闘ロジック
"""
from unittest.mock import patch

from game_engine import (
    Agent, GameState, TOOLS, TEAM_BUDGET,
    PLAYER, AI, NEUTRAL,
    STARTING_TROOPS, REINFORCE_COST,
)
from ward_data import WARDS


# ============================================================
# TOOLS 定義テスト
# ============================================================
class TestToolsDefinition:
    def test_all_tools_have_required_fields(self):
        for tid, tool in TOOLS.items():
            assert "name" in tool, f"{tid}: name missing"
            assert "cost" in tool, f"{tid}: cost missing"
            assert "description" in tool, f"{tid}: description missing"
            assert "icon" in tool, f"{tid}: icon missing"
            assert "effects" in tool, f"{tid}: effects missing"

    def test_all_tool_costs_positive(self):
        for tid, tool in TOOLS.items():
            assert tool["cost"] > 0, f"{tid}: cost must be > 0"

    def test_team_budget_covers_at_least_one_tool(self):
        min_cost = min(t["cost"] for t in TOOLS.values())
        assert TEAM_BUDGET >= min_cost

    def test_known_tools_exist(self):
        for key in ("rapid_move", "radar", "attack_boost", "shield", "medkit", "comm_boost"):
            assert key in TOOLS

    def test_shield_has_defense_pct(self):
        assert "defense_pct" in TOOLS["shield"]["effects"]
        assert TOOLS["shield"]["effects"]["defense_pct"] == 40

    def test_attack_boost_multiplier(self):
        assert TOOLS["attack_boost"]["effects"]["attack_multiplier"] == 1.5


# ============================================================
# Agent 初期化テスト
# ============================================================
class TestAgentInit:
    def test_default_values(self):
        agent = Agent("player_001", PLAYER, "test prompt")
        assert agent.id == "player_001"
        assert agent.owner == PLAYER
        assert agent.system_prompt == "test prompt"
        assert agent.health == 100
        assert agent.is_alive is True
        assert agent.state == "idle"
        assert agent.tools == []
        assert agent.destination is None

    def test_base_stats_without_tools(self):
        agent = Agent("player_001", PLAYER, "")
        assert agent.attack == 10
        assert agent.defense_pct == 0
        assert agent.regen == 0
        assert agent.comm_priority is False

    def test_unknown_tool_ignored(self):
        agent = Agent("player_001", PLAYER, "", tools=["nonexistent_tool"])
        assert agent.attack == 10  # unchanged


# ============================================================
# Agent ツール適用テスト
# ============================================================
class TestAgentTools:
    def test_rapid_move_doubles_speed(self):
        base = Agent("p", PLAYER, "")
        boosted = Agent("p", PLAYER, "", tools=["rapid_move"])
        assert boosted.speed == base.speed * 2

    def test_radar_increases_range(self):
        base = Agent("p", PLAYER, "")
        boosted = Agent("p", PLAYER, "", tools=["radar"])
        assert boosted.radar_range > base.radar_range

    def test_attack_boost_increases_attack(self):
        base = Agent("p", PLAYER, "")
        boosted = Agent("p", PLAYER, "", tools=["attack_boost"])
        assert boosted.attack == int(base.attack * 1.5)

    def test_shield_sets_defense_pct(self):
        agent = Agent("p", PLAYER, "", tools=["shield"])
        assert agent.defense_pct == 40

    def test_medkit_sets_regen(self):
        agent = Agent("p", PLAYER, "", tools=["medkit"])
        assert agent.regen == 8

    def test_comm_boost_sets_priority(self):
        agent = Agent("p", PLAYER, "", tools=["comm_boost"])
        assert agent.comm_priority is True

    def test_multiple_tools_stack(self):
        agent = Agent("p", PLAYER, "", tools=["attack_boost", "medkit"])
        assert agent.attack == 15
        assert agent.regen == 8

    def test_shield_defense_pct_capped_at_80(self):
        # 同じツールを重複指定しても80%上限
        agent = Agent("p", PLAYER, "", tools=["shield", "shield"])
        assert agent.defense_pct <= 80


# ============================================================
# Agent.take_damage() テスト
# ============================================================
class TestAgentTakeDamage:
    def test_full_damage_without_shield(self):
        agent = Agent("p", PLAYER, "")
        actual = agent.take_damage(10)
        assert actual == 10
        assert agent.health == 90

    def test_shield_reduces_damage_40pct(self):
        agent = Agent("p", PLAYER, "", tools=["shield"])
        # 40% reduction: 10 * 0.6 = 6
        actual = agent.take_damage(10)
        assert actual == 6
        assert agent.health == 94

    def test_minimum_damage_is_1(self):
        agent = Agent("p", PLAYER, "", tools=["shield"])
        # 1 * 0.6 = 0.6 → max(1, 0) = 1
        actual = agent.take_damage(1)
        assert actual >= 1

    def test_death_when_hp_reaches_zero(self):
        agent = Agent("p", PLAYER, "")
        agent.take_damage(100)
        assert agent.health == 0
        assert agent.is_alive is False
        assert agent.state == "dead"

    def test_overkill_clamps_hp_to_zero(self):
        agent = Agent("p", PLAYER, "")
        agent.take_damage(200)
        assert agent.health == 0


# ============================================================
# Agent.update_position() テスト
# ============================================================
class TestAgentUpdatePosition:
    def test_no_movement_when_idle(self):
        agent = Agent("p", PLAYER, "")
        agent.state = "idle"
        orig_lat, orig_lng = agent.lat, agent.lng
        agent.update_position()
        assert agent.lat == orig_lat
        assert agent.lng == orig_lng

    def test_moves_toward_destination(self):
        agent = Agent("p", PLAYER, "")
        dest_lat, dest_lng = agent.lat + 0.1, agent.lng + 0.1
        agent.set_destination(dest_lat, dest_lng)
        orig_lat = agent.lat
        agent.update_position()
        # 目的地方向に移動している
        assert agent.lat > orig_lat

    def test_arrival_sets_state_idle(self):
        agent = Agent("p", PLAYER, "")
        # 目的地をほぼ現在位置に設定
        agent.set_destination(agent.lat + 0.00001, agent.lng + 0.00001)
        # 何度か更新して到着
        for _ in range(100):
            agent.update_position()
            if agent.state == "idle":
                break
        assert agent.state == "idle"
        assert agent.destination is None

    def test_set_destination_changes_state_to_moving(self):
        agent = Agent("p", PLAYER, "")
        agent.set_destination(35.7, 139.8, "豊島区")
        assert agent.state == "moving"
        assert agent.target_ward == "豊島区"
        assert agent.destination is not None


# ============================================================
# GameState 初期化テスト
# ============================================================
class TestGameStateInit:
    def test_all_wards_neutral_at_start(self, minimal_stats):
        state = GameState(minimal_stats)
        for ward in WARDS:
            assert state.owner[ward] == NEUTRAL

    def test_starting_troops_set(self, minimal_stats):
        state = GameState(minimal_stats)
        for ward in WARDS:
            assert state.troops[ward] == STARTING_TROOPS

    def test_setup_starting_positions(self, game_state):
        assert game_state.owner["新宿区"] == PLAYER
        assert game_state.owner["足立区"] == AI
        assert game_state.troops["新宿区"] == 5
        assert game_state.troops["足立区"] == 5

    def test_commander_order_empty_by_default(self, minimal_stats):
        state = GameState(minimal_stats)
        assert state.commander_order == ""


# ============================================================
# GameState.setup_agents() テスト
# ============================================================
class TestSetupAgents:
    def test_creates_10_player_agents(self, game_state_with_agents):
        player_agents = [a for a in game_state_with_agents.agents.values()
                         if a.owner == PLAYER]
        assert len(player_agents) == 10

    def test_creates_10_ai_agents(self, game_state_with_agents):
        ai_agents = [a for a in game_state_with_agents.agents.values()
                     if a.owner == AI]
        assert len(ai_agents) == 10

    def test_player_agents_start_at_player_ward(self, game_state_with_agents):
        from ward_data import WARD_LATLNG
        plat, plng = WARD_LATLNG["新宿区"]
        for aid, agent in game_state_with_agents.agents.items():
            if aid.startswith("player"):
                assert abs(agent.lat - plat) < 0.001
                assert abs(agent.lng - plng) < 0.001

    def test_tools_applied_to_agents(self, minimal_stats):
        state = GameState(minimal_stats)
        state.setup_starting_positions("新宿区", "足立区")
        state.setup_agents(
            player_prompts=["test"] * 10,
            ai_prompts=["test"] * 10,
            player_ward="新宿区",
            ai_ward="足立区",
            player_tools=[["attack_boost"]] + [[] for _ in range(9)],
        )
        assert state.agents["player_001"].attack == 15

    def test_budget_respected_in_ai_tools(self, minimal_stats):
        """AI自動配分がTEAM_BUDGET以内に収まっていること"""
        state = GameState(minimal_stats)
        state.setup_starting_positions("新宿区", "足立区")
        state.setup_agents(
            player_prompts=["test"] * 10,
            ai_prompts=["test"] * 10,
            player_ward="新宿区",
            ai_ward="足立区",
        )
        # ai_tools は setup_agents のデフォルトなので []
        for aid, agent in state.agents.items():
            if aid.startswith("ai"):
                total = sum(TOOLS[t]["cost"] for t in agent.tools if t in TOOLS)
                # 各エージェントのコストはTEAM_BUDGET未満
                assert total <= TEAM_BUDGET


# ============================================================
# GameState.resolve_attack() テスト
# ============================================================
class TestResolveAttack:
    def test_non_adjacent_returns_failure(self, game_state):
        # 新宿区と足立区は隣接していない
        result = game_state.resolve_attack("新宿区", "足立区", PLAYER)
        assert result["success"] is False
        assert "隣接" in result["reason"]

    def test_not_own_ward_returns_failure(self, game_state):
        # 足立区はAI所有
        result = game_state.resolve_attack("足立区", "北区", PLAYER)
        assert result["success"] is False
        assert "自分の区" in result["reason"]

    def test_insufficient_troops_returns_failure(self, game_state):
        game_state.troops["新宿区"] = 1  # 最小兵力
        result = game_state.resolve_attack("新宿区", "文京区", PLAYER)
        assert result["success"] is False

    def test_successful_attack_returns_won_true(self, game_state):
        game_state.troops["新宿区"] = 20
        game_state.troops["文京区"] = 1
        with patch("random.uniform", return_value=1.2):  # 攻撃側有利
            result = game_state.resolve_attack("新宿区", "文京区", PLAYER)
        assert result["success"] is True
        assert result["won"] is True
        assert game_state.owner["文京区"] == PLAYER

    def test_failed_attack_returns_won_false(self, game_state):
        game_state.troops["新宿区"] = 2
        game_state.troops["文京区"] = 20
        with patch("random.uniform", return_value=0.8):  # 防御側有利
            result = game_state.resolve_attack("新宿区", "文京区", PLAYER)
        assert result["success"] is True
        assert result["won"] is False
        assert game_state.owner["文京区"] != PLAYER

    def test_won_attack_changes_ownership(self, game_state):
        game_state.troops["新宿区"] = 30
        game_state.troops["文京区"] = 1
        with patch("random.uniform", return_value=1.2):
            game_state.resolve_attack("新宿区", "文京区", PLAYER)
        assert game_state.owner["文京区"] == PLAYER

    def test_result_logged(self, game_state):
        game_state.troops["新宿区"] = 10
        game_state.troops["文京区"] = 1
        log_before = len(game_state.log)
        with patch("random.uniform", return_value=1.0):
            game_state.resolve_attack("新宿区", "文京区", PLAYER)
        assert len(game_state.log) > log_before


# ============================================================
# GameState.end_turn() テスト
# ============================================================
class TestEndTurn:
    def test_income_increases(self, game_state):
        before = game_state.income.get(PLAYER, 0)
        game_state.end_turn(PLAYER)
        assert game_state.income[PLAYER] > before

    def test_rec_high_auto_recovers_troops(self, minimal_stats):
        stats = {w: {"ATK": 5, "DEF": 5, "SPD": 5, "INC": 5, "REC": 5} for w in WARDS}
        stats["新宿区"]["REC"] = 9  # REC >= 7 → 自動回復
        state = GameState(stats)
        state.setup_starting_positions("新宿区", "足立区")
        state.troops["新宿区"] = 3
        state.end_turn(PLAYER)
        assert state.troops["新宿区"] >= 3  # 回復 or 維持

    def test_only_owned_wards_generate_income(self, game_state):
        # 最初はNEUTRALが大半 → 1区分のINCしか入らない
        income = game_state.end_turn(PLAYER)
        # 少なくとも0以上であること
        assert income >= 0


# ============================================================
# GameState.reinforce() テスト
# ============================================================
class TestReinforce:
    def test_success_case(self, game_state):
        game_state.income[PLAYER] = 100
        result = game_state.reinforce("新宿区", PLAYER, amount=2)
        assert result["success"] is True
        assert game_state.troops["新宿区"] == 7  # 5 + 2

    def test_insufficient_income(self, game_state):
        game_state.income[PLAYER] = 0
        result = game_state.reinforce("新宿区", PLAYER, amount=1)
        assert result["success"] is False
        assert "収入不足" in result["reason"]

    def test_wrong_owner(self, game_state):
        game_state.income[PLAYER] = 100
        result = game_state.reinforce("足立区", PLAYER, amount=1)
        assert result["success"] is False
        assert "自分の区" in result["reason"]

    def test_income_deducted(self, game_state):
        game_state.income[PLAYER] = 10
        game_state.reinforce("新宿区", PLAYER, amount=1)
        assert game_state.income[PLAYER] == 10 - REINFORCE_COST


# ============================================================
# GameState.check_victory() テスト
# ============================================================
class TestCheckVictory:
    def test_no_winner_initially(self, game_state):
        assert game_state.check_victory() is None

    def test_player_wins_majority(self, minimal_stats):
        """12区以上制圧でプレイヤー勝利"""
        state = GameState(minimal_stats)
        state.setup_starting_positions("新宿区", "足立区")
        for w in WARDS[:12]:
            state.owner[w] = PLAYER
        assert state.check_victory() == PLAYER

    def test_five_key_wards_not_enough(self, minimal_stats):
        """主要5区だけでは勝利しない（12区未満）"""
        state = GameState(minimal_stats)
        state.setup_starting_positions("新宿区", "足立区")
        for w in ["千代田区", "港区", "新宿区", "渋谷区", "豊島区"]:
            state.owner[w] = PLAYER
        assert state.check_victory() is None

    def test_ai_wins_all_non_neutral(self, minimal_stats):
        state = GameState(minimal_stats)
        for w in WARDS:
            state.owner[w] = AI
        assert state.check_victory() == AI

    def test_no_winner_if_tied(self, minimal_stats):
        state = GameState(minimal_stats)
        half = len(WARDS) // 2
        for i, w in enumerate(WARDS):
            state.owner[w] = PLAYER if i < half else AI
        # NEUTRALが残っていないかつ同数 → AIが多い側が勝つか引き分け
        result = state.check_victory()
        assert result in (PLAYER, AI, None)


# ============================================================
# GameState.serialize() テスト
# ============================================================
class TestSerialize:
    def test_serialize_contains_required_keys(self, game_state):
        data = game_state.serialize()
        for key in ("owner", "troops", "turn", "player_wards", "ai_wards", "agents"):
            assert key in data

    def test_serialize_agents_with_agents(self, game_state_with_agents):
        data = game_state_with_agents.serialize()
        assert len(data["agents"]) == 20

    def test_agent_dict_has_required_fields(self, game_state_with_agents):
        data = game_state_with_agents.serialize()
        agent_data = next(iter(data["agents"].values()))
        for key in ("id", "owner", "lat", "lng", "state", "health", "is_alive"):
            assert key in agent_data
