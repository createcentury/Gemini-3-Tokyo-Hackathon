# Tokyo Risk - 実装ロードマップ

**現在地**: Phase 1 完了 ✅
**次のステップ**: Phase 2 リアルマップUI 🎯

---

## Phase 2: リアルマップUI実装ガイド

### 目標
- ✅ 現状: 色分け表示のみ
- 🎯 目標: Google Maps上に実際の東京23区を表示

### ステップ1: Google Maps API セットアップ

#### 1.1 APIキー取得
```bash
# Google Cloud Console
# 1. プロジェクト作成
# 2. Maps JavaScript API 有効化
# 3. APIキー作成
# 4. .envに追加
echo "GOOGLE_MAPS_API_KEY=your_api_key_here" >> .env
```

#### 1.2 HTMLに地図を追加
```html
<!-- templates/index.html -->
<!DOCTYPE html>
<html>
<head>
    <title>🗾 Tokyo Risk</title>
    <script src="https://maps.googleapis.com/maps/api/js?key={{ maps_api_key }}&libraries=geometry"></script>
    <style>
        #map {
            height: 600px;
            width: 100%;
        }
        .game-controls {
            position: absolute;
            top: 10px;
            left: 10px;
            z-index: 1000;
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.3);
        }
    </style>
</head>
<body>
    <div id="map"></div>
    <div class="game-controls">
        <h2>🗾 Tokyo Risk</h2>
        <button id="btn-start">ゲーム開始</button>
        <div id="game-log"></div>
    </div>

    <script src="/static/game.js"></script>
</body>
</html>
```

### ステップ2: 区境界データの取得

#### 2.1 GeoJSON ダウンロード
```bash
# 東京23区のGeoJSONデータ
# オプション1: overpass-turbo.eu で取得
# オプション2: 既存データセット使用

# ward_boundaries.json として保存
```

#### 2.2 GeoJSON → Google Maps Polygon
```javascript
// static/game.js

class TokyoRiskMap {
    constructor() {
        this.map = null;
        this.wardPolygons = {};
        this.selectedWard = null;
    }

    async init() {
        // 地図初期化
        this.map = new google.maps.Map(document.getElementById('map'), {
            center: { lat: 35.6812, lng: 139.7671 },
            zoom: 11,
            mapTypeId: 'roadmap',
            disableDefaultUI: false,
            zoomControl: true,
            styles: this.getMapStyle() // カスタムスタイル
        });

        // 区境界データ読み込み
        const wardBoundaries = await this.loadWardBoundaries();

        // ポリゴン描画
        this.drawWards(wardBoundaries);
    }

    async loadWardBoundaries() {
        const response = await fetch('/static/ward_boundaries.json');
        return await response.json();
    }

    drawWards(boundaries) {
        Object.keys(boundaries).forEach(wardName => {
            const coords = boundaries[wardName];

            const polygon = new google.maps.Polygon({
                paths: coords,
                strokeColor: '#333',
                strokeOpacity: 0.8,
                strokeWeight: 2,
                fillColor: this.getWardColor(wardName),
                fillOpacity: 0.5,
                map: this.map
            });

            // クリックイベント
            polygon.addListener('click', () => {
                this.onWardClick(wardName);
            });

            // ホバー効果
            polygon.addListener('mouseover', () => {
                polygon.setOptions({ fillOpacity: 0.7 });
            });
            polygon.addListener('mouseout', () => {
                polygon.setOptions({ fillOpacity: 0.5 });
            });

            this.wardPolygons[wardName] = polygon;
        });
    }

    getWardColor(wardName) {
        // ゲーム状態から色を決定
        const owner = gameState.getOwner(wardName);
        if (owner === 'player') return '#4285F4'; // 青
        if (owner === 'ai') return '#EA4335'; // 赤
        return '#9AA0A6'; // 中立
    }

    onWardClick(wardName) {
        if (!this.selectedWard) {
            // 攻撃元選択
            this.selectedWard = wardName;
            this.highlightWard(wardName);
        } else {
            // 攻撃実行
            this.executeAttack(this.selectedWard, wardName);
            this.selectedWard = null;
        }
    }

    getMapStyle() {
        // 戦場風のカスタムスタイル
        return [
            {
                "featureType": "all",
                "stylers": [{ "saturation": -80 }]
            },
            {
                "featureType": "road",
                "elementType": "geometry",
                "stylers": [{ "hue": "#ff6f00" }]
            }
        ];
    }
}

// 初期化
const map = new TokyoRiskMap();
map.init();
```

