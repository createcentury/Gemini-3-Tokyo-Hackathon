"""
Thinking Controlを使用した高度な推論例

Gemini 3の新機能「Thinking Control」を使用して、
モデルの思考の深さを制御する例を示します。
"""

import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

def generate_with_thinking(prompt: str, thinking_level: int = 3):
    """
    Thinking Controlを使用してコンテンツを生成

    Args:
        prompt: 入力プロンプト
        thinking_level: 思考の深さ (0-5)
            0: 即座の応答
            3: 中程度の思考
            5: 最も深い思考
    """
    api_key = os.getenv("GEMINI_API_KEY")
    genai.configure(api_key=api_key)

    model = genai.GenerativeModel('gemini-3-pro')

    # Thinking Levelを設定してリクエスト
    # 注: この機能はAPIバージョンによって異なる可能性があります
    generation_config = {
        "thinking_level": thinking_level,
        "temperature": 0.7,
    }

    response = model.generate_content(
        prompt,
        generation_config=generation_config
    )

    return response.text

def main():
    # 複雑な問題を異なる思考レベルで解く
    problem = """
    以下の最適化問題を解いてください:

    あなたは配送ルートを最適化する必要があります。
    10の配送先があり、それぞれの座標と優先度が与えられています。
    燃料コストを最小化しつつ、優先度の高い配送先を優先するルートを提案してください。

    配送先データ:
    1. (2, 3) - 優先度: 高
    2. (5, 7) - 優先度: 中
    3. (1, 1) - 優先度: 低
    ...（省略）

    制約:
    - 開始地点: (0, 0)
    - 最大走行距離: 50km
    - 営業時間: 9:00-18:00
    """

    print("=== Thinking Level 比較 ===\n")

    # レベル1: 浅い思考
    print("【Thinking Level 1 - 高速だが浅い思考】")
    response_1 = generate_with_thinking(problem, thinking_level=1)
    print(response_1)
    print("\n" + "="*50 + "\n")

    # レベル5: 深い思考
    print("【Thinking Level 5 - 深い思考（時間がかかる）】")
    response_5 = generate_with_thinking(problem, thinking_level=5)
    print(response_5)
    print("\n" + "="*50 + "\n")

if __name__ == "__main__":
    main()
