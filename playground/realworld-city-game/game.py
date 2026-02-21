"""
Tokyo Real World Survival Game
================================
Gemini の Built-in Google Maps Tool を使った東京サバイバルゲーム

コンセプト:
- 実際の東京の地理・施設データをGeminiがMaps Toolで取得
- プレイヤーがリソース管理・ルート選択をする (マイクラ的な感覚)
- 選択ログを収集 → バッチでファインチューニング → エージェント進化

実行:
    python game.py

環境変数:
    GEMINI_API_KEY: Gemini API キー
"""

import os
import json
import time
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

try:
    from google import genai
    from google.genai import types
    USE_NEW_SDK = True
except ImportError:
    import google.generativeai as genai_legacy
    USE_NEW_SDK = False

from data_logger import GameDataLogger

# ============================================================
# ゲーム定数
# ============================================================
GAME_TITLE = """
╔═══════════════════════════════════════════╗
║   🗼 TOKYO REAL WORLD SURVIVAL GAME 🗼    ║
║   Powered by Gemini + Google Maps         ║
╚═══════════════════════════════════════════╝
"""

SCENARIOS = [
    {
        "id": "day1_arrival",
        "title": "Day 1: 東京到着",
        "situation": "あなたは外国から東京に到着したばかり。所持金: ¥5000、スタミナ: 100%。まず何をする？",
        "location_hint": "渋谷駅周辺",
        "resource": {"money": 5000, "stamina": 100, "day": 1},
    },
    {
        "id": "day2_exploration",
        "title": "Day 2: 探索",
        "situation": "お腹が空いてきた。近くで安くて美味しい食事場所を探したい。",
        "location_hint": "新宿区",
        "resource": {"money": 4200, "stamina": 75, "day": 2},
    },
    {
        "id": "day3_emergency",
        "title": "Day 3: 緊急事態",
        "situation": "突然体調が悪くなった。近くの医療施設を探すか、コンビニで薬を買うか？",
        "location_hint": "池袋周辺",
        "resource": {"money": 3800, "stamina": 40, "day": 3},
    },
    {
        "id": "day4_opportunity",
        "title": "Day 4: チャンス",
        "situation": "アルバイトの募集を見つけた。場所まで効率よく移動したい。",
        "location_hint": "秋葉原",
        "resource": {"money": 2500, "stamina": 60, "day": 4},
    },
    {
        "id": "day5_survive",
        "title": "Day 5: 生き残れ",
        "situation": "残り所持金が少ない。無料・低コストで過ごせる場所を見つけろ！",
        "location_hint": "上野公園周辺",
        "resource": {"money": 800, "stamina": 50, "day": 5},
    },
]

# 各シナリオロケーションの緯度経度 (Maps Tool の精度向上のため)
LOCATION_COORDS = {
    "渋谷駅周辺":   types.LatLng(latitude=35.6580, longitude=139.7016) if USE_NEW_SDK else None,
    "新宿区":       types.LatLng(latitude=35.6938, longitude=139.7034) if USE_NEW_SDK else None,
    "池袋周辺":     types.LatLng(latitude=35.7295, longitude=139.7109) if USE_NEW_SDK else None,
    "秋葉原":       types.LatLng(latitude=35.6984, longitude=139.7731) if USE_NEW_SDK else None,
    "上野公園周辺": types.LatLng(latitude=35.7148, longitude=139.7731) if USE_NEW_SDK else None,
}

# ============================================================
# Gemini クライアント初期化
# ============================================================
def init_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY が設定されていません。.env ファイルを確認してください。")

    if USE_NEW_SDK:
        client = genai.Client(api_key=api_key)
        print("  [SDK] google-genai (新SDK) を使用")
        return client, "new"
    else:
        genai_legacy.configure(api_key=api_key)
        print("  [SDK] google-generativeai (旧SDK) を使用")
        return genai_legacy, "legacy"


