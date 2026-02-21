"""
ward_data モジュールのユニットテスト
======================================
隣接グラフ・座標・スタッツデータの整合性を検証。
外部API (Gemini / Google Maps) は呼び出さない。
"""



# ============================================================
# TestAdjacency
# ============================================================

class TestAdjacency:
    """ADJACENCY グラフの整合性テスト"""

    def test_all_23_wards_present(self):
        from ward_data import ADJACENCY
        assert len(ADJACENCY) == 23

    def test_all_wards_in_wards_list(self):
        from ward_data import ADJACENCY, WARDS
        assert set(ADJACENCY.keys()) == set(WARDS)

    def test_adjacency_is_symmetric(self):
        """A→B ならば B→A でなければならない"""
        from ward_data import ADJACENCY
        for ward, neighbors in ADJACENCY.items():
            for neighbor in neighbors:
                assert ward in ADJACENCY[neighbor], (
                    f"非対称: {ward}→{neighbor} はあるが {neighbor}→{ward} がない"
                )

    def test_no_self_loops(self):
        """自己参照がないこと"""
        from ward_data import ADJACENCY
        for ward, neighbors in ADJACENCY.items():
            assert ward not in neighbors, f"{ward} が自分自身に隣接している"

    def test_each_ward_has_at_least_one_neighbor(self):
        from ward_data import ADJACENCY
        for ward, neighbors in ADJACENCY.items():
            assert len(neighbors) >= 1, f"{ward} に隣接区がない"

    def test_no_duplicate_neighbors(self):
        """隣接リストに重複がないこと"""
        from ward_data import ADJACENCY
        for ward, neighbors in ADJACENCY.items():
            assert len(neighbors) == len(set(neighbors)), (
                f"{ward} の隣接リストに重複あり"
            )

    def test_all_neighbors_are_valid_wards(self):
        """隣接先は全て有効な区名であること"""
        from ward_data import ADJACENCY, WARDS
        for ward, neighbors in ADJACENCY.items():
            for neighbor in neighbors:
                assert neighbor in WARDS, (
                    f"{ward} の隣接先 '{neighbor}' は無効な区名"
                )

    def test_graph_is_connected(self):
        """グラフ全体が連結されていること (BFS)"""
        from ward_data import ADJACENCY, WARDS
        start = WARDS[0]
        visited = {start}
        queue = [start]
        while queue:
            current = queue.pop(0)
            for neighbor in ADJACENCY[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        assert visited == set(WARDS), "グラフが連結されていない"

    def test_known_adjacencies(self):
        """実際の地理的隣接関係のスポットチェック"""
        from ward_data import ADJACENCY
        # 新宿区と渋谷区は隣接
        assert "渋谷区" in ADJACENCY["新宿区"]
        assert "新宿区" in ADJACENCY["渋谷区"]
        # 千代田区と大田区は隣接しない（非隣接チェック）
        assert "大田区" not in ADJACENCY["千代田区"]
        # 足立区と葛飾区は隣接
        assert "葛飾区" in ADJACENCY["足立区"]


# ============================================================
# TestWardLatlng
# ============================================================

class TestWardLatlng:
    """WARD_LATLNG の整合性テスト"""

    def test_all_23_wards_have_latlng(self):
        from ward_data import WARD_LATLNG, WARDS
        for ward in WARDS:
            assert ward in WARD_LATLNG, f"{ward} の緯度経度がない"

    def test_latlng_count_matches_wards(self):
        from ward_data import WARD_LATLNG, WARDS
        assert len(WARD_LATLNG) == len(WARDS)

    def test_all_latitudes_in_tokyo_range(self):
        """東京23区の緯度は概ね 35.5〜35.9 の範囲"""
        from ward_data import WARD_LATLNG
        for ward, (lat, lng) in WARD_LATLNG.items():
            assert 35.5 <= lat <= 35.9, f"{ward} の緯度 {lat} が東京範囲外"

    def test_all_longitudes_in_tokyo_range(self):
        """東京23区の経度は概ね 139.5〜140.0 の範囲"""
        from ward_data import WARD_LATLNG
        for ward, (lat, lng) in WARD_LATLNG.items():
            assert 139.5 <= lng <= 140.0, f"{ward} の経度 {lng} が東京範囲外"

    def test_latlng_are_tuples_of_floats(self):
        from ward_data import WARD_LATLNG
        for ward, coords in WARD_LATLNG.items():
            assert len(coords) == 2
            lat, lng = coords
            assert isinstance(lat, float), f"{ward} の緯度が float でない"
            assert isinstance(lng, float), f"{ward} の経度が float でない"

    def test_known_coordinates(self):
        """主要区の座標スポットチェック（概算）"""
        from ward_data import WARD_LATLNG
        # 新宿区は中央やや北西
        shinjuku_lat, shinjuku_lng = WARD_LATLNG["新宿区"]
        assert 35.68 <= shinjuku_lat <= 35.71
        assert 139.68 <= shinjuku_lng <= 139.72

    def test_no_duplicate_latlng(self):
        """全区が異なる座標を持つこと"""
        from ward_data import WARD_LATLNG
        coords = list(WARD_LATLNG.values())
        assert len(coords) == len(set(coords)), "重複した座標がある"


# ============================================================
# TestWardPositions
# ============================================================

class TestWardPositions:
    """WARD_POSITIONS (UI座標) のテスト"""

    def test_all_wards_have_position(self):
        from ward_data import WARD_POSITIONS, WARDS
        for ward in WARDS:
            assert ward in WARD_POSITIONS, f"{ward} の UI座標がない"

    def test_all_positions_in_valid_range(self):
        """UI座標は 0〜100 の範囲"""
        from ward_data import WARD_POSITIONS
        for ward, (x, y) in WARD_POSITIONS.items():
            assert 0 <= x <= 100, f"{ward} の x座標 {x} が範囲外"
            assert 0 <= y <= 100, f"{ward} の y座標 {y} が範囲外"


# ============================================================
# TestFallbackStats
# ============================================================

class TestFallbackStats:
    """_fallback_stats / _fallback_single のテスト"""

    def test_fallback_stats_covers_all_wards(self):
        from ward_data import _fallback_stats, WARDS
        stats = _fallback_stats()
        assert set(stats.keys()) == set(WARDS)

    def test_fallback_single_has_all_stat_keys(self):
        from ward_data import _fallback_single
        stat = _fallback_single("新宿区")
        for key in ["ATK", "DEF", "SPD", "INC", "REC"]:
            assert key in stat

    def test_fallback_values_in_range(self):
        from ward_data import _fallback_stats
        stats = _fallback_stats()
        for ward, ward_stats in stats.items():
            for key, val in ward_stats.items():
                assert 1 <= val <= 10, (
                    f"{ward}.{key} = {val} が 1〜10 の範囲外"
                )

    def test_central_wards_have_high_income(self):
        """都心区（千代田・中央・港・新宿・渋谷）は INC が高い"""
        from ward_data import _fallback_single
        central_wards = ["千代田区", "中央区", "港区", "新宿区", "渋谷区"]
        for ward in central_wards:
            stat = _fallback_single(ward)
            assert stat["INC"] >= 8, f"{ward} の INC が低すぎる: {stat['INC']}"

    def test_suburban_wards_have_high_rec(self):
        """郊外区は REC が高い（緑が多い）"""
        from ward_data import _fallback_single
        suburban_wards = ["練馬区", "足立区", "江戸川区", "葛飾区"]
        for ward in suburban_wards:
            stat = _fallback_single(ward)
            assert stat["REC"] >= 7, f"{ward} の REC が低すぎる: {stat['REC']}"


# ============================================================
# TestLoadOrFetchStats
# ============================================================

class TestLoadOrFetchStats:
    """load_or_fetch_stats のテスト"""

    def test_returns_fallback_when_no_client_and_no_cache(self, tmp_path, monkeypatch):
        """client=None かつキャッシュなし → フォールバック"""
        from ward_data import WARDS
        import ward_data

        # キャッシュファイルパスを存在しない一時パスにすり替え
        monkeypatch.setattr(ward_data, "CACHE_FILE", tmp_path / "nonexistent.json")

        from ward_data import load_or_fetch_stats
        stats = load_or_fetch_stats(client=None)

        assert set(stats.keys()) == set(WARDS)
        for ward_stats in stats.values():
            for key in ["ATK", "DEF", "SPD", "INC", "REC"]:
                assert key in ward_stats

    def test_loads_from_cache_when_exists(self, tmp_path, monkeypatch):
        """キャッシュファイルが存在する場合は読み込む"""
        import json
        from ward_data import WARDS
        import ward_data

        # 有効なキャッシュを作成
        cache_data = {w: {"ATK": 5, "DEF": 5, "SPD": 5, "INC": 5, "REC": 5}
                      for w in WARDS}
        cache_path = tmp_path / "ward_stats_cache.json"
        cache_path.write_text(json.dumps(cache_data), encoding="utf-8")

        monkeypatch.setattr(ward_data, "CACHE_FILE", cache_path)

        from ward_data import load_or_fetch_stats
        stats = load_or_fetch_stats(client=None)

        assert stats == cache_data

    def test_incomplete_cache_uses_fallback(self, tmp_path, monkeypatch):
        """不完全なキャッシュ（区数が足りない）はフォールバック"""
        import json
        from ward_data import WARDS
        import ward_data

        # 一部の区しかないキャッシュ
        partial_cache = {"新宿区": {"ATK": 9, "DEF": 7, "SPD": 9, "INC": 10, "REC": 4}}
        cache_path = tmp_path / "ward_stats_cache.json"
        cache_path.write_text(json.dumps(partial_cache), encoding="utf-8")

        monkeypatch.setattr(ward_data, "CACHE_FILE", cache_path)

        from ward_data import load_or_fetch_stats
        stats = load_or_fetch_stats(client=None)

        # フォールバックで全区が揃う
        assert set(stats.keys()) == set(WARDS)
