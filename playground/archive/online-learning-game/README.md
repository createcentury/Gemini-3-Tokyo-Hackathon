# オンライン学習ゲーム - POC

Gemini AIがプレイヤーとのインタラクションから学習し、進化するゲームのプロトタイプ

## プロジェクト構造

```
online-learning-game/
├── backend/                 # FastAPI バックエンド
│   ├── app/
│   │   ├── main.py         # APIエンドポイント
│   │   ├── game_logic.py   # ゲームロジック
│   │   ├── data_collector.py  # データ収集
│   │   └── models.py       # データモデル
│   ├── requirements.txt
│   └── .env.example
├── frontend/               # Next.js フロントエンド
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   └── lib/
│   └── package.json
├── training/               # ファインチューニングスクリプト
│   ├── fine_tune.py
│   ├── prepare_data.py
│   └── evaluate.py
└── README.md
```

## クイックスタート

### 1. バックエンドセットアップ

```bash
cd backend

# 仮想環境作成
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存関係インストール
pip install -r requirements.txt

# 環境変数設定
cp .env.example .env
# .envファイルにAPIキーを設定

# サーバー起動
uvicorn app.main:app --reload
```

### 2. フロントエンドセットアップ

```bash
cd frontend

# 依存関係インストール
npm install

# 開発サーバー起動
npm run dev
```

### 3. ゲームプレイ

ブラウザで http://localhost:3000 を開く

## 実装フェーズ

### フェーズ1: プロトタイプ（Day 1）✅
- [x] 基本UI
- [x] Gemini API統合
- [x] データ収集パイプライン
- [ ] 実装を開始

### フェーズ2: データ収集（Day 2）
- [ ] 10-20人でプレイテスト
- [ ] 100-500件のインタラクション収集
- [ ] データのクリーニング

### フェーズ3: 学習（Day 2-3）
- [ ] Vertex AIでファインチューニング
- [ ] 新モデルのデプロイ
- [ ] Before/After比較

### フェーズ4: デモ（Day 3）
- [ ] メトリクスダッシュボード
- [ ] デモビデオ作成
- [ ] プレゼン準備

## 環境変数

```bash
# .env
GEMINI_API_KEY=your_api_key_here
GOOGLE_CLOUD_PROJECT=your_project_id
VERTEX_AI_LOCATION=us-central1

# Firestore (オプション)
FIRESTORE_DATABASE=your_database

# モデル設定
BASE_MODEL=gemini-3-pro
TUNED_MODEL=  # ファインチューニング後に設定
```

## データ収集のポイント

### 良いデータの条件
1. **多様性**: 様々なプレイスタイル
2. **品質**: 高評価（★4-5）のインタラクション
3. **量**: 最低100件、推奨500件以上

### データ収集のコツ
```python
# 自動的に高品質データのみ収集
if rating >= 4 and session_length >= 5:
    collector.save_for_training()
```

## ファインチューニング実行

```bash
cd training

# データ準備
python prepare_data.py --min-rating 4

# ファインチューニング実行
python fine_tune.py --epochs 3

# 評価
python evaluate.py --model tuned-model-id
```

## トラブルシューティング

### Q: Vertex AIでエラーが出る
A: プロジェクトでVertex AI APIが有効化されているか確認

### Q: データが収集されない
A: Firestore接続設定を確認

### Q: ファインチューニングが高すぎる
A: データ量を減らす、またはFlash-Liteを使用

## 参考リンク

- [設計ドキュメント](../online-learning-game-design.md)
- [Vertex AI ドキュメント](https://cloud.google.com/vertex-ai/docs)
