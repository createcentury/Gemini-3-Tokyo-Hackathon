"""FastAPI + WebSocket server for disaster routing web game."""
import asyncio
import json
import os
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

load_dotenv()

from game import DisasterGame
from agent import get_action
from logger import log_step, get_stats

app = FastAPI()

# Serve frontend
FRONTEND = Path(__file__).parent / "frontend"
app.mount("/static", StaticFiles(directory=str(FRONTEND)), name="static")


@app.get("/")
async def root():
    return HTMLResponse((FRONTEND / "index.html").read_text())


@app.get("/api/maps-key")
async def maps_key():
    """Return Maps API key to frontend (never hardcode in HTML)."""
    return {"key": os.getenv("GOOGLE_MAPS_API_KEY", "")}


@app.get("/api/stats")
async def stats():
    return get_stats()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    game = DisasterGame(seed=42)

    # Send initial state
    await websocket.send_json({
        "type":  "state",
        "state": game.get_state(),
        "stats": get_stats(),
    })

    try:
        while True:
            msg = await websocket.receive_json()

            if msg.get("type") == "reset":
                game.reset(seed=msg.get("seed", 42))
                await websocket.send_json({
                    "type":  "state",
                    "state": game.get_state(),
                    "stats": get_stats(),
                })

            elif msg.get("type") == "step":
                # Run one AI turn
                state  = game.get_state()

                await websocket.send_json({"type": "thinking"})

                # Run Gemini in thread to avoid blocking event loop
                loop   = asyncio.get_event_loop()
                action = await loop.run_in_executor(None, get_action, state)

                reward, dispatches, resolved = game.apply_action(action)
                log_step(state, action, reward, action.get("reasoning", ""))

                await websocket.send_json({
                    "type":      "action",
                    "action":    action,
                    "reward":    reward,
                    "dispatches": dispatches,
                    "resolved":  resolved,
                    "state":     game.get_state(),
                    "stats":     get_stats(),
                })

    except WebSocketDisconnect:
        pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
