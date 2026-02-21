# Tokyo Risk - リアルデータ駆動型東京23区陣取りゲーム

## 📋 基本情報

| 項目 | 内容 |
|------|------|
| **プロジェクト名** | Tokyo Risk (東京23区 陣取りゲーム) |
| **ステータス** | 🚧 MVP完成 / 地図UI・自然言語コマンド拡張予定 |
| **作成日** | 2026-02-21 |
| **最終更新** | 2026-02-21 |
| **ハッカソントラック** | 推論&マルチモーダル / 高度なツール使用 |

## 🎯 概要（エレベーターピッチ）

**Google Maps APIから取得した実際のPOIデータ（病院・駅・商業施設等）と道路渋滞情報を使った、リアリティ溢れる東京23区の陣取りゲーム。Gemini 3が対戦相手として戦略的に攻めてくる。最終的には自然言語でコマンドを出し、AIコマンダーと対話しながらプレイできる次世代戦略ゲーム。**

## 🔍 問題・課題

### 解決したい問題
- **従来の戦略ゲーム**: ゲームデータが架空・固定的で現実感がない
- **マップの単調さ**: 実際の地理や都市データを反映していない
- **操作性**: クリック操作のみ、戦略を自然に伝えられない
- **AI対戦相手**: パターン化された動き、会話できない

### ターゲットユーザー
- **誰のため**: 戦略ゲーム好き、東京在住者、地理・都市データ愛好家
- **どんなシーン**:
  - 通勤途中に自分の住む区を守る
  - 東京の地理を楽しく学ぶ教育ツールとして
  - リアルデータとAIの融合を体験したい

## 💡 解決策

### コアアイデア

#### 1. **リアルデータ駆動型ゲームバランス**
```
Google Places API → 各区のPOI数
  ├ 病院・警察 → DEF（防御力）
  ├ 鉄道駅 → SPD（速度・ボーナスターン）
  ├ 商業施設 → INC（収入）
  └ 公園・神社 → REC（回復力）

Google Routes API → 区間の移動時間
  └ 渋滞が多い → 攻撃力ペナルティ
```

#### 2. **リアルマップUI** (次フェーズ)
- Google Maps JavaScript API または Leaflet + OpenStreetMap
- 実際の地形・道路を表示
- 進軍ルートをアニメーション表示

#### 3. **自然言語コマンドシステム** (最終目標)
```
プレイヤー: 「新宿から渋谷に5部隊で攻撃」
     ↓
Gemini 3 が解析 → ゲームコマンドに変換
     ↓
実行: attack("新宿区", "渋谷区", 5)
```

#### 4. **対話型AIコマンダー**
```
AI: 「司令官、江戸川区が手薄です。防衛を強化しますか？」
プレイヤー: 「はい、近隣の葛飾区から2部隊移動させて」
AI: 「了解しました。実行します。」
```

### Gemini 3の活用ポイント
- [x] **Tool Use**: Google Maps API統合（POI検索、ルート計算）
- [x] **Thinking Mode**: AI対戦相手の戦略生成
- [ ] **Multimodal**: 地図画像を見てAIが戦略提案（将来）
- [ ] **Function Calling**: 自然言語→ゲームコマンド変換
- [ ] **Long Context**: ゲーム履歴全体を記憶して戦略立案

### 差別化要因
- **実データ活用**: 架空データではなく、Google APIから毎回最新データ取得
- **リアル道路**: 実際の渋滞情報が戦闘に影響
- **自然言語UI**: 「司令官プレイ」の没入感
- **東京23区という親しみやすさ**: 知っている場所でプレイできる

## 🎨 主要機能

### ✅ MVP完成（Phase 1）

#### 1. **リアルデータ収集**
- Google Places API で各区のPOI数取得
  - `ward_stats_cache.json`: 23区 × 8種類のステータス
- Google Routes API で55区間の移動時間取得
  - `route_times_cache.json`: 実際の渋滞考慮済み

#### 2. **ゲームエンジン**
- ターン制戦闘システム
- 攻撃・防御・兵力管理
- 渋滞ペナルティ（移動コスト5 → 攻撃力60%）
- 特殊効果:
  - SPD≥8: ボーナスターン
  - REC≥7: 毎ターン回復

