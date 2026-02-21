"""
Real Google Maps Data Fetcher
==============================
Places API (New) + Routes API で実際の東京データを取得し、
ゲームスタッツとして ward_stats_cache.json に保存する。

使用API:
  - Places API (New): nearbySearch でPOIカウント
  - Routes API: 隣接区間の実際の所要時間（渋滞考慮）
"""

import os
import json
import time
from pathlib import Path
import urllib.request
import urllib.parse

from ward_data import WARDS, WARD_LATLNG, ADJACENCY

MAPS_API_KEY = os.getenv("MAPS_API_KEY", "")
if not MAPS_API_KEY:
    import warnings
    warnings.warn("MAPS_API_KEY が設定されていません。.env ファイルを確認してください。", stacklevel=1)
CACHE_FILE   = Path(__file__).parent / "ward_stats_cache.json"
ROUTE_CACHE  = Path(__file__).parent / "route_times_cache.json"

# ============================================================
# POI タイプ → スタッツのマッピング
# ============================================================
STAT_POI_TYPES = {
    "DEF": ["hospital", "pharmacy", "police"],
    "REC": ["park", "shrine", "tourist_attraction"],
    "INC": ["restaurant", "shopping_mall", "department_store", "supermarket"],
    "SPD": ["train_station", "subway_station", "bus_station"],
    "ATK": ["bar", "night_club", "movie_theater", "amusement_park"],
}

WARD_RADIUS = 2500  # 各区の検索半径（m）


# ============================================================
# Places API (New) - nearbySearch
# ============================================================
def fetch_poi_count(lat: float, lng: float, types: list[str], max_count: int = 20) -> int:
    """指定座標の半径内にある指定タイプのPOI数を返す"""
    url = "https://places.googleapis.com/v1/places:searchNearby"
    body = json.dumps({
        "includedTypes": types,
        "locationRestriction": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": float(WARD_RADIUS),
            }
        },
        "maxResultCount": max_count,
    }).encode()

    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Content-Type": "application/json",
        "X-Goog-Api-Key": MAPS_API_KEY,
        "X-Goog-FieldMask": "places.displayName",
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return len(data.get("places", []))
    except Exception as e:
        print(f"    [warn] Places API error: {e}")
        return 0


def count_to_stat(count: int, max_count: int = 20) -> int:
    """POI数を 1〜10 のスタッツに変換"""
    if count == 0:
        return 1
    if count >= 18:
        return 10
    return max(1, min(10, round(count / max_count * 10)))


def fetch_ward_stats_real(ward: str) -> dict:
    """Places API で1区分のスタッツを取得"""
    lat, lng = WARD_LATLNG[ward]
    stats = {}
    for stat_key, types in STAT_POI_TYPES.items():
        count = fetch_poi_count(lat, lng, types)
        stats[stat_key] = count_to_stat(count)
        time.sleep(0.1)  # レートリミット対策
    return stats


# ============================================================
# Routes API - 隣接区間の所要時間（渋滞考慮）
# ============================================================
def fetch_route_time(from_ward: str, to_ward: str) -> int:
    """隣接2区間のドライブ所要時間（秒）を返す"""
    o = WARD_LATLNG[from_ward]
    d = WARD_LATLNG[to_ward]

    url = "https://routes.googleapis.com/directions/v2:computeRoutes"
    body = json.dumps({
        "origin":      {"location": {"latLng": {"latitude": o[0], "longitude": o[1]}}},
        "destination": {"location": {"latLng": {"latitude": d[0], "longitude": d[1]}}},
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_AWARE",
    }).encode()

    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Content-Type": "application/json",
        "X-Goog-Api-Key": MAPS_API_KEY,
        "X-Goog-FieldMask": "routes.duration,routes.distanceMeters",
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            duration_str = data["routes"][0]["duration"]  # e.g. "428s"
            return int(duration_str.replace("s", ""))
    except Exception as e:
        print(f"    [warn] Routes API error ({from_ward}→{to_ward}): {e}")
        return 600  # フォールバック: 10分


