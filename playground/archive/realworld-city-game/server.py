"""
Tokyo Real World Survival Game - Web Server
============================================
FastAPI でゲームをブラウザから動かす。
game.py のロジックをそのまま API として公開する。

起動:
    uvicorn server:app --reload --port 8765
"""

import os
import time
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from google import genai
from google.genai import types
from data_logger import GameDataLogger

# ============================================================
# シナリオ定義 (game.py と同じ)
# ============================================================
SCENARIOS = [
    {"id": "day1_arrival",   "title": "Day 1: 東京到着",  "situation": "あなたは外国から東京に到着したばかり。所持金: ¥5000、スタミナ: 100%。まず何をする？",          "location_hint": "渋谷駅周辺",   "resource": {"money": 5000, "stamina": 100, "day": 1}},
    {"id": "day2_exploration","title": "Day 2: 探索",      "situation": "お腹が空いてきた。近くで安くて美味しい食事場所を探したい。",                                    "location_hint": "新宿区",        "resource": {"money": 4200, "stamina": 75,  "day": 2}},
    {"id": "day3_emergency",  "title": "Day 3: 緊急事態",  "situation": "突然体調が悪くなった。近くの医療施設を探すか、コンビニで薬を買うか？",                          "location_hint": "池袋周辺",      "resource": {"money": 3800, "stamina": 40,  "day": 3}},
    {"id": "day4_opportunity","title": "Day 4: チャンス",  "situation": "アルバイトの募集を見つけた。場所まで効率よく移動したい。",                                      "location_hint": "秋葉原",        "resource": {"money": 2500, "stamina": 60,  "day": 4}},
    {"id": "day5_survive",    "title": "Day 5: 生き残れ",  "situation": "残り所持金が少ない。無料・低コストで過ごせる場所を見つけろ！",                                  "location_hint": "上野公園周辺",  "resource": {"money": 800,  "stamina": 50,  "day": 5}},
]

LOCATION_COORDS = {
    "渋谷駅周辺":   types.LatLng(latitude=35.6580, longitude=139.7016),
    "新宿区":       types.LatLng(latitude=35.6938, longitude=139.7034),
    "池袋周辺":     types.LatLng(latitude=35.7295, longitude=139.7109),
    "秋葉原":       types.LatLng(latitude=35.6984, longitude=139.7731),
    "上野公園周辺": types.LatLng(latitude=35.7148, longitude=139.7731),
}

# ============================================================
# FastAPI アプリ
# ============================================================
app = FastAPI(title="Tokyo Survival Game API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# セッションストア（メモリ内）
sessions: dict[str, dict] = {}


# ============================================================
# リクエスト / レスポンス モデル
# ============================================================
class ActionRequest(BaseModel):
    session_id: str
    player_choice: str

class RatingRequest(BaseModel):
    session_id: str
    entry_id: str
    rating: int

class ActionResponse(BaseModel):
    response_text: str
    entry_id: str
    resources: dict
    scenario_index: int
    total_scenarios: int
    game_over: bool
    clear: bool
    elapsed_sec: float


# ============================================================
# API エンドポイント
# ============================================================
@app.post("/session/start")
def start_session():
    session_id = f"player_{int(time.time())}"
    sessions[session_id] = {
        "index": 0,
        "resources": {"money": 5000, "stamina": 100},
        "logger": GameDataLogger(session_id),
    }
    s = sessions[session_id]
    scenario = SCENARIOS[s["index"]]
    return {
        "session_id": session_id,
        "scenario": scenario,
        "resources": s["resources"],
        "total_scenarios": len(SCENARIOS),
    }


@app.post("/action", response_model=ActionResponse)
def player_action(req: ActionRequest):
    s = sessions.get(req.session_id)
    if not s:
        return ActionResponse(
            response_text="セッションが見つかりません。リロードしてください。",
            entry_id="", resources={}, scenario_index=0,
            total_scenarios=5, game_over=True, clear=False, elapsed_sec=0
        )

    scenario = SCENARIOS[s["index"]]
    location = scenario["location_hint"]
    resource = s["resources"]
    t0 = time.time()

    # Step 1: Gemini 2.5 Flash + Maps Tool
    maps_response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"{location}周辺で「{req.player_choice}」に関連する施設・費用を調べてください。施設名と費用を含めてください。",
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_maps=types.GoogleMaps())],
            tool_config=types.ToolConfig(
                retrieval_config=types.RetrievalConfig(
                    lat_lng=LOCATION_COORDS.get(location, types.LatLng(latitude=35.6762, longitude=139.6503))
                )
            ),
            max_output_tokens=300,
        )
    )
    maps_data = maps_response.text

    # Step 2: Gemini 3 Flash でゲーム展開生成
    prompt = f"""東京サバイバルゲームのゲームマスターとして応答してください。

【状況】
- 場所: {location}
- 所持金: ¥{resource['money']}
- スタミナ: {resource['stamina']}%
- {scenario['resource']['day']}日目

【プレイヤーの行動】
{req.player_choice}

【Google Mapsのリアルデータ】
{maps_data}

必ず以下の形式で返答してください:
[結果] (何が起きたか、具体的な施設名を含めて2〜3文)
[リソース変化] 所持金: ±XXX円 / スタミナ: ±XX%
[次の選択肢]
A) ...
B) ...
C) ..."""

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.7, max_output_tokens=1024)
    )
    response_text = response.text
    elapsed = time.time() - t0

    # リソース更新（簡易）
    resource["money"] = max(0, resource["money"] - 300)
    resource["stamina"] = max(0, resource["stamina"] - 15)

    # ログ保存
    entry = s["logger"].log_interaction(
        scenario_id=scenario["id"],
        player_choice=req.player_choice,
        gemini_response=response_text,
        resources=resource.copy(),
        elapsed_sec=elapsed,
    )

    # 次のシナリオへ
    s["index"] += 1
    game_over = resource["money"] <= 0 or resource["stamina"] <= 0
    clear = s["index"] >= len(SCENARIOS)

    return ActionResponse(
        response_text=response_text,
        entry_id=entry["id"],
        resources=resource,
        scenario_index=s["index"],
        total_scenarios=len(SCENARIOS),
        game_over=game_over,
        clear=clear,
        elapsed_sec=elapsed,
    )


@app.post("/rate")
def rate_interaction(req: RatingRequest):
    s = sessions.get(req.session_id)
    if s:
        s["logger"].add_rating(req.entry_id, req.rating)
    return {"ok": True}


@app.get("/stats/{session_id}")
def get_stats(session_id: str):
    s = sessions.get(session_id)
    if not s:
        return {"error": "not found"}
    return s["logger"].get_session_stats()


@app.get("/next_scenario/{session_id}")
def get_next_scenario(session_id: str):
    s = sessions.get(session_id)
    if not s or s["index"] >= len(SCENARIOS):
        return {"scenario": None}
    return {"scenario": SCENARIOS[s["index"]], "resources": s["resources"]}


@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    html_path = Path(__file__).parent / "index.html"
    return html_path.read_text(encoding="utf-8")
