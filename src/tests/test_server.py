"""
server モジュール (FastAPI) のエンドポイントテスト
===================================================
FastAPI TestClient を使って各エンドポイントを検証する。
google.genai と ward_data.load_or_fetch_stats はモック済み。
"""

import sys
import json
import pytest
from pathlib import Path
from unittest.mock import patch


# ============================================================
# TestClient セットアップ
# ============================================================

@pytest.fixture(scope="module")
def client():
    """FastAPI TestClient（モジュールスコープで1回だけ初期化）"""
    from ward_data import WARDS

    dummy_stats = {w: {"ATK": 5, "DEF": 5, "SPD": 5, "INC": 5, "REC": 5}
                   for w in WARDS}

    # server の module-level コードが load_or_fetch_stats を呼ぶので
    # キャッシュファイルを一時的に使うか、直接パッチする
    cache_path = Path(__file__).parent.parent / "ward_stats_cache.json"
    cache_existed = cache_path.exists()
    if not cache_existed:
        cache_path.write_text(json.dumps(dummy_stats), encoding="utf-8")

    try:
        if "server" not in sys.modules:
            with patch("google.genai.Client"):
                import server as _server
        else:
            _server = sys.modules["server"]

        from fastapi.testclient import TestClient
        tc = TestClient(_server.app)
        yield tc
    finally:
        if not cache_existed:
            cache_path.unlink(missing_ok=True)


@pytest.fixture(scope="module")
def server_module():
    """server モジュールへの参照"""
    return sys.modules["server"]


# ============================================================
# GET /game/tools
# ============================================================

class TestGetTools:
    def test_returns_200(self, client):
        resp = client.get("/game/tools")
        assert resp.status_code == 200

    def test_returns_budget(self, client):
        data = client.get("/game/tools").json()
        assert "budget" in data
        assert data["budget"] == 100

    def test_returns_tools_dict(self, client):
        data = client.get("/game/tools").json()
        assert "tools" in data
        assert isinstance(data["tools"], dict)
        assert len(data["tools"]) > 0

    def test_each_tool_has_required_fields(self, client):
        tools = client.get("/game/tools").json()["tools"]
        for tool_id, tool_data in tools.items():
            assert "name" in tool_data, f"{tool_id} に name がない"
            assert "cost" in tool_data, f"{tool_id} に cost がない"
            assert "effects" in tool_data, f"{tool_id} に effects がない"


# ============================================================
# GET /map/data
# ============================================================

class TestGetMapData:
    def test_returns_200(self, client):
        resp = client.get("/map/data")
        assert resp.status_code == 200

    def test_contains_required_keys(self, client):
        data = client.get("/map/data").json()
        for key in ["wards", "positions", "latlng", "adjacency", "stats"]:
            assert key in data, f"map/data に {key} がない"

    def test_wards_has_23_entries(self, client):
        data = client.get("/map/data").json()
        assert len(data["wards"]) == 23

    def test_stats_has_23_wards(self, client):
        data = client.get("/map/data").json()
        assert len(data["stats"]) == 23


# ============================================================
# GET / (Frontend)
# ============================================================

class TestFrontendRoute:
    def test_returns_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_returns_html(self, client):
        resp = client.get("/")
        assert "text/html" in resp.headers["content-type"]

    def test_contains_tokyo_risk(self, client):
        resp = client.get("/")
        assert "Tokyo Risk" in resp.text or "tokyo" in resp.text.lower()


# ============================================================
# POST /game/start
# ============================================================

