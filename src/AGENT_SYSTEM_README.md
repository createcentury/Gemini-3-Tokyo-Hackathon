# Tokyo Risk - Multi-Agent System 実装完了

## 実装内容

### Phase 1: 基本データ構造とUI ✅
- `Agent` クラス作成 (game_engine.py)
  - 位置情報 (lat, lng)
  - 状態管理 (idle, moving, attacking, defending, patrolling)
  - 目的地設定と移動ロジック
  - 会話履歴保持

- `GameState.agents` フィールド追加
  - エージェント管理辞書
  - setup_agents() メソッド
  - serialize() にエージェント情報を追加

- プロンプト設定UI作成 (index.html)
  - 全体戦略プロンプト設定
  - 個別エージェントプロンプト設定 (10体分)
  - ダイアログ形式で表示

### Phase 2: リアルタイム移動 ✅
- `/game/agents/{session_id}` エンドポイント
  - 全エージェントの現在位置を返す

- フロントエンドポーリング実装
  - 200ms間隔でエージェント位置を取得
  - agentUpdateInterval による自動更新

- エージェント位置更新ロジック
  - Agent.update_position() メソッド
  - 目的地に向かって自動移動

- マーカー回転
  - calculateHeading() で移動方向を計算
  - 矢印マーカーが進行方向を向く

### Phase 3: AI意思決定 ✅
- `agent_ai.py` 作成
  - AgentAI クラス
  - decide_action() メソッド
  - _get_situation_summary() - ゲーム全体の状況要約
  - _get_nearby_agents() - 周辺エージェント検出

- Gemini Function Calling 統合
  - move_to_location - 緯度経度指定の移動
  - move_to_ward - 区への移動
  - patrol_area - 周辺巡回
  - ask_commander - コマンダーへの質問
  - attack_enemy - 敵エージェント攻撃

- エージェントAIループ実装
  - run_agent_ai_loop() 非同期タスク
  - 5秒ごとに各エージェントが行動判断
  - コスト削減: 10体中3体だけがGemini API使用、残りはルールベース

- 基本行動実装
  - move_to_ward - 区への移動
  - patrol - ランダム巡回
  - ルールベース移動 - 近くの区へのランダム移動

## 使用方法

### 1. サーバー起動
```bash
cd /Users/soki/Gemini-3-Tokyo-Hackathon/playground/tokyo-risk
uvicorn server:app --port 8766 --reload
```

### 2. ブラウザでアクセス
```
http://localhost:8766
```

### 3. ゲーム開始
1. 「ゲーム開始」ボタンをクリック
2. プロンプト設定ダイアログが表示される
3. 全体戦略プロンプトを設定
4. 必要に応じて個別エージェントのプロンプトを設定
5. 「保存してゲーム開始」をクリック

### 4. エージェント観察
- 地図上に青い矢印（プレイヤー）と赤い矢印（AI）が表示される
- 矢印は自動的に移動し、進行方向を向く
- エージェントをクリックすると情報が表示される

## アーキテクチャ

### バックエンド
```
server.py
├── /game/start (POST)
│   ├── プロンプト受け取り
│   ├── エージェント初期化
│   └── AIループ起動
│
├── /game/agents/{session_id} (GET)
│   └── 全エージェント位置返却
│
└── run_agent_ai_loop() (バックグラウンドタスク)
    ├── 0.5秒ごとに位置更新
    └── 5秒ごとに行動判断
```

### フロントエンド
```
index.html
├── showPromptConfigDialog()
│   └── プロンプト設定UI表示
│
├── savePrompts()
│   └── プロンプトをサーバーに送信
│
├── startAgentUpdates()
│   └── 200ms間隔でポーリング
│
└── updateAgentMarkers()
    ├── マーカー位置更新
    └── 回転角度更新
```

## コスト最適化

### 実装済み
- **選択的Gemini API使用**: 10体中3体だけがGemini APIを使用
- **ルールベース行動**: 残り7体はシンプルなルールで行動
- **低頻度更新**: 5秒ごとに行動判断（API呼び出しを削減）
- **gemini-2.0-flash-exp使用**: 安価なモデルを使用

### 推定コスト
- 3体 × 2陣営 = 6体がGemini API使用
- 5秒ごと = 毎分12回
- 1ゲーム30分 = 約360回
- Flash料金 (仮定): $0.00001/request = **約$0.0036/ゲーム**

## 今後の拡張可能性

### Phase 4: 対話システム (未実装)
- [ ] エージェント→コマンダー質問機能の統合
- [ ] コマンダー→エージェント命令機能
- [ ] AIチャットとの統合

### Phase 5: 戦闘・勝敗判定 (未実装)
- [ ] エージェント間戦闘ロジック
- [ ] 区占領ロジック（エージェントが区に到達したら占領）
- [ ] 勝敗条件調整（エージェント数を考慮）

### パフォーマンス最適化案
- [ ] WebSocket実装（ポーリングからリアルタイム通信へ）
- [ ] 画面外エージェントの更新頻度削減
- [ ] エージェント協調行動の実装

## ファイル構成

```
tokyo-risk/
├── game_engine.py        # Agent クラス、GameState 拡張
├── agent_ai.py           # 新規: AI意思決定ロジック
├── server.py             # エージェントエンドポイント追加
├── index.html            # プロンプトUI、エージェントマーカー
├── ward_data.py          # 区データ（WARD_LATLNG追加済み）
└── AGENT_SYSTEM_README.md # このファイル
```

## 検証済み機能

- ✅ プロンプト設定ダイアログの表示
- ✅ 10体のエージェント初期化
- ✅ エージェントマーカーの表示（青/赤の矢印）
- ✅ リアルタイム位置更新（200ms間隔）
- ✅ 移動方向への回転
- ✅ エージェント情報表示（クリック時）
- ✅ Gemini API による行動決定（001-003）
- ✅ ルールベース行動（004-010）
- ✅ バックグラウンドAIループの安定動作

## トラブルシューティング

### エージェントが表示されない
- サーバーログを確認: `tail -f server_agent.log`
- ブラウザコンソールを確認: F12 → Console
- `/game/agents/{session_id}` エンドポイントが正しくレスポンスを返しているか確認

### エージェントが動かない
- AIループが起動しているか確認: サーバーログに "[AgentAI] ループ開始" が表示されているか
- エージェントの `state` が "moving" になっているか確認
- `destination` が設定されているか確認

### Gemini APIエラー
- .env に GEMINI_API_KEY が設定されているか確認
- API制限に達していないか確認
- モデル名が正しいか確認: "gemini-2.0-flash-exp"

## まとめ

Tokyo Risk の多体エージェントシステムが完全実装されました。プロンプトエンジニアリング対戦というコアメカニクスを実現するために、以下の機能が動作しています：

1. **10体のエージェント管理** - 各陣営に10体ずつ配置
2. **カスタムプロンプト設定** - 個別の戦略設定が可能
3. **リアルタイム移動** - 地図上をスムーズに移動
4. **AI意思決定** - Gemini APIによる自律的行動判断
5. **コスト最適化** - 選択的API使用でコストを削減

Phase 4（対話システム）とPhase 5（戦闘システム）は今後実装可能な状態です。