### ステップ3: 進軍ルートの可視化

#### 3.1 Routes APIデータを地図に描画
```javascript
class TokyoRiskMap {
    // ... 前述のコード ...

    async showAttackRoute(fromWard, toWard) {
        // サーバーからルートデータ取得
        const route = await this.getRouteData(fromWard, toWard);

        if (!route || !route.polyline) {
            // ルートデータがない場合は直線
            this.drawStraightLine(fromWard, toWard);
            return;
        }

        // ポリライン描画
        const path = google.maps.geometry.encoding.decodePath(route.polyline);

        const routeLine = new google.maps.Polyline({
            path: path,
            geodesic: true,
            strokeColor: '#FF0000',
            strokeOpacity: 0.8,
            strokeWeight: 4,
            map: this.map
        });

        // アニメーション: 兵隊アイコンが移動
        this.animateTroops(routeLine, fromWard, toWard);

        // 3秒後に消す
        setTimeout(() => {
            routeLine.setMap(null);
        }, 3000);
    }

    animateTroops(routeLine, fromWard, toWard) {
        const path = routeLine.getPath();
        const totalPoints = path.getLength();

        // 兵隊アイコン
        const troopMarker = new google.maps.Marker({
            position: path.getAt(0),
            map: this.map,
            icon: {
                path: google.maps.SymbolPath.CIRCLE,
                scale: 8,
                fillColor: '#FF0000',
                fillOpacity: 1,
                strokeColor: '#FFFFFF',
                strokeWeight: 2
            },
            label: {
                text: '⚔️',
                fontSize: '20px'
            }
        });

        // アニメーション
        let step = 0;
        const interval = setInterval(() => {
            step += 1;
            if (step >= totalPoints) {
                clearInterval(interval);
                troopMarker.setMap(null);
                // 戦闘エフェクト
                this.showBattleEffect(toWard);
                return;
            }

            troopMarker.setPosition(path.getAt(step));
        }, 30); // 30ms毎に移動
    }

    showBattleEffect(wardName) {
        // 戦闘エフェクト（炎・爆発）
        const wardCenter = this.getWardCenter(wardName);

        const battleMarker = new google.maps.Marker({
            position: wardCenter,
            map: this.map,
            icon: {
                path: google.maps.SymbolPath.CIRCLE,
                scale: 20,
                fillColor: '#FF6600',
                fillOpacity: 0.8,
                strokeWeight: 0
            },
            animation: google.maps.Animation.BOUNCE
        });

        // 1秒後に消す
        setTimeout(() => {
            battleMarker.setMap(null);
        }, 1000);
    }

    async getRouteData(fromWard, toWard) {
        const response = await fetch(`/api/route/${fromWard}/${toWard}`);
        return await response.json();
    }
}
```

### ステップ4: 戦況表示

#### 4.1 各区に兵力マーカー表示
```javascript
class TokyoRiskMap {
    // ... 前述のコード ...

    updateTroopMarkers(gameState) {
        // 既存マーカーをクリア
        this.clearTroopMarkers();

        Object.keys(gameState.troops).forEach(wardName => {
            const troops = gameState.troops[wardName];
            const center = this.getWardCenter(wardName);

            const marker = new google.maps.Marker({
                position: center,
                map: this.map,
                label: {
                    text: troops.toString(),
                    color: 'white',
                    fontSize: '16px',
                    fontWeight: 'bold'
                },
                icon: {
                    path: google.maps.SymbolPath.CIRCLE,
                    scale: 15,
                    fillColor: this.getWardColor(wardName),
                    fillOpacity: 0.9,
                    strokeColor: '#FFFFFF',
                    strokeWeight: 2
                }
            });

            this.troopMarkers.push(marker);
        });
    }

    getWardCenter(wardName) {
        const polygon = this.wardPolygons[wardName];
        const bounds = new google.maps.LatLngBounds();

        polygon.getPath().forEach(latLng => {
            bounds.extend(latLng);
        });

        return bounds.getCenter();
    }
}
```

---

## Phase 3: 自然言語コマンド実装ガイド

### 目標
プレイヤーが「新宿から渋谷に攻撃」と入力 → ゲームコマンド実行

### ステップ1: Gemini Function Calling 設定