class TestStartGame:
    @pytest.fixture
    def start_payload(self):
        return {
            "player_ward": "新宿区",
            "player_prompts": ["兵士プロンプト"] * 10,
            "player_tools": [[] for _ in range(10)]
        }

    def test_returns_200(self, client, start_payload, server_module):
        # run_agent_ai_loop は非同期タスクなのでモック
        with patch.object(server_module, "run_agent_ai_loop", return_value=None), \
             patch("asyncio.create_task"):
            resp = client.post("/game/start", json=start_payload)
        assert resp.status_code == 200

    def test_returns_session_id(self, client, start_payload, server_module):
        with patch.object(server_module, "run_agent_ai_loop", return_value=None), \
             patch("asyncio.create_task"):
            data = client.post("/game/start", json=start_payload).json()
        assert "session_id" in data

    def test_returns_player_start_ward(self, client, start_payload, server_module):
        with patch.object(server_module, "run_agent_ai_loop", return_value=None), \
             patch("asyncio.create_task"):
            data = client.post("/game/start", json=start_payload).json()
        assert data["player_start"] == "新宿区"

    def test_returns_ai_start_different_from_player(self, client, start_payload, server_module):
        with patch.object(server_module, "run_agent_ai_loop", return_value=None), \
             patch("asyncio.create_task"):
            data = client.post("/game/start", json=start_payload).json()
        assert data["ai_start"] != "新宿区"

    def test_returns_game_state(self, client, start_payload, server_module):
        with patch.object(server_module, "run_agent_ai_loop", return_value=None), \
             patch("asyncio.create_task"):
            data = client.post("/game/start", json=start_payload).json()
        assert "game_state" in data
        gs = data["game_state"]
        assert "turn" in gs
        assert "owner" in gs

    def test_budget_exceeded_returns_400(self, client, server_module):
        """予算オーバーの場合 400 を返す"""
        # attack_boost=25G を全10エージェントに付与 → 250G > 100G
        payload = {
            "player_ward": "新宿区",
            "player_tools": [["attack_boost"] for _ in range(10)]
        }
        with patch.object(server_module, "run_agent_ai_loop", return_value=None), \
             patch("asyncio.create_task"):
            resp = client.post("/game/start", json=payload)
        assert resp.status_code == 400

    def test_default_player_ward_is_shinjuku(self, client, server_module):
        """デフォルトの player_ward は新宿区"""
        with patch.object(server_module, "run_agent_ai_loop", return_value=None), \
             patch("asyncio.create_task"):
            data = client.post("/game/start", json={}).json()
        assert data["player_start"] == "新宿区"


# ============================================================
# GET /game/state/{session_id}
# ============================================================

class TestGetGameState:
    @pytest.fixture
    def session_id(self, client, server_module):
        with patch.object(server_module, "run_agent_ai_loop", return_value=None), \
             patch("asyncio.create_task"):
            data = client.post("/game/start", json={}).json()
        return data["session_id"]

    def test_returns_200_for_valid_session(self, client, session_id):
        resp = client.get(f"/game/state/{session_id}")
        assert resp.status_code == 200

    def test_returns_404_for_invalid_session(self, client):
        resp = client.get("/game/state/invalid_session_xyz")
        assert resp.status_code == 404

    def test_state_has_turn_field(self, client, session_id):
        data = client.get(f"/game/state/{session_id}").json()
        assert "turn" in data

    def test_state_has_owner_field(self, client, session_id):
        data = client.get(f"/game/state/{session_id}").json()
        assert "owner" in data
        assert isinstance(data["owner"], dict)
        assert len(data["owner"]) == 23


# ============================================================
# GET /game/agents/{session_id}
# ============================================================

