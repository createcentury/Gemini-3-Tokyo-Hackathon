# Gemini API サンプルコード集

このディレクトリには、Gemini 3 APIの基本的な使い方を示すサンプルコードが含まれています。

## セットアップ

### 1. APIキーの取得
1. [Google AI Studio](https://aistudio.google.com/) にアクセス
2. APIキーを生成
3. `.env`ファイルに保存

```bash
# .env
GEMINI_API_KEY=your_api_key_here
```

### 2. 依存関係のインストール

#### Python
```bash
cd python
pip install -r requirements.txt
```

#### JavaScript/TypeScript
```bash
cd javascript
npm install
```

## サンプルコード

### basic_chat.py
基本的なチャット機能

### multimodal_analysis.py
画像・動画・テキストの同時処理

### thinking_mode.py
Thinking Controlの使用例

### function_calling.py
カスタムツールの定義と使用

### streaming_response.py
ストリーミング応答の実装

### agent_example.py
エージェント機能の実装例

## 実行方法

```bash
# Python
python python/basic_chat.py

# JavaScript
npm run start:basic
```
