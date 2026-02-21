"""
Vertex AIでGeminiモデルをファインチューニング

使い方:
    python fine_tune.py --dataset gs://your-bucket/tuning_ready/dataset.jsonl
"""

import argparse
from google.cloud import aiplatform
import os
from dotenv import load_dotenv

load_dotenv()

def fine_tune_gemini(
    training_data_uri: str,
    model_name: str = "gemini-2.5-flash",
    epochs: int = 3,
    adapter_size: str = "ADAPTER_SIZE_SIXTEEN"
):
    """
    Vertex AIでGeminiをファインチューニング

    Args:
        training_data_uri: トレーニングデータのGCS URI
        model_name: ベースモデル
        epochs: エポック数
        adapter_size: アダプターサイズ（4, 8, 16, 32）
    """

    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("VERTEX_AI_LOCATION", "us-central1")

    if not project_id:
        raise ValueError("GOOGLE_CLOUD_PROJECT環境変数が設定されていません")

    print(f"🚀 ファインチューニング開始")
    print(f"  プロジェクト: {project_id}")
    print(f"  ロケーション: {location}")
    print(f"  ベースモデル: {model_name}")
    print(f"  データセット: {training_data_uri}")
    print(f"  エポック: {epochs}")
    print(f"  アダプターサイズ: {adapter_size}")

    aiplatform.init(
        project=project_id,
        location=location
    )

    # ファインチューニングジョブの作成
    tuning_job = aiplatform.SupervisedTuningJob.create(
        model=model_name,
        training_data_uri=training_data_uri,
        validation_data_uri=None,  # オプション
        tuning_config={
            "epoch_count": epochs,
            "learning_rate_multiplier": 1.0,
            "adapter_size": adapter_size
        }
    )

    print(f"\n✅ ファインチューニングジョブを作成しました")
    print(f"  ジョブID: {tuning_job.resource_name}")
    print(f"\n⏳ ファインチューニング実行中...")
    print(f"  （これには数時間かかる場合があります）")

    # ジョブの完了を待つ
    tuning_job.wait()

    print(f"\n🎉 ファインチューニングが完了しました！")
    print(f"  調整済みモデル: {tuning_job.tuned_model_endpoint_name}")
    print(f"\n次のステップ:")
    print(f"  1. .envファイルのTUNED_MODELを更新してください")
    print(f"  2. ゲームサーバーを再起動してください")
    print(f"  3. 改善を確認してください！")

    return tuning_job.tuned_model_endpoint_name

def main():
    parser = argparse.ArgumentParser(
        description="Geminiモデルをファインチューニング"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        required=True,
        help="トレーニングデータのGCS URI (gs://bucket/path/to/dataset.jsonl)"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gemini-2.5-flash",
        help="ベースモデル名"
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=3,
        help="エポック数"
    )
    parser.add_argument(
        "--adapter-size",
        type=str,
        default="ADAPTER_SIZE_SIXTEEN",
        choices=[
            "ADAPTER_SIZE_FOUR",
            "ADAPTER_SIZE_EIGHT",
            "ADAPTER_SIZE_SIXTEEN",
            "ADAPTER_SIZE_THIRTY_TWO"
        ],
        help="アダプターサイズ"
    )

    args = parser.parse_args()

    try:
        tuned_model = fine_tune_gemini(
            training_data_uri=args.dataset,
            model_name=args.model,
            epochs=args.epochs,
            adapter_size=args.adapter_size
        )

        print(f"\n📝 .envファイルに以下を追加してください:")
        print(f"TUNED_MODEL={tuned_model}")

    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        raise

if __name__ == "__main__":
    main()