#### 3. **Gemini AI対戦相手**
- 戦略的に攻撃対象を選択
- 形勢判断して戦術を変更

#### 4. **Web UI**
- FastAPI + HTML/JS
- 23区の色分け表示
- クリックで攻撃
- リアルタイムゲームログ

### 🚧 Phase 2: リアルマップUI（次の実装）

#### 1. **Google Maps統合**
```javascript
// Google Maps JavaScript API
const map = new google.maps.Map(document.getElementById('map'), {
  center: { lat: 35.6812, lng: 139.7671 }, // 東京
  zoom: 11,
  styles: customMapStyle // 戦場風
});

// 各区をポリゴンで表示
WARDS.forEach(ward => {
  const polygon = new google.maps.Polygon({
    paths: wardBoundaries[ward],
    strokeColor: getOwnerColor(ward),
    fillColor: getOwnerColor(ward),
    fillOpacity: 0.5
  });
  polygon.setMap(map);
});
```

#### 2. **進軍ルート可視化**
```javascript
// Routes APIの結果を地図上に描画
function showAttackRoute(fromWard, toWard) {
  const route = ROUTE_TIMES[`${fromWard}|${toWard}`];

  const path = new google.maps.Polyline({
    path: route.polyline, // Routes APIから取得
    geodesic: true,
    strokeColor: '#FF0000',
    strokeOpacity: 1.0,
    strokeWeight: 3
  });

  path.setMap(map);
  animateTroops(path); // 兵隊アイコンが移動
}
```

#### 3. **リアルタイム戦況表示**
- マップ上に兵力数をマーカー表示
- 戦闘時にアニメーション（炎・爆発エフェクト）
- 渋滞情報をヒートマップ表示

### 🎯 Phase 3: 自然言語コマンドシステム

#### 1. **コマンドパーサー（Gemini Function Calling）**
```python
# Function定義
attack_function = {
    "name": "attack",
    "description": "指定した区から別の区へ攻撃する",
    "parameters": {
        "type": "object",
        "properties": {
            "from_ward": {"type": "string", "description": "攻撃元の区名"},
            "to_ward": {"type": "string", "description": "攻撃先の区名"},
            "troops": {"type": "integer", "description": "投入する兵力"}
        }
    }
}

# プレイヤー入力
user_input = "新宿から渋谷に全力で攻撃"

# Gemini 3が解析
response = gemini.generate_content(
    user_input,
    tools=[attack_function, move_function, recruit_function]
)

# 実行
if response.function_call:
    execute_game_command(response.function_call)
```

#### 2. **音声入力対応**
```javascript
// Web Speech API
const recognition = new webkitSpeechRecognition();
recognition.lang = 'ja-JP';
recognition.onresult = (event) => {
  const command = event.results[0][0].transcript;
  sendCommandToGemini(command);
};
```

### 🤖 Phase 4: 対話型AIコマンダー

#### 1. **戦況分析と提案**
```python
def analyze_situation(game_state):
    """Geminiに戦況を分析させる"""
    prompt = f"""
    あなたは優秀な軍事コマンダーです。

    現在の戦況:
    - プレイヤー支配区: {player_wards}
    - AI支配区: {ai_wards}
    - 各区の兵力: {troops_distribution}
    - 隣接関係: {adjacency}

    以下を分析してください:
    1. 危険な区（防衛が手薄）
    2. 攻撃チャンス（敵の弱点）
    3. 推奨する次の行動3つ
    """

    analysis = gemini.generate_content(prompt)
    return analysis.text
```

#### 2. **対話フロー**
```
[ターン開始]
AI: 「司令官、江戸川区が危険です。敵の大軍が隣接しています。」
プレイヤー: 「防衛を強化して」
AI: 「了解。葛飾区から2部隊、墨田区から1部隊を移動させます。」

[実行]

AI: 「防衛完了。次の手は？ 反撃しますか、それとも他の戦線を強化しますか？」
プレイヤー: 「敵の本拠地である千代田区への最短ルートを教えて」
AI: 「新宿区→渋谷区→港区→千代田区のルートが最短です。
     ただし港区は敵の防御が固く（DEF:10）、突破は困難です。
     迂回して台東区経由をお勧めします。」
```