# ============================================================
# Gemini + Maps Tool でシナリオ応答を生成
# ============================================================
def ask_gemini_with_maps(client, sdk_type: str, scenario: dict, player_choice: str, history: list) -> str:
    """
    Gemini に Maps Tool を渡してリアルな東京情報を含む応答を生成する
    """
    location = scenario["location_hint"]
    resource = scenario["resource"]

    prompt = f"""
あなたは東京サバイバルゲームのゲームマスターです。
Google Maps のデータを活用して、プレイヤーをリアルな東京の情報でガイドしてください。

【現在の状況】
- 場所: {location}
- 所持金: ¥{resource['money']}
- スタミナ: {resource['stamina']}%
- {resource['day']}日目

【プレイヤーの選択】
{player_choice}

【指示】
1. Google Maps で {location} 周辺の関連施設・ルートを検索し、実際の情報を使って応答する
2. 具体的な施設名・場所・コストを含める
3. プレイヤーのリソース（お金・スタミナ）への影響を計算して示す
4. 次に取れる行動を3つ提示する（A/B/C の選択肢形式）
5. 応答は200文字以内で簡潔に

形式:
[結果] ...
[リソース変化] 所持金: ±XXX円 / スタミナ: ±XX%
[次の選択肢]
A) ...
B) ...
C) ...
"""

    try:
        if sdk_type == "new":
            # google_maps tool は Gemini 2.5 系が対応 (Gemini 3 は未対応)
            # Gemini 3 は推論・ストーリー生成に使い、マップ検索は 2.5 Flash で担当する2段構成
            #
            # Step 1: Gemini 2.5 Flash + Maps Tool でリアルな東京データを取得
            maps_response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"{location}周辺で「{player_choice}」に関連する実際の施設・ルート・費用を調べてください。具体的な施設名と大まかな費用を含めてください。",
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_maps=types.GoogleMaps())],
                    tool_config=types.ToolConfig(
                        retrieval_config=types.RetrievalConfig(
                            lat_lng=LOCATION_COORDS.get(location, types.LatLng(latitude=35.6762, longitude=139.6503))
                        )
                    ),
                    max_output_tokens=300,
                )
            )
            maps_data = maps_response.text

            # Step 2: Gemini 3 Flash でゲームマスターとして物語化
            full_prompt = prompt + f"\n\n【Google Maps から取得したリアルデータ】\n{maps_data}"
            response = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    max_output_tokens=1024,
                )
            )
            return response.text

        else:
            # 旧SDK フォールバック (Maps Tool なし)
            model = genai_legacy.GenerativeModel(
                "gemini-2.5-flash",
                system_instruction="あなたは東京の地理に詳しいゲームマスターです。実際の東京の施設・ルート情報を使ってゲームを進行してください。"
            )
            response = model.generate_content(prompt)
            return response.text

    except Exception as e:
        # Maps Tool が使えない場合のフォールバック
        return fallback_response(scenario, player_choice, str(e))


def fallback_response(scenario: dict, player_choice: str, error: str) -> str:
    """Maps Tool が使えない場合のシンプルな応答"""
    return f"""
[デモモード - Maps Tool 未接続]
エラー: {error[:100]}

{scenario['location_hint']}周辺でのプレイヤーの行動「{player_choice}」を処理中...

[結果] 行動を実行しました。現実のマップデータが接続されると、
具体的な施設名・ルート・コストが表示されます。

[リソース変化] 所持金: -200円 / スタミナ: -10%

[次の選択肢]
A) 近くのコンビニで休憩する
B) 公共交通機関で次のエリアへ移動する
C) 現在地で情報収集する
"""


