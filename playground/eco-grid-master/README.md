# Eco-Grid Master 🌿⚡

**リアルタイム電力需給適応エージェント — Era of Experience デモ**

## 概要

東京電力（TEPCO）が公開する電力需給予報データをリアルタイムで取得し、
Gemini が仮想のスマートホームを自律的に管理するエージェントです。

ユーザーが「エアコンを消さないで！」と介入すると、その経験を `experience.json` に蓄積し、
次回の高負荷時には他の家電から制御を試みるよう **動的にシステムプロンプトを更新** します。

## Era of Experience 準拠ポイント

> "Beyond Imitation": 本プロジェクトは Silver & Sutton (2025) が提唱する
> 「経験の時代（Era of Experience）」に基づき、エージェントが実環境からの
> フィードバック（報酬）を通じて自律的に方策を改善する「オンライン学習ループ」を実装しています。

### 報酬関数

```
R = α(Cost Saving) + β(CO₂ Reduction) - γ(User Discomfort)
  = 1.0 × (節約電力 × 30円/kWh) + 0.8 × (節約電力 × 0.45kg/kWh) - 1.5 × (却下フラグ)
```

### オンライン学習の仕組み

1. **経験バッファ** (`experience.json`): 全ての判断・承認・却下を永続化
2. **動的システムプロンプト**: 直近10件の経験 + 却下パターンをプロンプトに自動注入
3. **教訓抽出**: 却下時のユーザーコメントから行動制約を自動生成

## セットアップ

```bash
cd playground/eco-grid-master

# 依存関係インストール
pip install -r requirements.txt

# 環境変数設定
cp .env.example .env
# .env を編集して GEMINI_API_KEY を設定

# 実行
python eco_grid_master.py
```

## 使い方

```
サイクル #1
📡 TEPCOデータ取得中...
⚡ 電力グリッド状況 [2026-02-21 14:00]
   使用率: 82.3%
   [█████████████████████████████████████████░░░░░░░░░]

🤖 Geminiの判断
   リスクレベル: HIGH
   提案: EV充電器をオフ → 削減: 3000W

❓ 「EV充電器」を turn_off します。承認しますか？
   [Enter] = 承認  /  理由を入力して Enter = 却下
   >
```

- **承認**: Enter キーを押す
- **却下**: 理由を入力して Enter（例: `今日は遠出するので充電が必要`）

## データソース

- **TEPCO電力需給予報**: https://www.tepco.co.jp/forecast/html/images/juyo-d1-j.csv
  - 5分ごとに更新
  - 使用率(%)、需要(MW)、供給力(MW)、太陽光発電(MW)

## 仮想スマートホーム

| 家電 | 消費電力 | 優先度 |
|------|---------|--------|
| 冷蔵庫 | 150W | 1 (必須) |
| 照明 | 100W | 2 |
| エアコン | 1000W | 3 |
| テレビ | 200W | 3 |
| 洗濯機 | 800W | 4 |
| 食洗機 | 700W | 4 |
| EV充電器 | 3000W | 5 (延期可) |
| バッテリー | 10kWh | 放電/充電 |

## ファイル構成

```
eco-grid-master/
├── eco_grid_master.py   # メインエージェント
├── experience.json      # 経験バッファ（自動生成）
├── requirements.txt
├── .env.example
└── README.md
```