#### 1.1 ゲームコマンドの定義
```python
# server.py

# Gemini Function定義
GAME_FUNCTIONS = [
    {
        "name": "attack",
        "description": "指定した区から別の区へ攻撃する",
        "parameters": {
            "type": "object",
            "properties": {
                "from_ward": {
                    "type": "string",
                    "description": "攻撃元の区名（例: 新宿区）",
                    "enum": WARDS  # 23区のリスト
                },
                "to_ward": {
                    "type": "string",
                    "description": "攻撃先の区名（例: 渋谷区）",
                    "enum": WARDS
                },
                "troops": {
                    "type": "integer",
                    "description": "投入する兵力。省略時は最大兵力",
                    "minimum": 1
                }
            },
            "required": ["from_ward", "to_ward"]
        }
    },
    {
        "name": "move_troops",
        "description": "自分の支配する区間で兵力を移動する",
        "parameters": {
            "type": "object",
            "properties": {
                "from_ward": {"type": "string", "enum": WARDS},
                "to_ward": {"type": "string", "enum": WARDS},
                "troops": {"type": "integer", "minimum": 1}
            },
            "required": ["from_ward", "to_ward", "troops"]
        }
    },
    {
        "name": "get_status",
        "description": "指定した区の状態（兵力・所有者・ステータス）を確認",
        "parameters": {
            "type": "object",
            "properties": {
                "ward": {
                    "type": "string",
                    "description": "確認したい区名",
                    "enum": WARDS
                }
            },
            "required": ["ward"]
        }
    },
    {
        "name": "end_turn",
        "description": "自分のターンを終了し、AIのターンに移る",
        "parameters": {"type": "object", "properties": {}}
    }
]
```

#### 1.2 自然言語コマンド処理エンドポイント
```python
# server.py

import google.generativeai as genai

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

@app.post("/command/natural")
async def natural_language_command(request: Request):
    """
    自然言語コマンドを受け取り、Geminiで解析して実行
    """
    data = await request.json()
    user_input = data.get("command")
    session_id = data.get("session_id")

    if session_id not in sessions:
        raise HTTPException(404, "セッションが見つかりません")

    game_state = sessions[session_id]

    # Gemini モデル初期化
    model = genai.GenerativeModel(
        'gemini-3-pro',
        tools=GAME_FUNCTIONS
    )

    # コンテキストを含むプロンプト
    prompt = f"""
    あなたは東京23区の陣取りゲーム「Tokyo Risk」のコマンドパーサーです。

    現在の状況:
    - プレイヤー支配区: {list(game_state.player_wards)}
    - AI支配区: {list(game_state.ai_wards)}
    - 各区の兵力: {game_state.troops}

    プレイヤーの命令: "{user_input}"

    この命令を適切なゲームコマンドに変換してください。
    """

    try:
        response = model.generate_content(prompt)

        # Function Callがあれば実行
        if response.candidates[0].content.parts[0].function_call:
            function_call = response.candidates[0].content.parts[0].function_call
            result = execute_game_command(
                session_id,
                function_call.name,
                dict(function_call.args)
            )

            return {
                "success": True,
                "command": function_call.name,
                "args": dict(function_call.args),
                "result": result,
                "message": f"実行しました: {function_call.name}"
            }
        else:
            # 通常の応答（質問など）
            return {
                "success": False,
                "message": response.text
            }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def execute_game_command(session_id: str, command: str, args: dict):
    """ゲームコマンド実行"""
    game_state = sessions[session_id]

    if command == "attack":
        return game_state.attack(
            args["from_ward"],
            args["to_ward"]
        )
    elif command == "move_troops":
        return game_state.move_troops(
            args["from_ward"],
            args["to_ward"],
            args["troops"]
        )
    elif command == "get_status":
        ward = args["ward"]
        return {
            "ward": ward,
            "owner": game_state.get_owner(ward),
            "troops": game_state.troops[ward],
            "stats": game_state.get_all_stats(ward)
        }
    elif command == "end_turn":
        return game_state.end_player_turn()
```

### ステップ2: フロントエンド統合

#### 2.1 自然言語入力UI
```html
<!-- templates/index.html に追加 -->
<div class="game-controls">
    <h2>🗾 Tokyo Risk</h2>

    <!-- 自然言語コマンド入力 -->
    <div class="command-input">
        <input
            type="text"
            id="nl-command"
            placeholder="例: 新宿から渋谷に攻撃"
            style="width: 300px; padding: 8px;"
        />
        <button id="btn-execute-command">実行</button>
        <button id="btn-voice-input">🎤 音声入力</button>
    </div>

    <div id="game-log"></div>
</div>
```

