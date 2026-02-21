"""
データモデル定義
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime

class PlayerAction(BaseModel):
    """プレイヤーのアクション"""
    player_id: str = Field(..., description="プレイヤーID")
    text: str = Field(..., description="プレイヤーの入力テキスト")
    rating: Optional[int] = Field(None, ge=1, le=5, description="この応答への評価（1-5）")

class GameResponse(BaseModel):
    """ゲームからの応答"""
    text: str = Field(..., description="Geminiからの応答テキスト")
    session_active: bool = Field(True, description="セッションが続行中か")
    metadata: Optional[Dict] = Field(default=None, description="追加メタデータ")

class SessionRating(BaseModel):
    """セッション全体の評価"""
    player_id: str = Field(..., description="プレイヤーID")
    rating: int = Field(..., ge=1, le=5, description="セッション全体の評価（1-5）")
    feedback: Optional[str] = Field(None, description="フィードバックコメント")

class TrainingDataPoint(BaseModel):
    """ファインチューニング用のデータポイント"""
    player_id: str
    timestamp: datetime
    contents: List[Dict]
    rating: Optional[int] = None
    choice: Optional[str] = None
    outcome: Optional[str] = None
    session_length: Optional[int] = None

class GameStats(BaseModel):
    """ゲーム統計"""
    total_sessions: int
    total_interactions: int
    average_rating: float
    data_points_collected: int
    ready_for_training: bool