## 🏗️ 技術スタック

### フロントエンド
- **Framework**: Vanilla JS（現状）→ React/Vue（将来）
- **地図**: Google Maps JavaScript API または Leaflet.js
- **UI**: HTML5/CSS3
- **音声**: Web Speech API

### バックエンド
- **Framework**: FastAPI
- **言語**: Python 3.11+
- **AI**: Gemini 3 Pro
- **Database**: JSON Cache（現状）→ Redis（将来）

### 外部API
- **Google Places API**: POI検索
- **Google Routes API**: ルート計算・渋滞情報
- **Google Maps JavaScript API**: 地図表示
- **Gemini API**: AI対戦相手・自然言語処理

### インフラ
- **開発**: localhost:8766
- **本番**: Cloud Run（予定）

## 📐 アーキテクチャ

### 現状（Phase 1）
```
┌─────────────┐
│   Browser   │
│  (HTML/JS)  │
└──────┬──────┘
       │ REST API
       ▼
┌─────────────┐
│  FastAPI    │
│  server.py  │
└──┬────┬─────┘
   │    │
   │    └────────────┐
   ▼                 ▼
┌──────────┐  ┌─────────────┐
│ Gemini 3 │  │ JSON Cache  │
│   API    │  │ ward_stats  │
│          │  │ route_times │
└──────────┘  └─────────────┘
```

### 将来（Phase 3-4）
```
┌─────────────────────────┐
│      Browser            │
│  Google Maps + React    │
│  音声入力               │
└───────┬─────────────────┘
        │ WebSocket / REST
        ▼
┌───────────────────────┐
│   FastAPI Server      │
│  + WebSocket          │
└──┬────┬────┬──────────┘
   │    │    │
   │    │    └──────────────┐
   ▼    ▼                   ▼
┌─────┐ ┌──────────┐  ┌──────────┐
│Redis│ │ Gemini 3 │  │Google    │
│     │ │  - AI戦略 │  │Maps APIs │
│     │ │  - NL処理│  │          │
│     │ │  - 対話  │  │          │
└─────┘ └──────────┘  └──────────┘
```

## 📊 データフロー

### 攻撃コマンド実行（Phase 1）
1. プレイヤーが区をクリック → Frontend
2. Frontend → Backend `/game/attack`
3. Backend → `game_engine.py`:
   - 攻撃力計算（ATK × 兵力 × 渋滞ペナルティ）
   - 防御力計算（DEF × 兵力 × 地形ボーナス）
   - 勝敗判定
4. 結果 → Frontend → 画面更新

### 自然言語コマンド（Phase 3）
1. プレイヤー: 「新宿から渋谷に攻撃」
2. Frontend → Backend `/command/natural`
3. Backend → Gemini API（Function Calling）
4. Gemini: `{"function": "attack", "args": {"from": "新宿区", "to": "渋谷区"}}`
5. Backend → `game_engine.py` 実行
6. 結果 → Frontend

## 🎯 成功指標（KPI）

### ゲーム体験
- [ ] プレイ時間: 平均15-20分/ゲーム
- [ ] 再プレイ率: 60%以上
- [ ] 勝率バランス: プレイヤー勝率40-60%（AI強すぎず弱すぎず）

### 技術的指標
- [x] API応答時間: < 1秒（Places/Routes）
- [x] 戦闘計算: < 100ms
- [ ] 地図表示: < 2秒（Phase 2）
- [ ] 自然言語認識精度: > 90%（Phase 3）

### ハッカソン評価
- [x] リアルデータ活用: Google APIs統合
- [x] Gemini AI対戦相手: 戦略的思考
- [ ] マルチモーダル: 地図+テキスト
- [ ] 自然言語UI: 革新的UX

## 📅 実装スケジュール

### ✅ Phase 1: MVP（完了）
- [x] Places API統合（23区POI収集）
- [x] Routes API統合（55区間移動時間）
- [x] ゲームエンジン実装
- [x] Gemini AI対戦相手
- [x] 基本Web UI

### 🚧 Phase 2: リアルマップUI（1-2日）
- [ ] Google Maps JavaScript API統合
- [ ] 区境界ポリゴン描画
- [ ] 進軍ルートアニメーション
- [ ] 戦況マーカー・エフェクト

