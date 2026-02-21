"""
ゲームロジック実装

学習するストーリーゲームのコアロジック
"""

import google.generativeai as genai
from typing import Dict, List, Optional
import os
from datetime import datetime

from .data_collector import GameDataCollector

class AdaptiveStoryGame:
    """
    学習するインタラクティブストーリーゲーム

    プレイヤーとの会話から学習し、より良いストーリーを生成する
    """

    def __init__(self, model_name: str = "gemini-3-pro"):
        """
        初期化

        Args:
            model_name: 使用するGeminiモデル
        """
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY環境変数が設定されていません")

        genai.configure(api_key=api_key)

        self.model_name = model_name
        self.model = genai.GenerativeModel(model_name)
        self.collector = GameDataCollector()
        self.sessions: Dict = {}

        # ゲーム設定
        self.system_instruction = """
あなたは創造的なストーリーテラーです。
プレイヤーの選択に基づいて、魅力的で没入感のあるインタラクティブストーリーを作成します。

ガイドライン:
1. プレイヤーの選択を尊重し、その結果を論理的に展開する
2. 予測不可能で面白い展開を提供する
3. 適度な長さ（2-3段落）で応答する
4. プレイヤーに次の選択肢を提示する
5. 感情的に響くストーリーを心がける
"""

    def start_session(self, player_id: str) -> str:
        """
        新しいゲームセッション開始

        Args:
            player_id: プレイヤーID

        Returns:
            ゲームの導入テキスト
        """
        chat = self.model.start_chat()

        intro_prompt = f"""
{self.system_instruction}

新しい冒険を始めます。
プレイヤーに魅力的なオープニングシーンを提示し、
最初の選択肢を与えてください。

ファンタジー、SF、ミステリーなど、どのジャンルでも構いません。
創造的で引き込まれるオープニングをお願いします。
"""

        intro = chat.send_message(intro_prompt)

        self.sessions[player_id] = {
            "chat": chat,
            "history": [
                {
                    "role": "user",
                    "parts": [{"text": intro_prompt}]
                },
                {
                    "role": "model",
                    "parts": [{"text": intro.text}]
                }
            ],
            "choices": [],
            "ratings": [],
            "start_time": datetime.utcnow()
        }

        return intro.text

    def player_action(
        self,
        player_id: str,
        action: str,
        rating: Optional[int] = None
    ) -> str:
        """
        プレイヤーのアクション処理

        Args:
            player_id: プレイヤーID
            action: プレイヤーの行動/選択
            rating: 前回の応答への評価（オプション）

        Returns:
            Geminiからの応答
        """
        if player_id not in self.sessions:
            raise KeyError(f"Session not found for player {player_id}")

        session = self.sessions[player_id]

        # 前回の応答に評価があれば記録
        if rating:
            session["ratings"].append(rating)

            # 高評価なら学習データとして保存
            if rating >= 4 and len(session["history"]) >= 2:
                self.collector.record_interaction(
                    player_id=player_id,
                    conversation=session["history"][-2:],
                    metadata={
                        "rating": rating,
                        "choice": session["choices"][-1] if session["choices"] else None
                    }
                )

        # プレイヤーのアクションを送信
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
        session["choices"].append(action)

        return response.text

    def end_session(self, player_id: str, final_rating: int):
        """
        セッション終了とデータ保存

        Args:
            player_id: プレイヤーID
            final_rating: セッション全体の評価
        """
        if player_id not in self.sessions:
            raise KeyError(f"Session not found for player {player_id}")

        session = self.sessions[player_id]

        # セッション全体のデータを保存
        avg_rating = (
            sum(session["ratings"]) / len(session["ratings"])
            if session["ratings"]
            else final_rating
        )

        # 高評価セッションなら全体を学習データに
        if avg_rating >= 4:
            self.collector.record_interaction(
                player_id=player_id,
                conversation=session["history"],
                metadata={
                    "rating": final_rating,
                    "session_length": len(session["history"]) // 2,
                    "average_rating": avg_rating,
                    "total_choices": len(session["choices"])
                }
            )

        # セッション削除
        del self.sessions[player_id]

    def get_stats(self) -> Dict:
        """
        収集データの統計情報取得

        Returns:
            統計情報
        """
        return self.collector.get_stats()

    def prepare_training_data(self, min_rating: int = 4) -> str:
        """
        ファインチューニング用データ準備

        Args:
            min_rating: 最低評価

        Returns:
            データセットのCloud Storage URI
        """
        return self.collector.prepare_for_tuning(min_rating)
