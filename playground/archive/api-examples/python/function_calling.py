"""
Function Calling（ツール使用）の例

Gemini 3にカスタムツールを定義して使用させる例
"""

import os
from dotenv import load_dotenv
import google.generativeai as genai
import json

load_dotenv()

# カスタム関数の定義
def get_weather(city: str, unit: str = "celsius") -> dict:
    """
    天気情報を取得する関数（ダミー実装）

    実際のアプリケーションでは、ここで天気APIを呼び出します
    """
    # ダミーデータ
    weather_data = {
        "東京": {"temp": 15, "condition": "晴れ", "humidity": 45},
        "大阪": {"temp": 18, "condition": "曇り", "humidity": 55},
        "札幌": {"temp": 5, "condition": "雪", "humidity": 70},
    }

    data = weather_data.get(city, {"temp": 20, "condition": "不明", "humidity": 50})

    if unit == "fahrenheit":
        data["temp"] = data["temp"] * 9/5 + 32

    return {
        "city": city,
        "temperature": data["temp"],
        "unit": unit,
        "condition": data["condition"],
        "humidity": data["humidity"]
    }

def search_flights(origin: str, destination: str, date: str) -> list:
    """
    フライト検索関数（ダミー実装）
    """
    return [
        {
            "flight_number": "JL001",
            "airline": "JAL",
            "departure": "10:00",
            "arrival": "12:00",
            "price": 25000
        },
        {
            "flight_number": "NH002",
            "airline": "ANA",
            "departure": "14:00",
            "arrival": "16:00",
            "price": 23000
        }
    ]

# ツール定義
weather_tool = {
    "name": "get_weather",
    "description": "指定された都市の現在の天気情報を取得します",
    "parameters": {
        "type": "object",
        "properties": {
            "city": {
                "type": "string",
                "description": "天気を知りたい都市名"
            },
            "unit": {
                "type": "string",
                "enum": ["celsius", "fahrenheit"],
                "description": "温度の単位"
            }
        },
        "required": ["city"]
    }
}

flight_search_tool = {
    "name": "search_flights",
    "description": "出発地、目的地、日付から利用可能なフライトを検索します",
    "parameters": {
        "type": "object",
        "properties": {
            "origin": {
                "type": "string",
                "description": "出発地の都市名"
            },
            "destination": {
                "type": "string",
                "description": "目的地の都市名"
            },
            "date": {
                "type": "string",
                "description": "出発日（YYYY-MM-DD形式）"
            }
        },
        "required": ["origin", "destination", "date"]
    }
}

def execute_function_call(function_call):
    """
    Geminiから要求された関数を実行
    """
    function_name = function_call.name
    function_args = function_call.args

    if function_name == "get_weather":
        return get_weather(**function_args)
    elif function_name == "search_flights":
        return search_flights(**function_args)
    else:
        return {"error": f"Unknown function: {function_name}"}

def main():
    api_key = os.getenv("GEMINI_API_KEY")
    genai.configure(api_key=api_key)

    # ツールを登録したモデルを作成
    model = genai.GenerativeModel(
        'gemini-3-pro',
        tools=[weather_tool, flight_search_tool]
    )

    print("=== Function Calling デモ ===\n")

    # 例1: 天気情報の取得
    print("【例1: 天気情報の取得】")
    prompt1 = "東京の天気を教えてください"

    chat = model.start_chat()
    response = chat.send_message(prompt1)

    # Function Callの確認
    if response.candidates[0].content.parts[0].function_call:
        function_call = response.candidates[0].content.parts[0].function_call
        print(f"関数呼び出し: {function_call.name}")
        print(f"引数: {dict(function_call.args)}")

        # 関数を実行
        result = execute_function_call(function_call)
        print(f"結果: {result}")

        # 結果をGeminiに返して最終応答を得る
        final_response = chat.send_message(
            genai.protos.Content(
                parts=[genai.protos.Part(
                    function_response=genai.protos.FunctionResponse(
                        name=function_call.name,
                        response={"result": result}
                    )
                )]
            )
        )
        print(f"\nGeminiの応答: {final_response.text}")

    print("\n" + "="*50 + "\n")

    # 例2: 複数ツールの連続使用
    print("【例2: 複数ツールの使用】")
    prompt2 = "明日、東京から大阪に行きたいです。天気とフライトを調べてください。"

    chat2 = model.start_chat()
    response2 = chat2.send_message(prompt2)

    # 複数の関数呼び出しに対応
    for part in response2.candidates[0].content.parts:
        if part.function_call:
            function_call = part.function_call
            print(f"\n関数呼び出し: {function_call.name}")
            result = execute_function_call(function_call)
            print(f"結果: {json.dumps(result, ensure_ascii=False, indent=2)}")

if __name__ == "__main__":
    main()
