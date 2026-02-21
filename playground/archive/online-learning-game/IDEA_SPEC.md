# Online Learning Game - 学習するインタラクティブストーリー

## 📋 基本情報

| 項目 | 内容 |
|------|------|
| **プロジェクト名** | Online Learning Game |
| **ステータス** | 🚧 Backend完成 / Frontend未実装 |
| **作成日** | 2026-02-21 |
| **最終更新** | 2026-02-21 |
| **ハッカソントラック** | 推論&マルチモーダル / 高度なツール使用 |

## 🎯 概要（エレベーターピッチ）

**プレイヤーとの会話から学習し、より良いストーリーを生成するインタラクティブノベルゲーム。Gemini AIのファインチューニングを活用して、プレイヤーの高評価応答から学習し、継続的に進化する。**

## 🔍 問題・課題

### 解決したい問題
- **従来のAIゲーム**: 固定的な応答パターン、ユーザーフィードバックを活かせない
- **ストーリーの質**: プレイヤーの好みに合わないストーリー展開
- **エンゲージメント**: 繰り返しプレイしても同じ体験しか得られない

### ターゲットユーザー
- **誰のため**: インタラクティブフィクション愛好家、ゲーマー、教育関係者
- **どんなシーン**:
  - 暇つぶしに創造的なストーリー体験を楽しみたい時
  - 教育現場でのインタラクティブ学習教材として
  - AIの学習能力を体験したいテック愛好家

## 💡 解決策

### コアアイデア
1. **データ収集**: プレイヤーとの会話と評価を記録
2. **品質フィルタリング**: 高評価（★4-5）のインタラクションのみ抽出
3. **ファインチューニング**: Vertex AIで定期的にモデルを更新
4. **継続的改善**: 新しいモデルをデプロイ → より良いストーリー生成

### Gemini 3の活用ポイント
- [x] **Thinking Mode**: 深い推論でストーリーの整合性を保つ
- [ ] **Multimodal**: （将来的に）画像を含むストーリー
- [x] **Tool Use**: データ収集・分析ツールとの統合
- [x] **Fine-tuning**: Vertex AIでのSupervised Fine-tuning

### 差別化要因
- **真のオンライン学習**: 他のAIゲームと異なり、実際にモデルが学習・進化
- **SIMA 2方式の応用**: DeepMindの最先端研究を実用化
- **透明性**: Before/After比較でAIの進化を可視化

## 🎨 主要機能

### MVP（Minimum Viable Product）
1. **インタラクティブストーリー生成**
   - Gemini 3がプレイヤーの選択に応じてストーリーを生成
   - 2-3段落の適度な長さで応答
   - 次の選択肢を提示

2. **データ収集パイプライン**
   - プレイヤーとの会話履歴を自動記録
   - 評価（★1-5）の収集
   - JSONL形式でCloud Storageに保存

3. **ファインチューニング機能**
   - 高評価データの自動抽出
   - Vertex AIでのバッチファインチューニング
   - 新モデルのデプロイ

### 将来的な機能（Nice-to-have）
- [ ] マルチプレイヤー統計（人気の選択肢を表示）
- [ ] パーソナライズド学習（プレイヤーごとにモデル最適化）
- [ ] 画像生成（ストーリーに合わせた挿絵）
- [ ] 音声読み上げ
- [ ] ジャンル選択（ファンタジー、SF、ミステリー等）

## 🏗️ 技術スタック

### フロントエンド
- **Framework**: Next.js 14 (予定)
- **言語**: TypeScript
- **スタイリング**: Tailwind CSS
- **状態管理**: React Hooks / Zustand

### バックエンド
- **Framework**: FastAPI
- **言語**: Python 3.11+
- **Database**: Firestore（セッション管理）
- **Storage**: Google Cloud Storage（訓練データ）

