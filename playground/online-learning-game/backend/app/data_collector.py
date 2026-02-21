"""
データ収集モジュール

プレイヤーとのインタラクションを収集し、
ファインチューニング用データとして保存
"""

from typing import List, Dict, Optional
import json
from datetime import datetime
from google.cloud import storage
import os

class GameDataCollector:
    """
    ゲームデータ収集クラス

    プレイヤーとのインタラクションを収集し、
    Cloud Storageに保存してファインチューニングに使用
    """

    def __init__(self):
        """初期化"""
        self.bucket_name = os.getenv("GCS_BUCKET")

        if not self.bucket_name:
            print("⚠️  GCS_BUCKETが設定されていません。ローカルファイルに保存します")
            self.use_local = True
            self.local_dir = "data"
            os.makedirs(self.local_dir, exist_ok=True)
        else:
            self.use_local = False
            self.storage_client = storage.Client()
            self.bucket = self.storage_client.bucket(self.bucket_name)

        self.buffer: List[Dict] = []
        self.batch_size = int(os.getenv("BATCH_SIZE", 100))
        self.stats = {
            "total_interactions": 0,
            "high_quality_interactions": 0,
            "total_sessions": 0
        }

    def record_interaction(
        self,
        player_id: str,
        conversation: List[Dict],
        metadata: Dict
    ):
        """
        1つのインタラクションを記録

        Args:
            player_id: プレイヤーID
            conversation: 会話履歴
            metadata: メタデータ（rating, choiceなど）
        """
        data_point = {
            "player_id": player_id,
            "timestamp": datetime.utcnow().isoformat(),
            "contents": conversation,
            "rating": metadata.get("rating"),
            "choice": metadata.get("choice"),
            "outcome": metadata.get("outcome"),
            "session_length": metadata.get("session_length")
        }

        self.buffer.append(data_point)
        self.stats["total_interactions"] += 1

        if metadata.get("rating", 0) >= 4:
            self.stats["high_quality_interactions"] += 1

        # バッファが一杯なら保存
        if len(self.buffer) >= self.batch_size:
            self.flush_to_storage()

    def flush_to_storage(self):
        """バッファをストレージに保存"""
        if not self.buffer:
            return

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f'training_data/{timestamp}.jsonl'

        # JSONL形式で作成
        jsonl_content = '\n'.join(
            json.dumps(item, ensure_ascii=False)
            for item in self.buffer
        )

        if self.use_local:
            # ローカルファイルに保存
            filepath = os.path.join(self.local_dir, f"{timestamp}.jsonl")
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(jsonl_content)
            print(f"✅ {len(self.buffer)}件のインタラクションをローカルに保存: {filepath}")
        else:
            # Cloud Storageに保存
            blob = self.bucket.blob(filename)
            blob.upload_from_string(jsonl_content)
            print(f"✅ {len(self.buffer)}件のインタラクションをCloud Storageに保存: gs://{self.bucket_name}/{filename}")

        self.buffer.clear()

    def prepare_for_tuning(self, min_rating: int = 4) -> str:
        """
        ファインチューニング用にデータをフィルタリング

        Args:
            min_rating: 最低評価

        Returns:
            データセットのURI
        """
        # まずバッファを保存
        self.flush_to_storage()

        high_quality_data = []

        if self.use_local:
            # ローカルファイルから読み込み
            for filename in os.listdir(self.local_dir):
                if not filename.endswith('.jsonl'):
                    continue

                filepath = os.path.join(self.local_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    for line in f:
                        if not line.strip():
                            continue
                        data = json.loads(line)

                        if data.get('rating', 0) >= min_rating:
                            high_quality_data.append({
                                'contents': data['contents']
                            })

            # ファインチューニング用ファイルとして保存
            tuning_filepath = os.path.join(self.local_dir, 'tuning_dataset.jsonl')
            with open(tuning_filepath, 'w', encoding='utf-8') as f:
                for item in high_quality_data:
                    f.write(json.dumps(item, ensure_ascii=False) + '\n')

            print(f"✅ {len(high_quality_data)}件の高品質データを準備: {tuning_filepath}")
            return tuning_filepath

        else:
            # Cloud Storageから読み込み
            blobs = self.bucket.list_blobs(prefix='training_data/')

            for blob in blobs:
                content = blob.download_as_text()
                for line in content.split('\n'):
                    if not line.strip():
                        continue
                    data = json.loads(line)

                    if data.get('rating', 0) >= min_rating:
                        high_quality_data.append({
                            'contents': data['contents']
                        })

            # ファインチューニング用としてアップロード
            tuning_blob = self.bucket.blob('tuning_ready/dataset.jsonl')
            tuning_content = '\n'.join(
                json.dumps(item, ensure_ascii=False)
                for item in high_quality_data
            )
            tuning_blob.upload_from_string(tuning_content)

            uri = f"gs://{self.bucket_name}/tuning_ready/dataset.jsonl"
            print(f"✅ {len(high_quality_data)}件の高品質データを準備: {uri}")
            return uri

    def get_stats(self) -> Dict:
        """
        統計情報取得

        Returns:
            収集データの統計
        """
        return {
            **self.stats,
            "buffer_size": len(self.buffer),
            "ready_for_training": self.stats["high_quality_interactions"] >= 100
        }