def duration_to_movement_cost(seconds: int) -> int:
    """所要時間(秒) → ゲームの移動コスト (1〜5)"""
    # 5分以内=1、10分=2、15分=3、20分=4、25分超=5
    minutes = seconds / 60
    if minutes <= 5:
        return 1
    if minutes <= 10:
        return 2
    if minutes <= 15:
        return 3
    if minutes <= 20:
        return 4
    return 5


# ============================================================
# メイン: 全データ取得
# ============================================================
def fetch_all_stats(force: bool = False) -> dict:
    """
    全23区のスタッツを Places API で取得してキャッシュ。
    force=True でキャッシュを無視して再取得。
    """
    if not force and CACHE_FILE.exists():
        with open(CACHE_FILE) as f:
            cached = json.load(f)
        if set(cached.keys()) == set(WARDS):
            print(f"[stats] キャッシュ使用: {CACHE_FILE}")
            return cached

    print("[stats] Places API で23区のリアルPOIデータを取得中...")
    stats = {}
    for i, ward in enumerate(WARDS, 1):
        print(f"  [{i:02d}/23] {ward}...", end="", flush=True)
        s = fetch_ward_stats_real(ward)
        stats[ward] = s
        print(f" DEF:{s['DEF']} REC:{s['REC']} INC:{s['INC']} SPD:{s['SPD']} ATK:{s['ATK']}")
        time.sleep(0.2)

    with open(CACHE_FILE, "w") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(f"[stats] 保存: {CACHE_FILE}")
    return stats


def fetch_all_routes(force: bool = False) -> dict:
    """
    隣接区間の所要時間を Routes API で取得してキャッシュ。
    """
    if not force and ROUTE_CACHE.exists():
        with open(ROUTE_CACHE) as f:
            cached = json.load(f)
        print(f"[routes] キャッシュ使用: {ROUTE_CACHE}")
        return cached

    print("[routes] Routes API で隣接区間の所要時間を取得中...")
    routes = {}
    edges = set()
    for ward, neighbors in ADJACENCY.items():
        for nb in neighbors:
            key = "|".join(sorted([ward, nb]))
            edges.add((ward, nb, key))

    for i, (ward, nb, key) in enumerate(sorted(edges), 1):
        if key in routes:
            continue
        print(f"  [{i:02d}] {ward} → {nb}...", end="", flush=True)
        sec = fetch_route_time(ward, nb)
        cost = duration_to_movement_cost(sec)
        routes[key] = {"seconds": sec, "movement_cost": cost}
        print(f" {sec//60}分 (コスト:{cost})")
        time.sleep(0.1)

    with open(ROUTE_CACHE, "w") as f:
        json.dump(routes, f, ensure_ascii=False, indent=2)
    print(f"[routes] 保存: {ROUTE_CACHE}")
    return routes


if __name__ == "__main__":
    import sys
    force = "--force" in sys.argv
    print("=== Tokyo Risk - Real Data Fetcher ===\n")
    stats  = fetch_all_stats(force=force)
    routes = fetch_all_routes(force=force)
    print("\n=== 完了 ===")
    print(f"  スタッツ: {len(stats)}区")
    print(f"  ルート:   {len(routes)}区間")

    # ランキング表示
    print("\n--- DEF ランキング（守りやすい区） ---")
    for w, s in sorted(stats.items(), key=lambda x: -x[1]["DEF"])[:5]:
        print(f"  {w}: {s['DEF']}")
    print("\n--- SPD ランキング（移動しやすい区） ---")
    for w, s in sorted(stats.items(), key=lambda x: -x[1]["SPD"])[:5]:
        print(f"  {w}: {s['SPD']}")
    print("\n--- 移動コストが高い区間（渋滞） ---")
    for k, v in sorted(routes.items(), key=lambda x: -x[1]["movement_cost"])[:5]:
        w1, w2 = k.split("|")
        print(f"  {w1} ↔ {w2}: {v['seconds']//60}分 (コスト:{v['movement_cost']})")
