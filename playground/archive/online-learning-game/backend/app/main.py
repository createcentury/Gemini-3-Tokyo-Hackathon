"""
オンライン学習ゲーム - メインAPI

Gemini AIがプレイヤーとのインタラクションから学習するゲームのバックエンド
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv

from .game_logic import AdaptiveStoryGame
from .models import PlayerAction, GameResponse, SessionRating

load_dotenv()

app = FastAPI(
    title="Adaptive Learning Game API",
    description="Gemini AIが学習するゲームのAPI",
    version="0.1.0"
)

# CORS設定（フロントエンドからのアクセスを許可）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.jsのデフォルトポート
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ゲームインスタンス
game = AdaptiveStoryGame(
    model_name=os.getenv("BASE_MODEL", "gemini-3-pro")
)

@app.get("/")
async def root():
    """ヘルスチェック"""
    return {
        "status": "ok",
        "message": "Adaptive Learning Game API",
        "model": game.model_name
    }

@app.post("/session/start", response_model=GameResponse)
async def start_session(player_id: str):
    """
    新しいゲームセッションを開始

    Args:
        player_id: プレイヤーID

    Returns:
        ゲームの最初のメッセージ
    """
    try:
        intro_text = game.start_session(player_id)
        return GameResponse(
            text=intro_text,
            session_active=True
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/action", response_model=GameResponse)
async def player_action(action: PlayerAction):
    """
    プレイヤーのアクションを処理

    Args:
        action: プレイヤーの行動とメタデータ

    Returns:
        Geminiからの応答
    """
    try:
        response_text = game.player_action(
            player_id=action.player_id,
            action=action.text,
            rating=action.rating
        )

        return GameResponse(
            text=response_text,
            session_active=True
        )
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail="セッションが見つかりません。先に /session/start を呼び出してください"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/session/end")
async def end_session(rating: SessionRating):
    """
    セッション終了とデータ保存

    Args:
        rating: セッション全体の評価

    Returns:
        確認メッセージ
    """
    try:
        game.end_session(
            player_id=rating.player_id,
            final_rating=rating.rating
        )

        return {
            "message": "セッションを終了しました。ご協力ありがとうございました！",
            "data_saved": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_stats():
    """
    収集データの統計情報

    Returns:
        データ収集の統計
    """
    try:
        stats = game.get_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/training/prepare")
async def prepare_training_data(min_rating: int = 4):
    """
    ファインチューニング用データの準備

    Args:
        min_rating: 最低評価（これ以上のデータのみ使用）

    Returns:
        データセットのURI
    """
    try:
        dataset_uri = game.prepare_training_data(min_rating)
        return {
            "message": "トレーニングデータの準備が完了しました",
            "dataset_uri": dataset_uri,
            "next_step": "training/fine_tune.py を実行してください"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
