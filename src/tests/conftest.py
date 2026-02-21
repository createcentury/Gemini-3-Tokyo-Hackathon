"""
pytest 共通設定・フィクスチャ
================================
google.genai を sys.modules レベルでモックしてから
各モジュールをインポートするため、必ずこのファイルが最初に実行される。
"""
import sys
import os
from unittest.mock import MagicMock

# ============================================================
# google.genai モック (全テストで有効)
# ============================================================
_types_mock = MagicMock()
_types_mock.Tool = MagicMock(return_value=MagicMock())
_types_mock.GenerateContentConfig = MagicMock(return_value=MagicMock())
_types_mock.FunctionDeclaration = MagicMock(side_effect=lambda **kw: kw)

_genai_mock = MagicMock()
_genai_mock.types = _types_mock
_genai_mock.Client = MagicMock

_google_mock = MagicMock()
_google_mock.genai = _genai_mock

sys.modules.setdefault("google", _google_mock)
sys.modules.setdefault("google.genai", _genai_mock)
sys.modules.setdefault("google.genai.types", _types_mock)

# プロジェクトルートを path に追加
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

# ============================================================
# 共通フィクスチャ
# ============================================================
import pytest  # noqa: E402
from ward_data import WARDS  # noqa: E402


@pytest.fixture(scope="session")
def mock_genai_client():
    """Gemini API クライアントのモック"""
    client = MagicMock()

    # 基本的な generate_content レスポンス
    resp = MagicMock()
    resp.text = "テスト応答"
    resp.candidates = [MagicMock()]
    resp.candidates[0].content.parts = []
    client.models.generate_content.return_value = resp
    return client


@pytest.fixture
def minimal_stats():
    """全23区に同じスタッツを持つ最小限の stats dict"""
    return {w: {"ATK": 5, "DEF": 5, "SPD": 5, "INC": 5, "REC": 5} for w in WARDS}


@pytest.fixture
def high_spd_stats():
    """SPD 高スタッツ（ボーナスターン検証用）"""
    stats = {w: {"ATK": 5, "DEF": 5, "SPD": 5, "INC": 5, "REC": 5} for w in WARDS}
    stats["新宿区"]["SPD"] = 9
    return stats


@pytest.fixture
def game_state(minimal_stats):
    """初期化済み GameState（エージェントなし）"""
    from game_engine import GameState
    state = GameState(minimal_stats)
    state.setup_starting_positions("新宿区", "足立区")
    return state


@pytest.fixture
def game_state_with_agents(minimal_stats):
    """初期化済み GameState（エージェント20体あり）"""
    from game_engine import GameState
    state = GameState(minimal_stats)
    state.setup_starting_positions("新宿区", "足立区")
    state.setup_agents(
        player_prompts=["プレイヤー兵士"] * 10,
        ai_prompts=["AI兵士"] * 10,
        player_ward="新宿区",
        ai_ward="足立区",
    )
    return state
