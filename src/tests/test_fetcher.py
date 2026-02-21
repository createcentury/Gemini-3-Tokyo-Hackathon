"""
real_data_fetcher モジュールのユニットテスト
=============================================
純粋な変換関数（count_to_stat, duration_to_movement_cost）を
外部API呼び出しなしでテスト。
"""



# ============================================================
# TestCountToStat
# ============================================================

class TestCountToStat:
    """count_to_stat(count, max_count=20) のテスト"""

    def test_zero_count_returns_1(self):
        from real_data_fetcher import count_to_stat
        assert count_to_stat(0) == 1

    def test_max_count_returns_10(self):
        from real_data_fetcher import count_to_stat
        assert count_to_stat(18) == 10

    def test_above_18_returns_10(self):
        """18以上は全て 10"""
        from real_data_fetcher import count_to_stat
        assert count_to_stat(19) == 10
        assert count_to_stat(20) == 10
        assert count_to_stat(100) == 10

    def test_middle_value(self):
        """中間値: count=10, max=20 → 5"""
        from real_data_fetcher import count_to_stat
        assert count_to_stat(10) == 5

    def test_result_always_in_range_1_to_10(self):
        """0〜20 の全カウントで結果が 1〜10 の範囲内"""
        from real_data_fetcher import count_to_stat
        for count in range(0, 25):
            result = count_to_stat(count)
            assert 1 <= result <= 10, f"count={count} → {result} が範囲外"

    def test_small_count_returns_low_stat(self):
        from real_data_fetcher import count_to_stat
        assert count_to_stat(1) <= 3

    def test_large_count_returns_high_stat(self):
        from real_data_fetcher import count_to_stat
        assert count_to_stat(17) >= 8

    def test_custom_max_count(self):
        """max_count=10 のとき count=10 → 10"""
        from real_data_fetcher import count_to_stat
        assert count_to_stat(10, max_count=10) == 10

    def test_returns_integer(self):
        from real_data_fetcher import count_to_stat
        assert isinstance(count_to_stat(5), int)

    def test_monotonically_increasing(self):
        """count が増えるにつれて stat は単調非減少"""
        from real_data_fetcher import count_to_stat
        results = [count_to_stat(i) for i in range(21)]
        for i in range(len(results) - 1):
            assert results[i] <= results[i + 1], (
                f"単調非減少違反: count={i} → {results[i]}, count={i+1} → {results[i+1]}"
            )


# ============================================================
# TestDurationToMovementCost
# ============================================================

class TestDurationToMovementCost:
    """duration_to_movement_cost(seconds) のテスト"""

    def test_5_minutes_returns_1(self):
        from real_data_fetcher import duration_to_movement_cost
        assert duration_to_movement_cost(300) == 1  # 5分 = 300秒

    def test_less_than_5_minutes_returns_1(self):
        from real_data_fetcher import duration_to_movement_cost
        assert duration_to_movement_cost(0)   == 1
        assert duration_to_movement_cost(60)  == 1  # 1分
        assert duration_to_movement_cost(299) == 1  # 4分59秒

    def test_10_minutes_returns_2(self):
        from real_data_fetcher import duration_to_movement_cost
        assert duration_to_movement_cost(600) == 2  # 10分

    def test_6_to_10_minutes_returns_2(self):
        from real_data_fetcher import duration_to_movement_cost
        assert duration_to_movement_cost(301) == 2  # 5分1秒
        assert duration_to_movement_cost(540) == 2  # 9分

    def test_15_minutes_returns_3(self):
        from real_data_fetcher import duration_to_movement_cost
        assert duration_to_movement_cost(900) == 3  # 15分

    def test_11_to_15_minutes_returns_3(self):
        from real_data_fetcher import duration_to_movement_cost
        assert duration_to_movement_cost(601) == 3  # 10分1秒
        assert duration_to_movement_cost(840) == 3  # 14分

    def test_20_minutes_returns_4(self):
        from real_data_fetcher import duration_to_movement_cost
        assert duration_to_movement_cost(1200) == 4  # 20分

    def test_16_to_20_minutes_returns_4(self):
        from real_data_fetcher import duration_to_movement_cost
        assert duration_to_movement_cost(901)  == 4  # 15分1秒
        assert duration_to_movement_cost(1199) == 4  # 19分59秒

    def test_more_than_25_minutes_returns_5(self):
        from real_data_fetcher import duration_to_movement_cost
        assert duration_to_movement_cost(1201) == 5  # 20分1秒
        assert duration_to_movement_cost(1500) == 5  # 25分
        assert duration_to_movement_cost(3600) == 5  # 60分

    def test_result_always_in_range_1_to_5(self):
        """様々な秒数での結果が 1〜5 の範囲内"""
        from real_data_fetcher import duration_to_movement_cost
        test_seconds = [0, 60, 180, 300, 360, 600, 660, 900, 960, 1200, 1260, 1500, 3600]
        for sec in test_seconds:
            result = duration_to_movement_cost(sec)
            assert 1 <= result <= 5, f"seconds={sec} → {result} が範囲外"

    def test_returns_integer(self):
        from real_data_fetcher import duration_to_movement_cost
        assert isinstance(duration_to_movement_cost(600), int)

    def test_monotonically_non_decreasing(self):
        """秒数が増えるにつれてコストは単調非減少"""
        from real_data_fetcher import duration_to_movement_cost
        checkpoints = [0, 300, 600, 900, 1200, 1500]
        results = [duration_to_movement_cost(s) for s in checkpoints]
        for i in range(len(results) - 1):
            assert results[i] <= results[i + 1], (
                f"単調非減少違反: {checkpoints[i]}秒→{results[i]}, "
                f"{checkpoints[i+1]}秒→{results[i+1]}"
            )