### 🎯 Phase 3: 自然言語コマンド（1-2日）
- [ ] Gemini Function Calling実装
- [ ] コマンドパーサー
- [ ] 音声入力対応
- [ ] エラーハンドリング（曖昧な命令）

### 🤖 Phase 4: 対話型AI（1-2日）
- [ ] 戦況分析プロンプト設計
- [ ] AIコマンダー対話フロー
- [ ] 提案システム
- [ ] チュートリアルモード

## ✅ 実装状況

### 完了
- [x] プロジェクト立ち上げ
- [x] Google Places API統合
  - [x] 23区のPOI収集
  - [x] ward_stats_cache.json生成
- [x] Google Routes API統合
  - [x] 55区間の移動時間取得
  - [x] route_times_cache.json生成
- [x] ゲームエンジン
  - [x] 戦闘システム
  - [x] 渋滞ペナルティ反映
  - [x] 特殊効果（SPD/REC）
- [x] Gemini AI対戦相手
- [x] FastAPI サーバー
- [x] 基本Web UI

### 進行中
- [ ] リアルマップUI（0%）

### 未着手
- [ ] 自然言語コマンド
- [ ] 対話型AIコマンダー
- [ ] デプロイ設定

## 💰 コスト見積もり

### 開発フェーズ
- **Places API**: $0（無料枠: 1,000リクエスト/月）
- **Routes API**: $0（無料枠: 500リクエスト/月）
- **Maps JavaScript API**: $0（無料枠: 28,000ロード/月）
- **Gemini API**: $10-20（AI対戦相手・自然言語処理）
- **合計**: 約 **$10-20**

### 本番運用（想定）
- **月間**: $50-100（1000ユーザー想定）
- Google Maps API課金が大部分

## 🚧 課題・リスク

### 技術的課題
1. **地図パフォーマンス**: 23個のポリゴン描画が重い
   - 対策: 簡略化、キャッシュ、描画最適化

2. **自然言語の曖昧性**: 「渋谷に攻撃」→ どこから？
   - 対策: 確認ダイアログ、デフォルト動作（最寄りの自軍から）

3. **AIの強さ調整**: 強すぎると面白くない
   - 対策: 難易度設定、Geminiのtemperature調整

### スケジュールリスク
- **リスク**: Google Maps API統合に時間がかかる
- **対策**: Leaflet.jsなどシンプルな代替案を用意

## 📚 参考資料

### Google Maps Platform
- [Places API Documentation](https://developers.google.com/maps/documentation/places/web-service)
- [Routes API Documentation](https://developers.google.com/maps/documentation/routes)
- [Maps JavaScript API](https://developers.google.com/maps/documentation/javascript)

### Gemini
- [Function Calling Guide](https://ai.google.dev/gemini-api/docs/function-calling)
- [Gemini API Documentation](https://ai.google.dev/gemini-api/docs)

### 類似プロジェクト
- **Risk（ボードゲーム）**: 陣取りゲームの元祖
- **Civilization シリーズ**: ターン制戦略ゲーム
- 違い: リアルデータ + 自然言語UI

## 🔗 関連ファイル

- [server.py](./server.py) - FastAPI サーバー
- [game_engine.py](./game_engine.py) - ゲームロジック
- [ward_stats_cache.json](./ward_stats_cache.json) - POIデータ
- [route_times_cache.json](./route_times_cache.json) - 移動時間データ

## 📝 メモ・アイデア

### ブレインストーミング
- **マルチプレイヤー**: 友達と対戦
- **ランキング**: 最速制覇タイム
- **イベント**: 台風で渋滞増加、オリンピックでSPD増加
- **歴史モード**: 江戸時代の東京で陣取り

### 今後の拡張案
- **全国版**: 47都道府県
- **AR版**: スマホカメラで実際の街を見ながらプレイ
- **教育版**: 地理学習ツール（小学生向け）
- **eSports化**: 競技大会

---

**作成者**: Gemini-3-Tokyo-Hackathon Team
**最終更新**: 2026-02-21

**起動方法**:
```bash
cd playground/tokyo-risk
uvicorn server:app --port 8766 --reload
# ブラウザで http://localhost:8766 を開く
```
