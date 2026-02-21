"""
東京23区データ
==============
- 隣接グラフ
- 各区の概略座標（UIレイアウト用）
- Gemini Maps Tool でPOIからゲームスタッツを計算
"""

import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# 23区 隣接グラフ
# ============================================================
ADJACENCY: dict[str, list[str]] = {
    "千代田区": ["中央区", "港区", "新宿区", "文京区", "台東区"],
    "中央区":   ["千代田区", "港区", "江東区", "墨田区", "台東区"],
    "港区":     ["千代田区", "中央区", "品川区", "渋谷区", "新宿区"],
    "新宿区":   ["千代田区", "港区", "渋谷区", "中野区", "豊島区", "文京区"],
    "文京区":   ["千代田区", "新宿区", "豊島区", "荒川区", "台東区", "北区"],
    "台東区":   ["千代田区", "中央区", "文京区", "荒川区", "墨田区"],
    "墨田区":   ["中央区", "台東区", "荒川区", "葛飾区", "江東区"],
    "江東区":   ["中央区", "墨田区", "葛飾区", "江戸川区", "品川区", "大田区"],
    "品川区":   ["港区", "江東区", "大田区", "目黒区", "渋谷区"],
    "目黒区":   ["品川区", "大田区", "世田谷区", "渋谷区"],
    "大田区":   ["江東区", "品川区", "目黒区", "世田谷区"],
    "世田谷区": ["目黒区", "大田区", "渋谷区", "杉並区"],
    "渋谷区":   ["港区", "品川区", "目黒区", "世田谷区", "杉並区", "中野区", "新宿区"],
    "中野区":   ["新宿区", "渋谷区", "杉並区", "練馬区", "豊島区"],
    "杉並区":   ["渋谷区", "世田谷区", "中野区", "練馬区"],
    "豊島区":   ["新宿区", "文京区", "中野区", "練馬区", "北区", "板橋区"],
    "北区":     ["文京区", "豊島区", "板橋区", "荒川区", "足立区"],
    "荒川区":   ["文京区", "台東区", "墨田区", "葛飾区", "足立区", "北区"],
    "板橋区":   ["豊島区", "北区", "練馬区"],
    "練馬区":   ["中野区", "豊島区", "板橋区", "杉並区"],
    "足立区":   ["北区", "荒川区", "葛飾区"],
    "葛飾区":   ["墨田区", "江東区", "荒川区", "足立区", "江戸川区"],
    "江戸川区": ["江東区", "葛飾区"],
}

WARDS = list(ADJACENCY.keys())

# ============================================================
# 各区のUI座標（0〜100スケール、左上原点）
# ============================================================
WARD_POSITIONS: dict[str, tuple[float, float]] = {
    "板橋区":   (28, 12), "練馬区":   (18, 22), "北区":     (48, 17),
    "足立区":   (68, 12), "葛飾区":   (82, 22), "江戸川区": (92, 38),
    "豊島区":   (40, 26), "荒川区":   (64, 27), "墨田区":   (73, 38),
    "文京区":   (52, 32), "台東区":   (64, 36), "江東区":   (80, 50),
    "新宿区":   (38, 38), "千代田区": (54, 43), "中央区":   (66, 46),
    "中野区":   (28, 38), "渋谷区":   (38, 52), "港区":     (54, 55),
    "杉並区":   (20, 50), "目黒区":   (44, 64), "品川区":   (60, 65),
    "世田谷区": (28, 68), "大田区":   (54, 76),
}

# ============================================================
# POIカテゴリ → ゲームスタッツのマッピング
# ============================================================
# 各スタッツは 1〜10 のスケール
STAT_KEYS = ["ATK", "DEF", "SPD", "INC", "REC"]
STAT_LABELS = {
    "ATK": "攻撃力",   # 商業施設・繁華街密度
    "DEF": "防御力",   # 病院・警察署密度
    "SPD": "機動力",   # 駅・交通網密度
    "INC": "収入",     # ビジネス・オフィス密度
    "REC": "回復力",   # 公園・緑地密度
}

CACHE_FILE = Path(__file__).parent / "ward_stats_cache.json"

GEMINI_MODEL = "gemini-3-flash-preview"


