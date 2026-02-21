"""
Tokyo Risk - FastAPI サーバー
起動: uvicorn server:app --port 8766 --reload
"""

import os, json
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from google import genai
from ward_data import WARDS, ADJACENCY, WARD_POSITIONS, WARD_LATLNG, load_or_fetch_stats
from game_engine import GameState, GeminiAI, PLAYER, AI, NEUTRAL

# ============================================================
app = FastAPI(title="Tokyo Risk API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
gemini_ai = GeminiAI(client)

# スタッツ（起動時に1回だけ取得 or キャッシュ）
print("スタッツ初期化中...")
WARD_STATS = load_or_fetch_stats(client)

# ルート移動コスト（Routes API キャッシュ）
ROUTE_CACHE_FILE = Path(__file__).parent / "route_times_cache.json"
ROUTE_TIMES: dict = {}
if ROUTE_CACHE_FILE.exists():
    with open(ROUTE_CACHE_FILE) as f:
        ROUTE_TIMES = json.load(f)
    print(f"  [routes] {len(ROUTE_TIMES)}区間のルートデータ読み込み完了")

# セッションストア
sessions: dict[str, GameState] = {}

# ============================================================
# リクエストモデル
# ============================================================
class StartRequest(BaseModel):
    player_ward: str = "新宿区"

class AttackRequest(BaseModel):
    session_id: str
    from_ward: str = None
    to_ward: str = None
    attacker: str = None  # 互換性のため
    defender: str = None  # 互換性のため

class ReinforceRequest(BaseModel):
    session_id: str
    ward: str
    amount: int = 1

# ============================================================
# エンドポイント
# ============================================================
@app.post("/game/start")
def start_game(req: StartRequest):
    import time
    session_id = f"game_{int(time.time())}"
    state = GameState(WARD_STATS)

    # AI の開始位置: プレイヤーから最も遠い区
    player_pos = WARD_POSITIONS[req.player_ward]
    ai_ward = max(
        [w for w in WARDS if w != req.player_ward],
        key=lambda w: (WARD_POSITIONS[w][0] - player_pos[0])**2 + (WARD_POSITIONS[w][1] - player_pos[1])**2
    )
    state.setup_starting_positions(req.player_ward, ai_ward)
    sessions[session_id] = state

    return {
        "session_id": session_id,
        "player_ward": req.player_ward,
        "ai_ward": ai_ward,
        "state": state.serialize(),
    }


@app.post("/game/attack")
def attack(req: AttackRequest):
    state = sessions.get(req.session_id)
    if not state:
        raise HTTPException(404, "セッションが見つかりません")

    # from_ward/to_ward または attacker/defender のどちらでも受け付ける
    from_ward = getattr(req, 'from_ward', None) or getattr(req, 'attacker', None)
    to_ward = getattr(req, 'to_ward', None) or getattr(req, 'defender', None)

    if not from_ward or not to_ward:
        raise HTTPException(400, "攻撃元と攻撃先を指定してください")

    result = state.resolve_attack(from_ward, to_ward, PLAYER)
    if not result["success"]:
        raise HTTPException(400, result["reason"])

    # プレイヤーターン終了 → AI ターン
    player_income = state.end_turn(PLAYER)
    state.turn += 1

    ai_actions = []
    victory = state.check_victory()
    if not victory:
        # AI が行動（最大2手）
        for _ in range(2):
            ai_decision = gemini_ai.decide_action(state)
            if ai_decision.get("action") == "attack":
                ai_result = state.resolve_attack(
                    ai_decision["from"], ai_decision["to"], AI
                )
                ai_actions.append({
                    "decision": ai_decision,
                    "result": ai_result,
                })
                # ボーナスターンなければ1手で終了
                if not ai_result.get("bonus_turn"):
                    break
            elif ai_decision.get("action") == "reinforce":
                r = state.reinforce(ai_decision["ward"], AI, 2)
                ai_actions.append({"decision": ai_decision, "result": r})
                break
            else:
                break

        state.end_turn(AI)

    return {
        "attack_result": result,
        "player_income": player_income,
        "ai_actions": ai_actions,
        "state": state.serialize(),
    }


@app.post("/game/reinforce")
def reinforce(req: ReinforceRequest):
    state = sessions.get(req.session_id)
    if not state:
        raise HTTPException(404, "セッションが見つかりません")
    result = state.reinforce(req.ward, PLAYER, req.amount)
    return {"result": result, "state": state.serialize()}


@app.get("/game/state/{session_id}")
def get_state(session_id: str):
    state = sessions.get(session_id)
    if not state:
        raise HTTPException(404, "セッションが見つかりません")
    return state.serialize()


@app.get("/map/data")
def get_map_data():
    """フロントエンドに23区の座標・隣接情報・スタッツを返す"""
    return {
        "wards": WARDS,
        "positions": WARD_POSITIONS,
        "latlng": WARD_LATLNG,
        "adjacency": ADJACENCY,
        "stats": WARD_STATS,
        "routes": ROUTE_TIMES,
    }


@app.get("/route/{from_ward}/{to_ward}")
def get_route(from_ward: str, to_ward: str):
    """2区間のルート情報を返す"""
    # キーは辞書順でソート済み
    key = "|".join(sorted([from_ward, to_ward]))
    route_data = ROUTE_TIMES.get(key)

    if not route_data:
        # ルートデータがない場合は基本情報のみ
        return {
            "from": from_ward,
            "to": to_ward,
            "has_data": False,
            "estimated_minutes": 15
        }

    return {
        "from": from_ward,
        "to": to_ward,
        "has_data": True,
        "seconds": route_data.get("seconds", 900),
        "minutes": route_data.get("seconds", 900) // 60,
        "movement_cost": route_data.get("movement_cost", 3),
        "polyline": route_data.get("polyline", None)
    }


@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    return (Path(__file__).parent / "index.html").read_text(encoding="utf-8")
