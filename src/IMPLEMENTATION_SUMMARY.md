# Tokyo Risk - Multi-Agent System Implementation Summary

## 実装完了 ✅

10体の自律AIエージェント（兵士）を各プレイヤーとAIに追加する多体エージェントシステムが完全実装されました。

---

## 実装された機能

### Phase 1: 基本データ構造とUI ✅

#### 1. Agent エンティティ (game_engine.py)
```python
class Agent:
    - id: "player_001" ~ "player_010", "ai_001" ~ "ai_010"
    - owner: PLAYER or AI
    - system_prompt: ユーザーが設定した戦略プロンプト
    - 位置情報: lat, lng, destination, speed
    - 状態: state (idle, moving, attacking, defending, patrolling)
    - health: 体力
    - target_ward: 目標とする区
    - conversation_history: AI対話履歴
    - last_action_time: 最後の行動時刻
```

**主要メソッド:**
- `update_position()`: 目的地に向かって自動移動
- `set_destination()`: 目的地を設定して移動開始
- `to_dict()`: フロントエンド用にシリアライズ

#### 2. GameState 拡張
```python
- agents: dict[str, Agent]  # エージェント管理辞書
- setup_agents(): 10体ずつのエージェントを初期化
- serialize(): エージェント情報を含む
- player_wards, ai_wards: プロパティとして実装
```

#### 3. プロンプト設定UI (index.html)
- ダイアログ形式で表示
- 全体戦略プロンプト設定
- 個別エージェントプロンプト設定 (10体分)
- リアルタイム予算管理表示

### Phase 2: リアルタイム移動 ✅

#### 1. API エンドポイント
```
GET /game/agents/{session_id}
  → 全エージェントの現在位置を返す
  → 200ms間隔でフロントエンドからポーリング
```

#### 2. フロントエンド更新システム
```javascript
startAgentUpdates()
  → 200ms間隔でエージェント位置を取得
  → updateAgentMarkers() で マーカー位置を更新
  → calculateHeading() で進行方向を計算
  → 矢印マーカーが進行方向に回転
```

#### 3. エージェントマーカー
- 青い矢印: プレイヤーのエージェント
- 赤い矢印: AIのエージェント
- ラベル表示: "001", "002"など
- クリック時に詳細情報を表示
- スムーズな位置更新とアニメーション

### Phase 3: AI意思決定 ✅

#### 1. agent_ai.py モジュール
```python
class AgentAI:
    - decide_action(): エージェントの次の行動を決定
    - _get_situation_summary(): ゲーム全体の状況要約
    - _get_nearby_agents(): 周辺エージェント検出
    - _parse_response(): Geminiレスポンス解析
```

#### 2. Gemini Function Calling 統合
```python
AGENT_FUNCTIONS = [
    move_to_location    # 緯度経度指定の移動
    move_to_ward        # 区への移動
    patrol_area         # 周辺巡回
    ask_commander       # コマンダーへの質問
    attack_enemy        # 敵エージェント攻撃
]
```

#### 3. エージェントAIループ (server.py)
```python
run_agent_ai_loop():
    - 0.5秒ごとに全エージェントの位置を更新
    - 5秒ごとに各エージェントが行動判断
    - 10体中3体だけがGemini API使用（コスト削減）
    - 残り7体はルールベースで行動
```

#### 4. 行動実装
- **Gemini API**: 001-003番のエージェントが自律的に判断
- **ルールベース**: 004-010番のエージェントがランダム移動
- **実行関数**: execute_agent_action() で行動を実際に実行

---

## アーキテクチャ

### バックエンド構成
```
server.py
├── POST /game/start
│   ├── プロンプト受け取り (player_prompts)
│   ├── GameState.setup_agents() でエージェント初期化
│   └── run_agent_ai_loop() をバックグラウンドタスクとして起動
│
├── GET /game/agents/{session_id}
│   └── 全エージェント位置を返却
│
└── run_agent_ai_loop() (AsyncIO Task)
    ├── while not victory:
    │   ├── 全エージェントの位置を0.5秒ごとに更新
    │   └── 5秒ごとに行動判断
    │       ├── 001-003: AgentAI.decide_action() → Gemini API
    │       └── 004-010: ルールベース（ランダム移動）
    └── execute_agent_action() で行動実行
```

### フロントエンド構成
```
index.html
├── showPromptConfigDialog()
│   ├── プロンプト入力UI表示
│   └── 10体分の個別設定
│
├── savePrompts()
│   ├── プロンプトをリストに変換
│   └── POST /game/start に送信
│
├── startAgentUpdates()
│   └── setInterval(200ms)
│       └── GET /game/agents/{session_id}
│
└── updateAgentMarkers()
    ├── 既存マーカーの位置更新
    ├── 新規マーカー作成
    ├── 進行方向に回転
    └── クリックイベント登録
```

---

## コスト最適化

### 実装済み施策
1. **選択的API使用**: 10体中3体だけがGemini APIを使用
2. **ルールベース行動**: 残り7体はシンプルなルールで行動
3. **低頻度判断**: 5秒ごとに行動判断（高頻度な位置更新は不要）
4. **軽量モデル**: gemini-3-flash-preview 使用