# ============================================================
# TestBuildAiToolsIntegration (server._build_ai_tools)
# ============================================================

class TestBuildAiTools:
    """server._build_ai_tools のユニットテスト"""

    def test_returns_list_of_10(self):
        import sys
        # server のインポートには conftest.py のモックが必要
        # ward_stats_cache.json がないとエラーになるので monkeypatch で対処
        from unittest.mock import patch
        import json
        from pathlib import Path

        cache_path = Path(__file__).parent.parent / "ward_stats_cache.json"
        from ward_data import WARDS
        dummy_cache = {w: {"ATK": 5, "DEF": 5, "SPD": 5, "INC": 5, "REC": 5}
                       for w in WARDS}

        # キャッシュファイルが存在しない場合は一時的に作成して import する
        cache_existed = cache_path.exists()
        if not cache_existed:
            cache_path.write_text(json.dumps(dummy_cache), encoding="utf-8")
        try:
            # モジュールがすでに import されていれば再利用
            if "server" in sys.modules:
                from server import _build_ai_tools
            else:
                with patch("google.genai.Client"):
                    pass
                from server import _build_ai_tools
            result = _build_ai_tools()
        finally:
            if not cache_existed:
                cache_path.unlink(missing_ok=True)

        assert len(result) == 10
        assert all(isinstance(tools, list) for tools in result)

    def test_total_cost_within_budget(self):
        import sys
        from unittest.mock import patch
        import json
        from pathlib import Path
        from game_engine import TOOLS, TEAM_BUDGET

        cache_path = Path(__file__).parent.parent / "ward_stats_cache.json"
        from ward_data import WARDS
        dummy_cache = {w: {"ATK": 5, "DEF": 5, "SPD": 5, "INC": 5, "REC": 5}
                       for w in WARDS}

        cache_existed = cache_path.exists()
        if not cache_existed:
            cache_path.write_text(json.dumps(dummy_cache), encoding="utf-8")
        try:
            if "server" in sys.modules:
                from server import _build_ai_tools
            else:
                with patch("google.genai.Client"):
                    pass
                from server import _build_ai_tools

            # 複数回実行して予算制約を確認
            for _ in range(5):
                ai_tools = _build_ai_tools()
                total_cost = sum(
                    TOOLS[t]["cost"]
                    for agent_tools in ai_tools
                    for t in agent_tools
                    if t in TOOLS
                )
                assert total_cost <= TEAM_BUDGET, (
                    f"AI ツールコスト {total_cost}G が予算 {TEAM_BUDGET}G を超過"
                )
        finally:
            if not cache_existed:
                cache_path.unlink(missing_ok=True)