### AI/ML
- **モデル**: Gemini 3 Pro（推論）、Gemini 2.5 Flash（ファインチューニング）
- **サービス**: Vertex AI（ファインチューニング）
- **学習手法**: Supervised Fine-tuning

### インフラ
- **API**: Cloud Run（予定）
- **Frontend**: Vercel（予定）
- **ストレージ**: Cloud Storage
- **モニタリング**: Cloud Logging

## 📐 アーキテクチャ

```
┌─────────────┐
│  Frontend   │ (Next.js / React)
│  Game UI    │
└──────┬──────┘
       │ REST API
       ▼
┌─────────────┐
│  Backend    │ (FastAPI)
│  Game Logic │
└──┬────┬─────┘
   │    │
   │    └──────────────┐
   │                   │
   ▼                   ▼
┌─────────────┐  ┌──────────────┐
│  Gemini API │  │  Firestore   │
│  (Inference)│  │ (Game State) │
└─────────────┘  └──────┬───────┘
                        │
                        ▼
                 ┌──────────────┐
                 │Cloud Storage │
                 │  (Training   │
                 │   Dataset)   │
                 └──────┬───────┘
                        │
                        ▼
                 ┌──────────────┐
                 │  Vertex AI   │
                 │ (Fine-tuning)│
                 └──────────────┘
```

## 📊 データフロー

### プレイ時
1. プレイヤーが選択 → Frontend
2. Frontend → Backend API（`/action`）
3. Backend → Gemini API（ストーリー生成）
4. Gemini応答 → Backend
5. Backend → Firestore（会話履歴保存）
6. Backend → Frontend → プレイヤー
7. プレイヤーが評価（★1-5）→ Backend
8. Backend → Cloud Storage（高評価データ保存）

### 学習時
1. 管理者が `/training/prepare` 呼び出し
2. Backend → Cloud Storageから高評価データ抽出
3. JSONL形式でファインチューニング用データセット作成
4. `training/fine_tune.py` 実行
5. Vertex AIでファインチューニング（数時間）
6. 新モデルをデプロイ
7. ゲームが進化！

## 🎯 成功指標（KPI）

### 技術的指標
- [x] 応答時間: < 3秒（Gemini API）
- [ ] エラー率: < 1%
- [ ] データ収集率: 高評価データ100件以上/週

### ユーザー指標
- [ ] 平均評価: 3.5 → 4.2以上（ファインチューニング後）
- [ ] セッション時間: 8分 → 12分以上
- [ ] 完了率: 45% → 65%以上

### 学習効果指標
- [ ] Before/Afterでの評価改善: +20%以上
- [ ] エンゲージメント向上: +30%以上
- [ ] 選択の多様性: 偏りなく様々な展開を提供

### ハッカソン評価基準
- [x] Gemini 3機能の創造的活用（ファインチューニング）
- [x] 実用性・問題解決力（継続的改善）
- [x] 技術的深さ（データパイプライン + ML）
- [ ] 完成度・デモの質（要フロントエンド）

## 📅 実装スケジュール

### Phase 1: プロトタイプ（Day 1） ✅
- [x] データモデル定義
- [x] 基本ゲームロジック
- [x] データ収集パイプライン
- [x] REST API実装
- [x] ファインチューニングスクリプト

### Phase 2: MVP開発（Day 2）
- [ ] Next.jsフロントエンド実装
- [ ] セッション管理UI
- [ ] 評価システムUI
- [ ] Vertex AIプロジェクト設定
- [ ] Cloud Storageバケット作成

### Phase 3: テスト・学習（Day 2-3）
- [ ] 10-20人でプレイテスト
- [ ] 100-500件のインタラクション収集
- [ ] 初回ファインチューニング実行
- [ ] Before/After比較デモ作成

### Phase 4: 完成・デモ（Day 3）
- [ ] UI/UX改善
- [ ] メトリクスダッシュボード
- [ ] デモビデオ録画
- [ ] プレゼン資料作成

