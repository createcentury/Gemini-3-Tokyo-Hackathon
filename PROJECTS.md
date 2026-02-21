# プロジェクト一覧

Gemini 3 Tokyo Hackathon で開発中のプロジェクト・POC一覧

**最終更新**: 2026年2月21日

---

## 📋 目次
- [概要](#概要)
- [実装済みプロジェクト](#実装済みプロジェクト)
- [ドキュメント・リソース](#ドキュメントリソース)
- [技術スタック](#技術スタック)
- [開発ガイドライン](#開発ガイドライン)

---

## 概要

このリポジトリは、Gemini 3 Tokyo Hackathonに向けた実験・POC・プロジェクトの集約場所です。
各プロジェクトは`playground/`配下に独立したディレクトリとして管理されています。

### プロジェクト数
- **実装済み**: 2
- **設計中**: 0
- **アイデア段階**: 10+ (hackathon-ideas.md参照)

---

## 実装済みプロジェクト

### 1. Online Learning Game 🎮🤖

**Status**: ✅ Backend実装完了 | 🚧 Frontend未実装

#### 概要
プレイヤーとのインタラクションから学習し、継続的に進化するインタラクティブストーリーゲーム。
Gemini AIが高評価の応答パターンを学習し、より魅力的なストーリーを生成できるようになる。

#### ディレクトリ
```
playground/online-learning-game/
├── backend/              # FastAPI実装
├── training/             # Vertex AIファインチューニングスクリプト
└── README.md
```

#### 技術スタック
- **Backend**: FastAPI, Python 3.11+
- **AI**: Gemini 3 Pro (Vertex AI)
- **Storage**: Google Cloud Storage
- **Database**: Firestore (オプション)

#### 主要機能
1. **データ収集パイプライン**
   - プレイヤーとの会話を自動記録
   - 高評価(★4-5)のインタラクションを抽出
   - JSONL形式でCloud Storageに保存

2. **学習サイクル**
   - バッチファインチューニング（100-500例）
   - Vertex AIでモデル更新
   - 新モデルの自動デプロイ

3. **ゲームロジック**
   - 適応型ストーリー生成
   - プレイヤー評価の収集
   - セッション管理

#### API エンドポイント
```
POST /session/start       # セッション開始
POST /action             # プレイヤーアクション
POST /session/end        # セッション終了
GET  /stats              # データ統計
POST /training/prepare   # ファインチューニングデータ準備
```

#### 実装状況
- [x] データモデル定義
- [x] データ収集パイプライン
- [x] ゲームロジック
- [x] REST API
- [x] ファインチューニングスクリプト
- [ ] フロントエンドUI
- [ ] デプロイ設定

#### 関連ドキュメント
- [詳細設計書](./playground/online-learning-game-design.md)
- [README](./playground/online-learning-game/README.md)
- [Idea Spec](./playground/online-learning-game/IDEA_SPEC.md)

#### コスト見積もり
- **開発・テスト**: $40程度（100プレイヤー想定）
- **ファインチューニング**: $10-50/回
- **推論**: Gemini 3.1 Pro - $2/100万入力トークン

#### 次のステップ
1. [ ] Next.jsフロントエンド実装
2. [ ] Vertex AIプロジェクト設定
3. [ ] 初回プレイテスト（10-20人）
4. [ ] 初回ファインチューニング実行

---

### 2. API Examples 📚

**Status**: ✅ 完成

#### 概要
Gemini 3 APIの主要機能を実演するサンプルコード集。
ハッカソン参加者がすぐに使えるコードテンプレート。

#### ディレクトリ
```
playground/api-examples/
├── python/
│   ├── basic_chat.py
│   ├── thinking_mode.py
│   ├── multimodal_analysis.py
│   ├── function_calling.py
│   └── requirements.txt
└── README.md
```

#### サンプル一覧

| ファイル | 機能 | 難易度 |
|---------|------|--------|
| `basic_chat.py` | 基本的なチャット機能 | ★☆☆ |
| `thinking_mode.py` | Thinking Control（思考の深さ制御） | ★★☆ |
| `multimodal_analysis.py` | 画像+テキストの統合分析 | ★★☆ |
| `function_calling.py` | カスタムツール定義と使用 | ★★★ |

#### 技術スタック
- **言語**: Python 3.11+
- **ライブラリ**: google-generativeai, python-dotenv, Pillow

#### 使い方
```bash
cd playground/api-examples/python
pip install -r requirements.txt
cp ../.env.example ../.env
# .envにAPIキー設定
python basic_chat.py
```

#### 実装状況
- [x] 基本チャット
- [x] Thinking Mode
- [x] マルチモーダル分析
- [x] Function Calling
- [ ] Streaming応答
- [ ] JavaScript版

#### 関連ドキュメント
- [README](./playground/api-examples/README.md)

---

## ドキュメント・リソース

### 📖 研究・設計ドキュメント

#### 1. Gemini Research Overview
**ファイル**: `playground/gemini-research-overview.md`

**内容**:
- Gemini 2.5の技術革新（5倍のコーディング性能向上等）
- Gemini Deep Thinkの科学研究応用（IMO金メダル水準）
- Gemini 3のベンチマーク結果
- Googleの研究方向性分析

**文字数**: ~8,000字

#### 2. Hackathon Ideas
**ファイル**: `playground/hackathon-ideas.md`

**内容**:
- 4つのトラック別プロジェクトアイデア（全12案）
- 最新API機能の解説（Thinking Level, Thought Signatures等）
- 技術スタック推奨
- 実装ベストプラクティス

**文字数**: ~15,000字

#### 3. Online Learning Game Design
**ファイル**: `playground/online-learning-game-design.md`

**内容**:
- オンライン学習の3つのアプローチ
- 技術的実現可能性の調査
- 具体的なゲーム設計案
- 完全な実装ガイド

**文字数**: ~19,000字

### 📐 プロジェクト管理ドキュメント

#### 1. Branch Strategy (CONTRIBUTING.md)
- 3つのブランチ戦略オプション
- ハッカソン向け推奨ワークフロー
- Gitコミットメッセージテンプレート

#### 2. Project Structure (この文書)
- 全プロジェクト一覧
- 技術スタック
- 実装状況

---

## 技術スタック

### 使用中の技術

#### AI/ML
- **Gemini 3 Pro**: メイン推論モデル
- **Gemini 3.1 Pro**: 長コンテキスト版（1M tokens）
- **Gemini 2.5 Flash**: 高速・低コスト版
- **Vertex AI**: ファインチューニング

#### バックエンド
- **Python 3.11+**
- **FastAPI**: REST API
- **Google Cloud SDK**: GCP統合

#### フロントエンド（予定）
- **Next.js 14+**: React framework
- **TypeScript**: 型安全性
- **Tailwind CSS**: スタイリング

#### インフラ
- **Google Cloud Storage**: データ保存
- **Firestore**: NoSQLデータベース
- **Vertex AI**: MLオペレーション

#### 開発ツール
- **Git**: バージョン管理
- **dotenv**: 環境変数管理
- **uvicorn**: ASGI server

---

## 開発ガイドライン

### 新しいPOCを始める

#### 1. Idea Specを作成
```bash
cp playground/example-poc/IDEA_SPEC.md playground/my-new-poc/
# IDEA_SPEC.mdを編集
```

#### 2. プロジェクト構造を作成
```bash
mkdir -p playground/my-new-poc/{src,tests,docs}
cd playground/my-new-poc
```

#### 3. READMEを作成
```bash
# README.mdに以下を含める:
# - 何を作るか（1-2文）
# - セットアップ手順
# - 使い方
# - 技術スタック
```

#### 4. 開発開始
```bash
# 自由に実装
git add .
git commit -m "Add: my-new-poc initial implementation"
git push origin main
```

### コードの品質基準

#### 必須
- [x] README.mdがある
- [x] 環境変数は.env.exampleで管理
- [x] requirements.txt/package.jsonがある

#### 推奨
- [ ] IDEA_SPEC.mdで設計を文書化
- [ ] コメントは日本語でOK
- [ ] エラーハンドリング

#### オプション
- [ ] テストコード
- [ ] 型ヒント（Python）/TypeScript
- [ ] Docker化

### データ管理

#### APIキー・機密情報
```bash
# ❌ 絶対にコミットしない
GEMINI_API_KEY=secret_key

# ✅ .envファイルに保存（.gitignore済み）
# ✅ .env.exampleをテンプレートとして提供
```

#### 大きなファイル
```bash
# ❌ Git管理しない
*.mp4, *.zip, *.tar.gz, large_dataset.json

# ✅ Cloud Storageにアップロード
# ✅ README.mdにダウンロードリンク記載
```

---

## プロジェクト選定基準

### ハッカソンで評価されるポイント

#### 1. Gemini 3の機能活用度
- [ ] Multimodal（画像・動画・テキスト統合）
- [ ] Thinking Mode（深い推論）
- [ ] Tool Use（Function Calling）
- [ ] Long Context（1M+ tokens）

#### 2. 実用性
- [ ] 実際の問題を解決する
- [ ] ユーザーに明確な価値
- [ ] スケーラビリティ

#### 3. 技術的深さ
- [ ] 単純なAPI呼び出し以上
- [ ] データパイプライン構築
- [ ] 創造的な実装

#### 4. 完成度
- [ ] 動作するデモ
- [ ] エラーハンドリング
- [ ] UX/UIの配慮

---

## メトリクス

### リポジトリ統計

| 項目 | 値 |
|------|-----|
| **総プロジェクト数** | 2（実装済み） |
| **総ドキュメント** | 6ファイル |
| **総コード行数** | ~2,000行 |
| **サンプルコード** | 4ファイル |
| **設計アイデア** | 12案 |

### 開発進捗

```
調査・設計: ████████████████████ 100%
POC実装:    ██████████░░░░░░░░░░  50%
フロント:   ░░░░░░░░░░░░░░░░░░░░   0%
デプロイ:   ░░░░░░░░░░░░░░░░░░░░   0%
```

---

## 次のマイルストーン

### Short-term (今週)
- [ ] Online Learning Gameのフロントエンド実装
- [ ] Vertex AIプロジェクト設定
- [ ] 初回プレイテスト

### Mid-term (ハッカソンまで)
- [ ] 2-3個の追加POC実装
- [ ] デモビデオ作成
- [ ] プレゼン資料作成

### Long-term (ハッカソン後)
- [ ] 優勝プロジェクトの本格開発
- [ ] オープンソース化
- [ ] 論文執筆（研究成果があれば）

---

## 貢献者

- **あなた** - プロジェクトオーナー
- **Claude Sonnet 4.5** - 設計・実装支援

---

## ライセンス

TBD

---

**最終更新**: 2026年2月21日
