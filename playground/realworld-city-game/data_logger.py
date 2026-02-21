"""
ゲームデータロガー
==================
プレイヤーのインタラクションを収集し、Vertex AI ファインチューニング用の
JSONL データを生成する。

学習データ形式 (Gemini Fine-tuning):
{
  "contents": [
    {"role": "user",   "parts": [{"text": "...シナリオ + プレイヤー入力..."}]},
    {"role": "model",  "parts": [{"text": "...Gemini の応答..."}]}
  ]
}
"""

import json
import uuid
import os
from datetime import datetime
from typing import Optional
from pathlib import Path


class GameDataLogger:
    def __init__(self, player_id: str, data_dir: str = "data"):
        self.player_id = player_id
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        # セッションごとのログファイル
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_file = self.data_dir / f"session_{player_id}_{timestamp}.jsonl"

        # Fine-tuning 用データファイル (高評価のみ)
        self.finetune_file = self.data_dir / "finetune_ready.jsonl"

        self.interactions = []

    def log_interaction(
        self,
        scenario_id: str,
        player_choice: str,
        gemini_response: str,
        resources: dict,
        elapsed_sec: float = 0.0,
    ) -> dict:
        """
        1インタラクションをログに記録する

        Returns:
            記録したエントリ（rating追加のために返す）
        """
        entry = {
            "id": str(uuid.uuid4())[:8],
            "timestamp": datetime.now().isoformat(),
            "player_id": self.player_id,
            "scenario_id": scenario_id,
            "player_choice": player_choice,
            "gemini_response": gemini_response,
            "resources_at_time": resources,
            "elapsed_sec": elapsed_sec,
            "rating": None,  # 後で add_rating() で追加
        }

        self.interactions.append(entry)

        # JSONL に即時書き込み（クラッシュ時のデータ保護）
        with open(self.session_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        return entry

    def add_rating(self, entry_id: str, rating: int):
        """プレイヤーの評価を既存エントリに追加"""
        for entry in self.interactions:
            if entry["id"] == entry_id:
                entry["rating"] = rating
                # Fine-tuning データに追加（評価 4以上のみ）
                if rating >= 4:
                    self._append_finetune_data(entry)
                break

        # セッションファイルを更新（評価付きで再書き込み）
        self._rewrite_session_file()

    def _append_finetune_data(self, entry: dict):
        """
        高評価のインタラクションを Fine-tuning 用 JSONL に追加

        Gemini Fine-tuning フォーマット:
        https://cloud.google.com/vertex-ai/generative-ai/docs/models/gemini-supervised-tuning-prepare
        """
        finetune_entry = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": self._build_user_prompt(entry)}],
                },
                {
                    "role": "model",
                    "parts": [{"text": entry["gemini_response"]}],
                },
            ],
            "metadata": {
                "scenario_id": entry["scenario_id"],
                "rating": entry["rating"],
                "source": "realworld_city_game",
            },
        }

        with open(self.finetune_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(finetune_entry, ensure_ascii=False) + "\n")

    def _build_user_prompt(self, entry: dict) -> str:
        """ユーザープロンプトを再構築（Fine-tuning 用）"""
        r = entry["resources_at_time"]
        return (
            f"シナリオ: {entry['scenario_id']}\n"
            f"リソース: 所持金¥{r.get('money', '?')}, スタミナ{r.get('stamina', '?')}%\n"
            f"プレイヤーの行動: {entry['player_choice']}"
        )

    def _rewrite_session_file(self):
        """セッションファイルを最新状態で上書き"""
        with open(self.session_file, "w", encoding="utf-8") as f:
            for entry in self.interactions:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def get_session_stats(self) -> dict:
        """セッションの統計情報を返す"""
        rated = [e for e in self.interactions if e["rating"] is not None]
        avg_rating = (
            sum(e["rating"] for e in rated) / len(rated) if rated else 0.0
        )
        finetune_count = len([e for e in self.interactions if (e.get("rating") or 0) >= 4])

        return {
            "total_interactions": len(self.interactions),
            "rated_count": len(rated),
            "avg_rating": avg_rating,
            "finetune_ready_count": finetune_count,
            "log_file": str(self.session_file),
            "finetune_file": str(self.finetune_file),
        }

    def export_finetune_summary(self) -> dict:
        """
        Fine-tuning データの件数を確認する

        Returns:
            {"total_entries": int, "file_path": str}
        """
        if not self.finetune_file.exists():
            return {"total_entries": 0, "file_path": str(self.finetune_file)}

        count = 0
        with open(self.finetune_file, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    count += 1

        return {"total_entries": count, "file_path": str(self.finetune_file)}
