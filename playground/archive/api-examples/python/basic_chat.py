"""
基本的なGemini APIチャット実装例

このスクリプトは、Gemini 3 APIを使用した最も基本的なチャット機能を示します。
"""

import os
from dotenv import load_dotenv
import google.generativeai as genai

# 環境変数の読み込み
load_dotenv()

def main():
    # APIキーの設定
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY環境変数が設定されていません")

    genai.configure(api_key=api_key)

    # モデルの初期化
    model = genai.GenerativeModel('gemini-3-pro')

    print("Gemini 3 チャットボット")
    print("終了するには 'quit' と入力してください\n")

    # チャット履歴を保持
    chat = model.start_chat(history=[])

    while True:
        # ユーザー入力
        user_input = input("あなた: ")

        if user_input.lower() in ['quit', 'exit', '終了']:
            print("チャットを終了します。")
            break

        try:
            # Geminiからの応答
            response = chat.send_message(user_input)
            print(f"\nGemini: {response.text}\n")

        except Exception as e:
            print(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    main()
