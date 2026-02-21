"""
マルチモーダル分析の例

画像、テキスト、動画を同時に処理してGemini 3に分析させる例
"""

import os
from dotenv import load_dotenv
import google.generativeai as genai
from PIL import Image
import requests
from io import BytesIO

load_dotenv()

def analyze_multimodal(text_prompt: str, image_url: str = None, image_path: str = None):
    """
    テキストと画像を同時に分析

    Args:
        text_prompt: テキストプロンプト
        image_url: 画像のURL（オプション）
        image_path: ローカル画像のパス（オプション）
    """
    api_key = os.getenv("GEMINI_API_KEY")
    genai.configure(api_key=api_key)

    model = genai.GenerativeModel('gemini-3-pro')

    # 画像の読み込み
    if image_url:
        response = requests.get(image_url)
        img = Image.open(BytesIO(response.content))
    elif image_path:
        img = Image.open(image_path)
    else:
        raise ValueError("画像URLまたはパスを指定してください")

    # マルチモーダル入力で分析
    response = model.generate_content([text_prompt, img])

    return response.text

def analyze_document_with_context(document_text: str, reference_images: list):
    """
    長文ドキュメントと複数の参照画像を統合分析

    Args:
        document_text: 分析対象のテキスト
        reference_images: 参照画像のリスト
    """
    api_key = os.getenv("GEMINI_API_KEY")
    genai.configure(api_key=api_key)

    model = genai.GenerativeModel('gemini-3.1-pro')  # 1Mコンテキスト版

    # コンテンツリストを構築
    contents = [
        "以下のドキュメントと画像を分析し、包括的なレポートを作成してください:",
        document_text
    ]

    # 画像を追加
    for img_path in reference_images:
        contents.append(Image.open(img_path))

    # 大規模コンテキストで分析
    response = model.generate_content(contents)

    return response.text

def main():
    print("=== マルチモーダル分析例 ===\n")

    # 例1: 画像とテキストの統合分析
    print("【例1: 画像の詳細分析】")

    # サンプル画像URL（例として）
    sample_image_url = "https://example.com/sample-chart.png"

    try:
        result = analyze_multimodal(
            text_prompt="""
            この画像に含まれるデータを分析し、以下を提供してください:
            1. グラフの種類と目的
            2. 主要なトレンドや傾向
            3. 異常値や注目すべき点
            4. ビジネス上の推奨事項
            """,
            image_url=sample_image_url
        )
        print(result)
    except Exception as e:
        print(f"画像分析エラー: {e}")
        print("実際の画像URLまたはパスに置き換えて実行してください")

    print("\n" + "="*50 + "\n")

    # 例2: 複数画像と長文の統合分析
    print("【例2: ドキュメント + 複数画像の分析】")

    document = """
    # プロジェクト進捗レポート

    ## 概要
    本プロジェクトは、AIを活用した医療診断支援システムの開発です。
    過去3ヶ月の進捗を以下にまとめます。

    ## 成果
    - モデル精度: 92%達成
    - テストケース: 1000件完了
    - ユーザーフィードバック: 4.5/5.0

    ## 課題
    - データ不均衡の問題
    - 推論速度の改善が必要
    ...
    """

    # 実際には実在する画像パスを指定
    reference_images = [
        # "path/to/chart1.png",
        # "path/to/chart2.png",
    ]

    if reference_images:
        try:
            result = analyze_document_with_context(document, reference_images)
            print(result)
        except Exception as e:
            print(f"ドキュメント分析エラー: {e}")
    else:
        print("画像パスを設定して実行してください")

if __name__ == "__main__":
    main()
