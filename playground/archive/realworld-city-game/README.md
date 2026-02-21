# Tokyo Real World Survival Game

Gemini の **Built-in Google Maps Tool** を使った東京サバイバルゲームのプレイグラウンド。

## コンセプト

```
実際の東京の地理・施設データ
        ↓ (Gemini Maps Tool が取得)
プレイヤーが選択
        ↓
インタラクションをログ保存
        ↓
Vertex AI でバッチファインチューニング
        ↓
エージェントが「東京での生き残り方」を学習・進化
```

マイクラ的な「リソース管理 × 現実世界の地理」で、エージェントが学習する仕組みの実験。

---

## ファイル構成

```
realworld-city-game/
├── game.py           # メインゲームループ
├── data_logger.py    # インタラクションログ + Fine-tuning データ生成
├── requirements.txt
├── .env.example
├── data/             # セッションログ (自動生成)
│   ├── session_*.jsonl       # 全インタラクション
│   └── finetune_ready.jsonl  # 評価4以上の良質データ (Fine-tuning用)
└── saves/            # セーブデータ (将来用)
```

---

## クイックスタート

```bash
cd playground/realworld-city-game

# 環境変数を設定
cp .env.example .env
# .env に GEMINI_API_KEY を記入

# 依存関係インストール
pip install -r requirements.txt

# ゲーム起動
python game.py
```

APIキーがなくてもデモモードで動作確認できます。

---

## Maps Tool について

### 実装: 2段構成

**Gemini 3 は Maps Tool 未対応** (2026/02 時点)。Maps Tool は Gemini 2.5 系のみ対応。
そのため 2 モデルを役割分担させる構成:

```
Gemini 2.5 Flash + Maps Tool  →  実際の施設名・ルート・費用を取得
         ↓ (マップデータを渡す)
Gemini 3 Flash               →  ゲームマスターとして物語化・選択肢生成
```

```python
# Step 1: Maps Tool でリアルデータ取得 (2.5 Flash)
maps_response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="渋谷周辺でコンビニを探してください",
    config=types.GenerateContentConfig(
        tools=[types.Tool(google_maps=types.GoogleMaps())],
        tool_config=types.ToolConfig(
            retrieval_config=types.RetrievalConfig(
                lat_lng=types.LatLng(latitude=35.658, longitude=139.701)
            )
        ),
    )
)

# Step 2: Gemini 3 で物語化
response = client.models.generate_content(
    model="gemini-3-flash-preview",
    contents=f"ゲームマスターとして以下のデータを使って展開を生成:\n{maps_response.text}",
)
```

Maps Tool の料金: $25 / 1K grounded prompts (500 req/day 無料枠あり)

---

## 学習データの活用

ゲームプレイ中、評価 4-5 のインタラクションが `data/finetune_ready.jsonl` に自動保存される。

```jsonl
{"contents": [{"role": "user", "parts": [{"text": "シナリオ: day1_arrival..."}]}, {"role": "model", "parts": [{"text": "..."}]}], "metadata": {...}}
```

このファイルを Vertex AI の Supervised Fine-tuning に使える:

```python
# training/ ディレクトリ (online-learning-game) の fine_tune.py を参照
```

---

## 次の実験アイデア

- [ ] シナリオを将棋の「盤面」として表現 (各エリア = 駒)
- [ ] 複数プレイヤーデータを集約してコミュニティ学習
- [ ] マップの「危険エリア」「お得エリア」をエージェントが自律発見
- [ ] Cesium + Unity で 3D ビジュアライゼーション追加