#### 2.2 JavaScript実装
```javascript
// static/game.js

class NaturalLanguageController {
    constructor(sessionId) {
        this.sessionId = sessionId;
        this.recognition = null;
        this.initVoiceRecognition();
    }

    async executeCommand(commandText) {
        const response = await fetch('/command/natural', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: this.sessionId,
                command: commandText
            })
        });

        const result = await response.json();

        if (result.success) {
            this.showMessage(`✅ ${result.message}`);
            // ゲーム状態を更新
            await updateGameState();
        } else {
            this.showMessage(`❌ ${result.message || result.error}`);
        }

        return result;
    }

    initVoiceRecognition() {
        if (!('webkitSpeechRecognition' in window)) {
            console.log('音声認識非対応');
            return;
        }

        this.recognition = new webkitSpeechRecognition();
        this.recognition.lang = 'ja-JP';
        this.recognition.continuous = false;

        this.recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            document.getElementById('nl-command').value = transcript;
            this.executeCommand(transcript);
        };

        this.recognition.onerror = (event) => {
            console.error('音声認識エラー:', event.error);
        };
    }

    startVoiceInput() {
        if (this.recognition) {
            this.recognition.start();
            this.showMessage('🎤 話してください...');
        }
    }

    showMessage(msg) {
        const log = document.getElementById('game-log');
        const entry = document.createElement('div');
        entry.textContent = msg;
        log.prepend(entry);
    }
}

// イベントリスナー
document.getElementById('btn-execute-command').addEventListener('click', () => {
    const command = document.getElementById('nl-command').value;
    nlController.executeCommand(command);
});

document.getElementById('btn-voice-input').addEventListener('click', () => {
    nlController.startVoiceInput();
});
```

---

## Phase 4: 対話型AIコマンダー実装ガイド

### 目標
AIが戦況を分析し、プレイヤーに提案・質問する

### ステップ1: 戦況分析エンドポイント

```python
# server.py

@app.get("/ai/analysis/{session_id}")
async def get_ai_analysis(session_id: str):
    """AIコマンダーが戦況を分析"""
    if session_id not in sessions:
        raise HTTPException(404, "セッションが見つかりません")

    game_state = sessions[session_id]

    # Gemini に戦況分析させる
    analysis_prompt = f"""
    あなたは優秀な軍事コマンダーです。
    東京23区の陣取りゲーム「Tokyo Risk」の戦況を分析してください。

    【現在の状況】
    プレイヤー支配区: {list(game_state.player_wards)} ({len(game_state.player_wards)}区)
    AI支配区: {list(game_state.ai_wards)} ({len(game_state.ai_wards)}区)

    各区の兵力:
    {format_troops_distribution(game_state)}

    隣接関係:
    {format_adjacency()}

    【分析項目】
    1. **危険な区**: プレイヤーの支配区で防衛が手薄な場所（AIの攻撃を受けやすい）
    2. **攻撃チャンス**: AIの弱点（兵力が少ない、孤立している区）
    3. **戦略的要所**: 制圧すると有利になる区（複数の区に隣接）
    4. **推奨行動**: プレイヤーが次に取るべき行動3つ（優先順位付き）

    簡潔に、司令官に報告する口調で回答してください。
    """

    model = genai.GenerativeModel('gemini-3-pro')
    response = model.generate_content(analysis_prompt)

    return {
        "analysis": response.text,
        "timestamp": datetime.now().isoformat()
    }

def format_troops_distribution(game_state):
    """兵力分布を見やすくフォーマット"""
    lines = []
    for ward, troops in game_state.troops.items():
        owner = game_state.get_owner(ward)
        emoji = "🔵" if owner == "player" else "🔴" if owner == "ai" else "⚪"
        lines.append(f"{emoji} {ward}: {troops}兵")
    return "\n".join(lines)
```

### ステップ2: 対話フロー実装