class TestGetAgentsState:
    @pytest.fixture
    def session_id(self, client, server_module):
        with patch.object(server_module, "run_agent_ai_loop", return_value=None), \
             patch("asyncio.create_task"):
            data = client.post("/game/start", json={}).json()
        return data["session_id"]

    def test_returns_200(self, client, session_id):
        resp = client.get(f"/game/agents/{session_id}")
        assert resp.status_code == 200

    def test_returns_404_for_invalid_session(self, client):
        resp = client.get("/game/agents/invalid_session_xyz")
        assert resp.status_code == 404

    def test_returns_agents_dict(self, client, session_id):
        data = client.get(f"/game/agents/{session_id}").json()
        assert "agents" in data
        assert isinstance(data["agents"], dict)

    def test_returns_20_agents(self, client, session_id):
        """10 player + 10 AI = 合計 20 エージェント"""
        data = client.get(f"/game/agents/{session_id}").json()
        assert len(data["agents"]) == 20

    def test_returns_victory_field(self, client, session_id):
        data = client.get(f"/game/agents/{session_id}").json()
        assert "victory" in data

    def test_returns_player_and_ai_counts(self, client, session_id):
        data = client.get(f"/game/agents/{session_id}").json()
        assert "player_agents" in data
        assert "ai_agents" in data
        assert data["player_agents"] == 10
        assert data["ai_agents"] == 10

    def test_returns_logs(self, client, session_id):
        data = client.get(f"/game/agents/{session_id}").json()
        assert "logs" in data
        assert "log_count" in data

    def test_since_parameter_filters_logs(self, client, session_id):
        """since=N で N 番目以降のログのみ返す"""
        # 全ログ取得
        all_data = client.get(f"/game/agents/{session_id}").json()
        total = all_data["log_count"]

        # since=total → 新しいログなし
        data = client.get(f"/game/agents/{session_id}?since={total}").json()
        assert data["logs"] == []

    def test_each_agent_has_required_fields(self, client, session_id):
        """各エージェントに必須フィールドがあること"""
        data = client.get(f"/game/agents/{session_id}").json()
        required = ["id", "lat", "lng", "state", "health", "owner"]
        for agent_id, agent_data in data["agents"].items():
            for field in required:
                assert field in agent_data, f"Agent {agent_id} に {field} がない"


# ============================================================
# POST /game/commander-order/{session_id}
# ============================================================

class TestCommanderOrder:
    @pytest.fixture
    def session_id(self, client, server_module):
        with patch.object(server_module, "run_agent_ai_loop", return_value=None), \
             patch("asyncio.create_task"):
            data = client.post("/game/start", json={}).json()
        return data["session_id"]

    def test_set_commander_order_returns_ok(self, client, session_id):
        resp = client.post(
            f"/game/commander-order/{session_id}",
            json={"order": "新宿区を守れ！"}
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_order_stored_in_game_state(self, client, session_id, server_module):
        order_text = "全軍、渋谷区へ進撃！"
        client.post(
            f"/game/commander-order/{session_id}",
            json={"order": order_text}
        )
        state = server_module.sessions[session_id]
        assert state.commander_order == order_text

    def test_order_logged_in_game_log(self, client, session_id, server_module):
        client.post(
            f"/game/commander-order/{session_id}",
            json={"order": "攻撃開始！"}
        )
        state = server_module.sessions[session_id]
        assert any("攻撃開始" in log for log in state.log)

    def test_invalid_session_returns_404(self, client):
        resp = client.post(
            "/game/commander-order/invalid_session_xyz",
            json={"order": "テスト"}
        )
        assert resp.status_code == 404


# ============================================================
# POST /game/reinforce
# ============================================================

class TestReinforce:
    @pytest.fixture
    def session_id(self, client, server_module):
        with patch.object(server_module, "run_agent_ai_loop", return_value=None), \
             patch("asyncio.create_task"):
            data = client.post("/game/start", json={}).json()
        return data["session_id"]

    def test_reinforce_player_ward_returns_200(self, client, session_id):
        resp = client.post(
            "/game/reinforce",
            json={"session_id": session_id, "ward": "新宿区", "amount": 1}
        )
        assert resp.status_code == 200

    def test_invalid_session_returns_404(self, client):
        resp = client.post(
            "/game/reinforce",
            json={"session_id": "invalid_session_xyz", "ward": "新宿区", "amount": 1}
        )
        assert resp.status_code == 404


# ============================================================
# GET /route/{from_ward}/{to_ward}
# ============================================================

class TestGetRoute:
    def test_returns_200(self, client):
        resp = client.get("/route/新宿区/渋谷区")
        assert resp.status_code == 200

    def test_returns_from_and_to(self, client):
        data = client.get("/route/新宿区/渋谷区").json()
        assert data["from"] == "新宿区"
        assert data["to"] == "渋谷区"

    def test_no_route_data_returns_fallback(self, client):
        """ルートキャッシュがない場合はデフォルト値を返す"""
        data = client.get("/route/新宿区/渋谷区").json()
        assert "has_data" in data
        # キャッシュがなければ has_data=False でも OK
        if not data["has_data"]:
            assert data["estimated_minutes"] == 15