### コスト試算
```
API使用エージェント: 3体 × 2陣営 = 6体
判断頻度: 5秒ごと = 毎分12回
1ゲーム30分 = 約360回のAPI呼び出し

Flash料金 (仮定): $0.00001/request
→ 約 $0.0036/ゲーム
```

---

## 技術スタック

### Backend
- **FastAPI**: REST API + WebSocket準備済み
- **Gemini 3 Flash**: AI意思決定エンジン
- **AsyncIO**: バックグラウンドタスク管理
- **Pydantic**: データバリデーション

### Frontend
- **Google Maps JavaScript API**: 地図表示
- **Vanilla JavaScript**: エージェントマーカー管理
- **Polling (200ms)**: リアルタイム位置更新

---

## 使用方法

### 1. サーバー起動
```bash
cd /Users/soki/Gemini-3-Tokyo-Hackathon/playground/tokyo-risk
uvicorn server:app --port 8766 --reload
```

### 2. ブラウザアクセス
```
http://localhost:8766
```

### 3. ゲーム開始手順
1. **ゲーム開始ボタンクリック**
2. **プロンプト設定ダイアログ表示**
   - 全体戦略プロンプトを入力
   - 各エージェントの個別指示を入力（オプション）
3. **「保存してゲーム開始」をクリック**
4. **エージェント観察**
   - 地図上に20個の矢印マーカーが表示
   - 青: プレイヤー、赤: AI
   - 自動的に移動開始

### 4. エージェント確認
- **マーカークリック**: エージェント情報表示
- **自動更新**: 200ms間隔で位置更新
- **回転**: 進行方向を向く

---

## テスト

### 自動テストスクリプト
```bash
python test_agents.py
```

**テスト内容:**
1. ゲーム開始（プロンプト送信）
2. エージェント状態取得
3. 10秒後の移動確認

---

## 実装ファイル

```
tokyo-risk/
├── game_engine.py              # Agent クラス、GameState 拡張
├── agent_ai.py                 # 新規: AI意思決定ロジック
├── server.py                   # エージェントエンドポイント追加
├── index.html                  # プロンプトUI、エージェントマーカー
├── ward_data.py                # 区データ（WARD_LATLNG使用）
├── test_agents.py              # 新規: 自動テストスクリプト
├── AGENT_SYSTEM_README.md      # 詳細ドキュメント
└── IMPLEMENTATION_SUMMARY.md   # このファイル
```

---

## 動作確認済み機能

- ✅ プロンプト設定ダイアログの表示
- ✅ 10体×2陣営=20体のエージェント初期化
- ✅ エージェントマーカーの表示（青/赤の矢印）
- ✅ リアルタイム位置更新（200ms間隔）
- ✅ 移動方向への矢印回転
- ✅ エージェント情報表示（クリック時）
- ✅ Gemini APIによる行動決定（001-003番）
- ✅ ルールベース行動（004-010番）
- ✅ バックグラウンドAIループの安定動作
- ✅ セッション管理
- ✅ エラーハンドリング

---

## 今後の拡張可能性

### Phase 4: 対話システム（計画済み・未実装）
- [ ] エージェント→コマンダー質問機能の統合
- [ ] コマンダー→エージェント命令機能
- [ ] AIチャットとの統合
- [ ] エージェント間通信

### Phase 5: 戦闘・勝敗判定（計画済み・未実装）
- [ ] エージェント間戦闘ロジック
- [ ] 区占領ロジック（エージェントが区に到達したら占領）
- [ ] エージェント体力減少
- [ ] 勝敗条件調整（エージェント数を考慮）

### パフォーマンス最適化
- [ ] WebSocket実装（ポーリング→リアルタイム通信）
- [ ] 画面外エージェントの更新頻度削減
- [ ] エージェント協調行動アルゴリズム
- [ ] キャッシング戦略

---

## トラブルシューティング

### エージェントが表示されない
```bash
# サーバーログ確認
tail -f server_agent.log

# ブラウザコンソール確認
F12 → Console

# エンドポイント確認
curl http://localhost:8766/game/agents/{session_id}
```

### エージェントが動かない
- AIループが起動しているか: ログに "[AgentAI] ループ開始" 表示
- エージェントの state が "moving" になっているか
- destination が設定されているか

### Gemini APIエラー
- .env に GEMINI_API_KEY が設定されているか
- モデル名が正しいか: "gemini-3-flash-preview"
- API制限に達していないか

---

## まとめ

Tokyo Risk の**プロンプトエンジニアリング対戦**というコアメカニクスを実現するため、以下を完全実装しました：

1. ✅ **10体×2陣営のエージェント管理**
2. ✅ **カスタムプロンプト設定システム**
3. ✅ **リアルタイム移動・描画**
4. ✅ **Gemini APIによる自律的意思決定**
5. ✅ **コスト最適化（選択的API使用）**

Phase 1-3が完全動作し、Phase 4-5は今後実装可能な状態です。

**ゲームにアクセス**: http://localhost:8766

---

**実装日**: 2026-02-21
**実装者**: Claude Code (Sonnet 4.5)