```python
# server.py

@app.post("/ai/chat")
async def chat_with_ai_commander(request: Request):
    """AIコマンダーと対話"""
    data = await request.json()
    session_id = data.get("session_id")
    user_message = data.get("message")

    if session_id not in sessions:
        raise HTTPException(404, "セッションが見つかりません")

    game_state = sessions[session_id]

    # 会話履歴を保持
    if not hasattr(game_state, 'chat_history'):
        game_state.chat_history = []

    # システムプロンプト
    system_prompt = f"""
    あなたは東京23区陣取りゲーム「Tokyo Risk」のAIコマンダーです。
    プレイヤーを「司令官」と呼び、戦略的なアドバイスを提供します。

    現在の状況:
    - プレイヤー支配区: {list(game_state.player_wards)}
    - AI支配区: {list(game_state.ai_wards)}
    - ターン数: {game_state.turn}

    プレイヤーの質問や命令に対して、以下のように対応してください:
    1. 戦況の質問 → 分析結果を報告
    2. 命令（攻撃・移動等） → Function Callingで実行
    3. 提案依頼 → 具体的な行動を3つ提案
    """

    model = genai.GenerativeModel(
        'gemini-3-pro',
        tools=GAME_FUNCTIONS,
        system_instruction=system_prompt
    )

    # 会話履歴を含めて送信
    chat = model.start_chat(history=game_state.chat_history)
    response = chat.send_message(user_message)

    # 会話履歴を更新
    game_state.chat_history.append({
        "role": "user",
        "parts": [{"text": user_message}]
    })
    game_state.chat_history.append({
        "role": "model",
        "parts": [{"text": response.text}]
    })

    # Function Callがあれば実行
    if response.candidates[0].content.parts[0].function_call:
        function_call = response.candidates[0].content.parts[0].function_call
        command_result = execute_game_command(
            session_id,
            function_call.name,
            dict(function_call.args)
        )

        return {
            "ai_response": response.text,
            "command_executed": function_call.name,
            "command_args": dict(function_call.args),
            "command_result": command_result
        }

    return {
        "ai_response": response.text
    }
```

### ステップ3: チャットUI

```html
<!-- templates/index.html に追加 -->
<div class="ai-commander-chat">
    <h3>🤖 AIコマンダー</h3>
    <div id="chat-messages" style="height: 300px; overflow-y: scroll; border: 1px solid #ccc; padding: 10px;">
        <div class="ai-message">
            司令官、準備完了です。ご命令を。
        </div>
    </div>
    <input
        type="text"
        id="chat-input"
        placeholder="AIコマンダーに質問・命令"
        style="width: 100%; padding: 8px;"
    />
</div>
```

```javascript
// static/game.js

class AICommanderChat {
    constructor(sessionId) {
        this.sessionId = sessionId;
    }

    async sendMessage(message) {
        // ユーザーメッセージを表示
        this.addMessage('user', message);

        const response = await fetch('/ai/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: this.sessionId,
                message: message
            })
        });

        const result = await response.json();

        // AIの応答を表示
        this.addMessage('ai', result.ai_response);

        // コマンド実行された場合
        if (result.command_executed) {
            this.addMessage('system', `✅ 実行: ${result.command_executed}`);
            await updateGameState();
        }
    }

    addMessage(role, text) {
        const chatMessages = document.getElementById('chat-messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `${role}-message`;
        messageDiv.textContent = text;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    async getAnalysis() {
        const response = await fetch(`/ai/analysis/${this.sessionId}`);
        const result = await response.json();
        this.addMessage('ai', result.analysis);
    }
}

// 初期化
const aiChat = new AICommanderChat(sessionId);

// エンターキーで送信
document.getElementById('chat-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        const message = e.target.value;
        aiChat.sendMessage(message);
        e.target.value = '';
    }
});
```

---

## まとめ

### 実装優先順位

| Phase | 機能 | 難易度 | 所要時間 | インパクト |
|-------|------|--------|----------|-----------|
| **Phase 2** | リアルマップUI | ★★★☆☆ | 1-2日 | ⭐⭐⭐⭐⭐ |
| **Phase 3** | 自然言語コマンド | ★★☆☆☆ | 1日 | ⭐⭐⭐⭐☆ |
| **Phase 4** | 対話型AI | ★★★★☆ | 1-2日 | ⭐⭐⭐⭐⭐ |

### 推奨実装順序

1. **Phase 2 ステップ1-2**: Google Maps基本統合（4時間）
2. **Phase 3 ステップ1**: Function Calling実装（3時間）
3. **Phase 2 ステップ3**: 進軍ルート可視化（4時間）
4. **Phase 3 ステップ2**: 音声入力（2時間）
5. **Phase 4 ステップ1-2**: AIコマンダー対話（6時間）
6. **Phase 2 ステップ4 + UI改善**: 完成度向上（4時間）

**合計**: 約3日（24時間）でハッカソン優勝レベルの完成度！

---

**Next Step**: Phase 2のGoogle Maps統合から始めましょう 🚀
