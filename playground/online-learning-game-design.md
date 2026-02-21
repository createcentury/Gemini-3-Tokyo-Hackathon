# Geminiオンライン学習ゲーム - 設計要件書

**プロジェクト目標**: Gemini AIがプレイヤーとのインタラクションから継続的に学習し、進化していく面白いゲームを作る

**最終更新**: 2026年2月21日

---

## 📋 目次
1. [技術的実現可能性の調査結果](#技術的実現可能性の調査結果)
2. [オンライン学習の3つのアプローチ](#オンライン学習の3つのアプローチ)
3. [推奨ゲームジャンル](#推奨ゲームジャンル)
4. [具体的なゲーム設計案](#具体的なゲーム設計案)
5. [技術実装ガイド](#技術実装ガイド)
6. [評価基準とメトリクス](#評価基準とメトリクス)

---

## 技術的実現可能性の調査結果

### ✅ 現在可能なこと

#### 1. **Vertex AI Supervised Fine-Tuning**
- **対応モデル**: Gemini 2.5 Pro/Flash/Flash-Lite、2.0 Flash/Flash-Lite
- **データ要件**: JSONL形式、最低100-500例推奨
- **学習方法**: プレイヤーのインタラクションを収集 → 定期的にファインチューニング
- **制約**: Gemini API/AI Studioでは非対応、Vertex AIのみ

#### 2. **Preference Tuning（人間のフィードバックから学習）**
- **概要**: 主観的なユーザー好みを学習
- **用途**: プレイヤーの選択、評価、ランキングから学習
- **利点**: RLHFと同様のアプローチ、より人間らしい応答

#### 3. **Gemini-based Feedback Loop（SIMA 2方式）**
- **概要**: Gemini自身が報酬推定を行い、自己改善
- **実績**: SIMA 2で実証済み（ゲーム内で自律学習）
- **特徴**:
  - 人間のデモから開始 → 自己プレイで改善
  - Geminiが報酬を推定 → 次の学習に使用
  - 新しい環境でも人間データなしで適応可能

### ⚠️ 制限事項

- **リアルタイム学習は不可**: APIレベルでの即座の重み更新はできない
- **ファインチューニング時間**: 数時間〜数日（データ量次第）
- **コスト**: ファインチューニングと推論の両方でコストが発生
- **Gemini API制限**: 現時点でファインチューニング非対応（Vertex AI必須）

---

## オンライン学習の3つのアプローチ

### アプローチ1: バッチ型ファインチューニング（推奨・実装容易）⭐

**仕組み**:
```
プレイヤーがゲームをプレイ
     ↓
インタラクションデータを収集（JSONL）
     ↓
一定量溜まったら（例: 100-500件）
     ↓
Vertex AIでファインチューニング
     ↓
新しいモデルをデプロイ
     ↓
ゲームが進化！
```

**メリット**:
- ✅ 実装が比較的簡単
- ✅ 公式にサポートされている
- ✅ コスト管理しやすい
- ✅ ハッカソンで実現可能

**デメリット**:
- ⏱️ 即座には反映されない（数時間〜1日のサイクル）
- 💰 ファインチューニングコストがかかる

**最適なゲームタイプ**:
- ストーリーベースのゲーム
- キャラクターとの会話ゲーム
- クイズ・教育ゲーム

---

### アプローチ2: プロンプトベース疑似学習（即座・低コスト）⚡

**仕組み**:
```
プレイヤーがゲームをプレイ
     ↓
インタラクションをデータベースに保存
     ↓
次のプレイ時にプロンプトに含める
     ↓
「過去のプレイヤーは〜を好んだ」という情報を渡す
     ↓
Geminiが文脈から"学習"したように振る舞う
```

**メリット**:
- ✅ 実装が最も簡単
- ✅ 即座に反映
- ✅ ファインチューニング不要
- ✅ コスト最小

**デメリット**:
- ❌ 真の学習ではない（コンテキスト情報として渡すだけ）
- ⚠️ トークン数が増える（コスト増）

**最適なゲームタイプ**:
- マルチプレイヤー統計を使うゲーム
- トレンドを反映するゲーム
- 短期記憶で十分なゲーム

**実装例**:
```python
# 過去のプレイヤーデータを取得
player_stats = get_player_choices()

prompt = f"""
あなたはゲームマスターです。
過去のプレイヤー統計:
- 70%のプレイヤーが「森」を選択
- 「洞窟」選択者の85%が宝箱を発見
- 平均プレイ時間: 15分

現在のプレイヤーに次のステージを提案してください。
"""
```

---

### アプローチ3: Gemini自己改善ループ（SIMA 2方式・高度）🚀

**仕組み**:
```
初期: 人間が作った例でGeminiをファインチューニング
     ↓
Geminiがゲームをプレイ（AIエージェント）
     ↓
Gemini自身が結果を評価（報酬推定）
     ↓
良いプレイデータを収集
     ↓
それを使って次のファインチューニング
     ↓
繰り返し → 自己改善
```

**メリット**:
- ✅ 真のオンライン学習に最も近い
- ✅ 人間の介入を減らせる
- ✅ 最先端の研究と同じアプローチ

**デメリット**:
- 💻 実装が複雑
- 🧠 高度なAI知識が必要
- ⏰ ハッカソンには重い可能性

**最適なゲームタイプ**:
- AIエージェント同士の対戦ゲーム
- シミュレーションゲーム
- 複雑な戦略ゲーム

---

## 推奨ゲームジャンル

### ✨ 最適: 対話型ゲーム

**理由**:
- テキストベース → データ収集が容易
- 会話履歴 → そのままファインチューニングデータ
- ユーザー選択 → 明確なフィードバック

**例**:
1. **インタラクティブノベル**（最推奨）
2. **RPGのNPC会話システム**
3. **謎解きゲーム**
4. **教育系クイズゲーム**

### 🎯 良い: 戦略・判断ゲーム

**例**:
1. **カードバトルゲーム**
   - プレイヤーの戦略 → AIが学習
   - デッキ構成の最適化
2. **マネジメントシミュレーション**
   - 経営判断 → AIがアドバイス
   - 過去の成功/失敗から学習

### △ 難しい: アクションゲーム

**理由**:
- リアルタイム性が求められる
- テキストベースの学習と相性悪い
- 画像・動画処理が必要

---

## 具体的なゲーム設計案

### 案1: 進化するストーリーテラー⭐最推奨

**コンセプト**: プレイヤーとの会話から学習し、より良い物語を紡ぐAIストーリーテラー

#### ゲームフロー
```
1. プレイヤーがストーリーの選択肢を選ぶ
2. Geminiが次の展開を生成
3. プレイヤーが評価（★1-5）
4. データを収集
5. 100人分溜まったら → ファインチューニング
6. 次のバージョンで「より好まれるストーリー」を生成
```

#### データ収集構造
```jsonl
{
  "contents": [
    {
      "role": "user",
      "parts": [{"text": "森に入る"}]
    },
    {
      "role": "model",
      "parts": [{"text": "深い森の中、古びた小屋を見つけた。中から光が漏れている..."}]
    },
    {
      "role": "user",
      "parts": [{"text": "小屋に入る"}]
    }
  ],
  "rating": 5,
  "player_choice": "entered_cabin",
  "story_outcome": "positive"
}
```

#### 学習メトリクス
- **高評価率**: ★4-5の割合
- **継続率**: プレイヤーが最後まで遊んだか
- **選択の多様性**: 同じ選択肢ばかりでないか

#### ファインチューニング戦略
```python
# 高評価のストーリーのみを学習データに
filtered_data = [
    example for example in all_data
    if example["rating"] >= 4
]

# Vertex AIでファインチューニング
tune_gemini(
    model="gemini-2.5-flash",
    training_data=filtered_data,
    validation_split=0.2
)
```

---

### 案2: AI先生ゲーム（教育系）

**コンセプト**: プレイヤーの理解度から学習し、最適な教え方を見つけるAI先生

#### 特徴
- プレイヤーの正答/誤答パターンを学習
- 説明の仕方を改善（簡単すぎ/難しすぎを調整）
- 個別最適化された学習体験

#### データ収集
```jsonl
{
  "systemInstruction": {
    "role": "system",
    "parts": [{"text": "あなたは数学を教える先生です"}]
  },
  "contents": [
    {
      "role": "user",
      "parts": [{"text": "2次方程式がわかりません"}]
    },
    {
      "role": "model",
      "parts": [{"text": "まず、ax²+bx+c=0の形を覚えましょう..."}]
    }
  ],
  "student_understood": true,
  "time_to_understand": 120,
  "difficulty_rating": "appropriate"
}
```

---

### 案3: AIダンジョンマスター

**コンセプト**: TRPGのゲームマスターとしてプレイヤーの行動に応じて即興でストーリーを展開

#### ハイブリッドアプローチ
1. **即時応答**: プロンプトベース（アプローチ2）
2. **長期学習**: バッチファインチューニング（アプローチ1）

```python
# セッション中（即時）
current_context = load_session_history()
prompt = f"""
過去のセッション統計:
- プレイヤーは戦闘より謎解きを好む傾向（70%）
- ダーク系ストーリーの評価が高い（平均4.2/5）

現在の状況: {current_context}
プレイヤーの行動: {player_action}

次の展開を提案してください。
"""

# 週次（学習）
weekly_fine_tuning(
    high_rated_sessions
)
```

---

### 案4: キャラクター育成ゲーム

**コンセプト**: AIキャラクターがプレイヤーとの会話から「性格」を学習

#### 仕組み
```
初期: 汎用的な性格
     ↓
プレイヤーとの会話を記録
     ↓
プレイヤーの好みの応答スタイルを学習
     ↓
そのプレイヤー専用のキャラクターに進化
```

#### パーソナライズド学習
```jsonl
{
  "systemInstruction": {
    "role": "system",
    "parts": [{"text": "あなたは冒険者の相棒です。このプレイヤーは真面目な会話を好みます。"}]
  },
  "contents": [...],
  "player_preference": "serious_tone",
  "engagement_score": 8.5
}
```

---

## 技術実装ガイド

### 必要なGCPサービス

```yaml
必須:
  - Vertex AI (ファインチューニング用)
  - Cloud Storage (データセット保存)
  - Gemini API (推論用)

推奨:
  - Firestore (プレイヤーデータ保存)
  - Cloud Functions (自動化)
  - BigQuery (分析)
```

### アーキテクチャ図

```
┌─────────────┐
│  Frontend   │ (Next.js / React)
│  Game UI    │
└──────┬──────┘
       │ API calls
       ▼
┌─────────────┐
│  Backend    │ (FastAPI / Node.js)
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

### データ収集パイプライン

```python
# game_backend/data_collector.py

from typing import List, Dict
import json
from datetime import datetime
from google.cloud import storage

class GameDataCollector:
    """プレイヤーとのインタラクションを収集"""

    def __init__(self):
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket('your-game-data')
        self.buffer = []

    def record_interaction(
        self,
        player_id: str,
        conversation: List[Dict],
        metadata: Dict
    ):
        """1つのインタラクションを記録"""
        data_point = {
            "player_id": player_id,
            "timestamp": datetime.utcnow().isoformat(),
            "contents": conversation,
            "rating": metadata.get("rating"),
            "choice": metadata.get("choice"),
            "outcome": metadata.get("outcome")
        }

        self.buffer.append(data_point)

        # 100件溜まったらCloud Storageに保存
        if len(self.buffer) >= 100:
            self.flush_to_storage()

    def flush_to_storage(self):
        """バッファをCloud Storageに保存"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        blob = self.bucket.blob(f'training_data/{timestamp}.jsonl')

        # JSONL形式で保存
        jsonl_content = '\n'.join(
            json.dumps(item, ensure_ascii=False)
            for item in self.buffer
        )

        blob.upload_from_string(jsonl_content)
        self.buffer.clear()

        print(f"✅ Saved {len(self.buffer)} interactions to Cloud Storage")

    def prepare_for_tuning(self, min_rating: int = 4):
        """ファインチューニング用にデータをフィルタリング"""
        all_files = self.bucket.list_blobs(prefix='training_data/')

        high_quality_data = []

        for blob in all_files:
            content = blob.download_as_text()
            for line in content.split('\n'):
                if not line:
                    continue
                data = json.loads(line)

                # 高評価のデータのみ
                if data.get('rating', 0) >= min_rating:
                    high_quality_data.append({
                        'contents': data['contents']
                    })

        # ファインチューニング用JSONLとして保存
        tuning_blob = self.bucket.blob('tuning_ready/dataset.jsonl')
        tuning_content = '\n'.join(
            json.dumps(item, ensure_ascii=False)
            for item in high_quality_data
        )
        tuning_blob.upload_from_string(tuning_content)

        return f"gs://{self.bucket.name}/tuning_ready/dataset.jsonl"
```

### ファインチューニング実行

```python
# training/fine_tune.py

from google.cloud import aiplatform

def fine_tune_gemini(
    training_data_uri: str,
    model_name: str = "gemini-2.5-flash"
):
    """Vertex AIでGeminiをファインチューニング"""

    aiplatform.init(
        project="your-project-id",
        location="us-central1"
    )

    # ファインチューニングジョブの作成
    tuning_job = aiplatform.SupervisedTuningJob.create(
        model=model_name,
        training_data_uri=training_data_uri,
        validation_data_uri=None,  # オプション
        tuning_config={
            "epoch_count": 3,
            "learning_rate_multiplier": 1.0,
            "adapter_size": "ADAPTER_SIZE_SIXTEEN"  # 4, 8, 16, 32
        }
    )

    print(f"🚀 Fine-tuning job started: {tuning_job.resource_name}")

    # ジョブの完了を待つ（数時間かかる可能性）
    tuning_job.wait()

    print(f"✅ Fine-tuning complete!")
    print(f"Tuned model endpoint: {tuning_job.tuned_model_endpoint_name}")

    return tuning_job.tuned_model_endpoint_name
```

### ゲームロジック例

```python
# game_backend/game_logic.py

import google.generativeai as genai
from data_collector import GameDataCollector

class AdaptiveStoryGame:
    """学習するストーリーゲーム"""

    def __init__(self, model_name="gemini-3-pro"):
        self.model = genai.GenerativeModel(model_name)
        self.collector = GameDataCollector()
        self.sessions = {}

    def start_session(self, player_id: str):
        """新しいゲームセッション開始"""
        self.sessions[player_id] = {
            "chat": self.model.start_chat(),
            "history": [],
            "choices": []
        }

        intro = self.sessions[player_id]["chat"].send_message(
            "新しい冒険を始めましょう。どんな冒険者になりたいですか？"
        )

        return intro.text

    def player_action(
        self,
        player_id: str,
        action: str,
        rating: int = None
    ):
        """プレイヤーのアクション処理"""
        session = self.sessions[player_id]

        # Geminiに送信
        response = session["chat"].send_message(action)

        # 履歴に追加
        session["history"].append({
            "role": "user",
            "parts": [{"text": action}]
        })
        session["history"].append({
            "role": "model",
            "parts": [{"text": response.text}]
        })

        # 評価があればデータ収集
        if rating:
            self.collector.record_interaction(
                player_id=player_id,
                conversation=session["history"][-2:],  # 直近の会話
                metadata={
                    "rating": rating,
                    "choice": action
                }
            )

        return response.text

    def end_session(self, player_id: str, final_rating: int):
        """セッション終了時にデータ保存"""
        session = self.sessions[player_id]

        # 全体の会話を記録
        self.collector.record_interaction(
            player_id=player_id,
            conversation=session["history"],
            metadata={
                "rating": final_rating,
                "session_length": len(session["history"]) / 2
            }
        )

        del self.sessions[player_id]
```

---

## 評価基準とメトリクス

### 学習効果の測定

#### 1. プレイヤー満足度
```python
# 平均評価の向上を追跡
metrics = {
    "version_1_avg_rating": 3.2,
    "version_2_avg_rating": 3.8,  # ファインチューニング後
    "version_3_avg_rating": 4.1,  # さらに学習後
    "improvement": "+28%"
}
```

#### 2. エンゲージメント
```python
# セッション時間・継続率
metrics = {
    "avg_session_time_v1": "8分",
    "avg_session_time_v2": "12分",  # 改善
    "completion_rate_v1": "45%",
    "completion_rate_v2": "68%"     # 改善
}
```

#### 3. 選択の多様性
```python
# AIの応答が単調でないか
diversity_score = unique_responses / total_responses
```

### A/Bテスト設計

```python
# 50%のプレイヤーに元のモデル、50%に新モデル
def get_model_for_player(player_id: str):
    if hash(player_id) % 2 == 0:
        return "gemini-3-pro"  # ベースライン
    else:
        return "gemini-3-pro-tuned-v2"  # ファインチューニング版
```

---

## 実装スケジュール（ハッカソン用）

### Day 1: 基礎実装
- [ ] ゲームの基本UI（Next.js）
- [ ] Gemini APIとの接続
- [ ] データ収集パイプライン
- [ ] Firestore統合

### Day 2: データ収集・学習準備
- [ ] プロトタイプで実際にプレイして データ収集
- [ ] JSONL形式への変換
- [ ] Vertex AIセットアップ
- [ ] 初回ファインチューニング実行（時間がかかるので早めに）

### Day 3: 改善・デモ準備
- [ ] ファインチューニング済みモデルのデプロイ
- [ ] Before/Afterの比較デモ
- [ ] メトリクスダッシュボード
- [ ] プレゼン資料作成

---

## コスト見積もり

### Vertex AI ファインチューニング
- **学習**: 約$10-50（データ量・エポック数次第）
- **推論**: 通常のGemini API料金

### 推論コスト（Gemini 3.1 Pro）
- **入力**: $2 / 100万トークン
- **出力**: $8 / 100万トークン

### 参考: 100プレイヤー × 10ターン
- 入力トークン: 約50万（$1）
- 出力トークン: 約100万（$8）
- **合計**: 約$9 + ファインチューニング$30 = **$39程度**

**ハッカソン期間なら十分現実的！**

---

## 参考文献

### 公式ドキュメント
- [Vertex AI Supervised Fine-Tuning](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini-use-supervised-tuning)
- [Preparing Training Data](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini-supervised-tuning-prepare)
- [Gemini API Documentation](https://ai.google.dev/gemini-api/docs)

### 研究・事例
- [SIMA 2: Gemini-Powered AI Agent](https://deepmind.google/blog/sima-2-an-agent-that-plays-reasons-and-learns-with-you-in-virtual-3d-worlds/)
- [Genie 3: World Model](https://deepmind.google/models/genie/)
- [RLHF in Games](https://en.wikipedia.org/wiki/Reinforcement_learning_from_human_feedback)
- [LearnLM: Improving Gemini for Learning](https://arxiv.org/html/2412.16429v1)

---

## 次のステップ

1. **アプローチを選ぶ**:
   - ハッカソン → アプローチ1（バッチファインチューニング）推奨
   - プロトタイプ → アプローチ2（プロンプトベース）で素早く検証

2. **ゲームジャンルを決定**:
   - 最推奨: インタラクティブノベル/ストーリーゲーム

3. **技術検証**:
   - Vertex AIアカウント作成
   - 小規模データでファインチューニングテスト

4. **POC作成**:
   - `playground/online-learning-game/` 配下で実装開始

**Good luck! 🎮🤖**