## ✅ 実装状況

### 完了
- [x] アイデア仕様書作成
- [x] 詳細設計ドキュメント（19,000字）
- [x] バックエンド実装（FastAPI）
  - [x] `main.py` - REST API
  - [x] `game_logic.py` - ゲームロジック
  - [x] `data_collector.py` - データ収集
  - [x] `models.py` - データモデル
- [x] ファインチューニングスクリプト
  - [x] `fine_tune.py` - Vertex AI統合
- [x] ドキュメント
  - [x] README.md
  - [x] 設計ドキュメント

### 進行中
- [ ] フロントエンド実装（0%）

### 未着手
- [ ] デプロイ設定
- [ ] モニタリング設定
- [ ] テストコード

## 💰 コスト見積もり

### 開発フェーズ（ハッカソン期間）
- **Gemini API推論**: $9（100プレイヤー × 10ターン想定）
  - 入力: 50万トークン × $2/100万 = $1
  - 出力: 100万トークン × $8/100万 = $8
- **Vertex AI ファインチューニング**: $30（1回）
- **Cloud Storage**: $1
- **Firestore**: $2
- **合計**: 約 **$42**

### 本番運用（想定）
- **月間**: $200-500（1000ユーザー想定）
- **ユーザー単価**: $0.20-0.50/user

## 🚧 課題・リスク

### 技術的課題
1. **ファインチューニング時間**: 数時間かかる
   - 対策: 夜間バッチで実行、プレイヤーには「次回更新で反映」と通知

2. **データ品質**: 低品質データが混入する可能性
   - 対策: 評価★4-5のみ使用、明らかに不適切なデータは手動で除外

3. **コスト管理**: 予想以上のユーザー数でコスト増
   - 対策: Gemini 2.5 Flash使用、レート制限実装

### スケジュールリスク
- **リスク**: フロントエンド実装に時間がかかりすぎる
- **対策**: シンプルなUIに徹する、既存テンプレート活用

## 📚 参考資料

### 公式ドキュメント
- [Vertex AI Supervised Fine-Tuning](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini-use-supervised-tuning)
- [Preparing Training Data](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini-supervised-tuning-prepare)
- [Gemini API Documentation](https://ai.google.dev/gemini-api/docs)

### 参考研究
- [SIMA 2: Gemini-Powered AI Agent](https://deepmind.google/blog/sima-2-an-agent-that-plays-reasons-and-learns-with-you-in-virtual-3d-worlds/)
- [LearnLM: Improving Gemini for Learning](https://arxiv.org/html/2412.16429v1)
- [RLHF in Games](https://en.wikipedia.org/wiki/Reinforcement_learning_from_human_feedback)

### 類似プロジェクト
- [AI Dungeon](https://play.aidungeon.io/): GPT活用のテキストアドベンチャー
  - 違い: 学習機能なし、静的なモデル

## 🔗 関連ファイル

- [README.md](./README.md) - セットアップ・使い方
- [設計ドキュメント](../online-learning-game-design.md) - 詳細設計（19,000字）
- [Backend実装](./backend/) - FastAPI実装
- [Training Scripts](./training/) - ファインチューニング

## 📝 メモ・アイデア

### ブレインストーミング
- **アイデア**: プレイヤー同士でストーリーを共有
- **アイデア**: AIが自動でストーリーの「分岐ポイント」を検出
- **アイデア**: 「週刊モデル更新」として定期的にファインチューニング

### 今後の拡張案
- **マルチエンディング解析**: どの選択肢がどの結末につながるか可視化
- **コミュニティ機能**: 人気のストーリー展開をシェア
- **AI vs AIモード**: 複数のモデルを対戦させて最高のストーリーを競う
- **教育版**: 歴史・科学の学習コンテンツとして

---

**作成者**: Gemini-3-Tokyo-Hackathon Team
**最終更新**: 2026-02-21