# ============================================================
# ゲームループ
# ============================================================
class TokyoSurvivalGame:
    def __init__(self):
        self.player_id = f"player_{int(time.time())}"
        self.logger = GameDataLogger(self.player_id)
        self.history = []
        self.resources = {"money": 5000, "stamina": 100}
        self.client = None
        self.sdk_type = None

    def setup(self):
        print(GAME_TITLE)
        print("初期化中...")
        try:
            self.client, self.sdk_type = init_gemini_client()
            print("  [Gemini] 接続成功\n")
        except ValueError as e:
            print(f"  [警告] {e}")
            print("  デモモードで起動します（APIキーなし）\n")
            self.client = None
            self.sdk_type = "demo"

    def display_status(self, scenario: dict):
        r = scenario["resource"]
        print(f"\n{'='*50}")
        print(f"  {scenario['title']}")
        print(f"  📍 {scenario['location_hint']}")
        print(f"  💰 所持金: ¥{self.resources.get('money', r['money'])}")
        print(f"  ⚡ スタミナ: {self.resources.get('stamina', r['stamina'])}%")
        print(f"{'='*50}")
        print(f"\n{scenario['situation']}\n")

    def get_player_input(self, prompt_text: str = "あなたの行動 > ") -> str:
        try:
            return input(prompt_text).strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nゲームを終了します...")
            return "quit"

    def play_scenario(self, scenario: dict) -> bool:
        """1シナリオをプレイ。False を返すとゲーム終了。"""
        self.display_status(scenario)

        # プレイヤーの入力を受け付ける
        print("どうしますか？ (自由に入力してください)")
        print("例: 'コンビニで食料を買う' / '電車で移動する' / '地図を調べる'")
        print("(quit で終了)\n")

        choice = self.get_player_input()
        if choice.lower() in ["quit", "q", "exit"]:
            return False
        if not choice:
            choice = "周辺を探索する"

        # Gemini に問い合わせ
        print("\n[Gemini + Maps Tool が処理中...]\n")
        start_time = time.time()

        if self.sdk_type == "demo" or self.client is None:
            response_text = fallback_response(scenario, choice, "APIキー未設定")
        else:
            response_text = ask_gemini_with_maps(
                self.client, self.sdk_type, scenario, choice, self.history
            )

        elapsed = time.time() - start_time

        print(response_text)
        print(f"\n  [応答時間: {elapsed:.1f}秒]")

        # ログ保存（学習データとして）
        log_entry = self.logger.log_interaction(
            scenario_id=scenario["id"],
            player_choice=choice,
            gemini_response=response_text,
            resources=self.resources.copy(),
            elapsed_sec=elapsed,
        )

        # プレイヤーの評価を収集（5段階）
        print("\n--- この展開はどうでしたか？ (1-5, Enter でスキップ) ---")
        rating_input = self.get_player_input("評価 > ")
        if rating_input.isdigit() and 1 <= int(rating_input) <= 5:
            rating = int(rating_input)
            self.logger.add_rating(log_entry["id"], rating)
            print(f"  評価 {rating}/5 を記録しました（学習データに追加）")

        # 簡易リソース更新（デモ用）
        self.resources["money"] = max(0, self.resources.get("money", 5000) - 300)
        self.resources["stamina"] = max(0, self.resources.get("stamina", 100) - 15)

        # ゲームオーバー判定
        if self.resources["money"] <= 0:
            print("\n💸 所持金が尽きました... GAME OVER")
            return False
        if self.resources["stamina"] <= 0:
            print("\n😴 スタミナが尽きました... GAME OVER")
            return False

        return True

    def show_learning_summary(self):
        """セッション終了時に学習データサマリーを表示"""
        stats = self.logger.get_session_stats()
        print(f"\n{'='*50}")
        print("  📊 セッション学習データ サマリー")
        print(f"{'='*50}")
        print(f"  プレイヤーID: {self.player_id}")
        print(f"  インタラクション数: {stats['total_interactions']}")
        print(f"  平均評価: {stats['avg_rating']:.1f}/5.0")
        print(f"  ログファイル: {stats['log_file']}")
        print(f"\n  このデータは Vertex AI ファインチューニングに使用できます。")
        print(f"  詳細: training/fine_tune.py を参照\n")

    def run(self):
        """メインゲームループ"""
        self.setup()

        print("ゲームを開始します！")
        print("あなたは東京でサバイバルします。実際の東京の地理・施設情報を使ってゲームが進みます。\n")
        input("Enter を押してスタート...")

        for scenario in SCENARIOS:
            should_continue = self.play_scenario(scenario)
            if not should_continue:
                break
            print("\n次のシナリオへ...")
            time.sleep(1)
        else:
            print("\n🎉 5日間生き残りました！ CLEAR！")

        self.show_learning_summary()


# ============================================================
# エントリーポイント
# ============================================================
if __name__ == "__main__":
    game = TokyoSurvivalGame()
    game.run()