def fetch_ward_stats_from_gemini(ward_name: str, client) -> dict | None:
    """
    Gemini 3 Flash の東京知識でスタッツを計算する（高速・安定）
    Maps Tool はゲームプレイ中のイベント生成に使用
    """
    from google.genai import types
    import re

    query = f"""{ward_name}のゲームスタッツを東京の実際の特徴から1〜10で評価してください。

評価基準:
- ATK: 飲食店・商業施設・繁華街の密度
- DEF: 病院・警察署・安全施設の密度
- SPD: 鉄道駅数・交通アクセスの良さ
- INC: オフィスビル・企業・経済力
- REC: 公園・緑地・神社の多さ

JSON形式のみで返してください:
{{"ATK": X, "DEF": X, "SPD": X, "INC": X, "REC": X}}"""

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=query,
            config=types.GenerateContentConfig(temperature=0.1, max_output_tokens=2048)
        )
        text = (response.text or "").strip()
        # markdownコードブロック対応
        m = re.search(r'\{[^{}]*"ATK"[^{}]*\}', text, re.DOTALL)
        if m:
            stats = json.loads(m.group())
            return {k: max(1, min(10, int(v))) for k, v in stats.items() if k in STAT_KEYS}
    except Exception as e:
        print(f"  [warn] {ward_name} 取得失敗: {e}")
    return None


# 緯度経度（各区の中心点、概算）
WARD_LATLNG: dict[str, tuple[float, float]] = {
    "千代田区": (35.694, 139.754), "中央区":   (35.670, 139.773),
    "港区":     (35.658, 139.751), "新宿区":   (35.694, 139.703),
    "文京区":   (35.708, 139.752), "台東区":   (35.713, 139.780),
    "墨田区":   (35.711, 139.801), "江東区":   (35.673, 139.817),
    "品川区":   (35.609, 139.730), "目黒区":   (35.642, 139.698),
    "大田区":   (35.562, 139.716), "世田谷区": (35.646, 139.653),
    "渋谷区":   (35.661, 139.704), "中野区":   (35.707, 139.664),
    "杉並区":   (35.699, 139.636), "豊島区":   (35.725, 139.717),
    "北区":     (35.752, 139.734), "荒川区":   (35.736, 139.783),
    "板橋区":   (35.752, 139.689), "練馬区":   (35.736, 139.651),
    "足立区":   (35.775, 139.804), "葛飾区":   (35.734, 139.847),
    "江戸川区": (35.706, 139.868),
}


def load_or_fetch_stats(client=None) -> dict[str, dict]:
    """
    キャッシュがあれば読み込む。なければ Gemini Maps で取得してキャッシュ。
    client=None の場合はフォールバック値を使う。
    """
    if CACHE_FILE.exists():
        with open(CACHE_FILE) as f:
            cached = json.load(f)
        if set(cached.keys()) == set(WARDS):
            print(f"  [stats] キャッシュから読み込み: {CACHE_FILE}")
            return cached

    if client is None:
        print("  [stats] APIなし → フォールバック値を使用")
        return _fallback_stats()

    print("  [stats] Gemini Maps で23区スタッツを取得中...")
    stats = {}
    for ward in WARDS:
        print(f"    {ward}...", end="", flush=True)
        result = fetch_ward_stats_from_gemini(ward, client)
        if result:
            stats[ward] = result
            print(f" {result}")
        else:
            stats[ward] = _fallback_single(ward)
            print(f" (fallback) {stats[ward]}")

    with open(CACHE_FILE, "w") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(f"  [stats] キャッシュ保存: {CACHE_FILE}")
    return stats


def _fallback_single(ward: str) -> dict:
    """都心 vs 郊外で大まかなフォールバック値"""
    central = ["千代田区", "中央区", "港区", "新宿区", "渋谷区"]
    inner   = ["文京区", "台東区", "豊島区", "品川区", "目黒区", "墨田区", "江東区"]
    if ward in central:
        return {"ATK": 9, "DEF": 7, "SPD": 9, "INC": 10, "REC": 4}
    elif ward in inner:
        return {"ATK": 7, "DEF": 7, "SPD": 8, "INC": 7,  "REC": 6}
    else:
        return {"ATK": 5, "DEF": 6, "SPD": 5, "INC": 5,  "REC": 8}


def _fallback_stats() -> dict[str, dict]:
    return {w: _fallback_single(w) for w in WARDS}
