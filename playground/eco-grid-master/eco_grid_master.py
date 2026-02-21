"""
Eco-Grid Master: リアルタイム電力需給適応エージェント
=======================================================
Era of Experience準拠のオンライン学習デモ

TEPCOの公開電力需給データをリアルタイムで読み込み、
Gemini 3が仮想スマートホームを管理します。
ユーザーの介入（「エアコンを消さないで」など）を
経験バッファに蓄積し、次回の判断を自動改善します。
"""

import os
import io
import json
import time
import requests
import csv
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

# ========== 設定 ==========

TEPCO_CSV_URL = "https://www.tepco.co.jp/forecast/html/images/juyo-d1-j.csv"

# 報酬係数
ALPHA = 1.0  # コスト削減の重み
BETA = 0.8   # CO2削減の重み
GAMMA = 1.5  # ユーザー不満の重み

# 電気代 (円/kWh) と CO2排出係数 (kg/kWh)
ELECTRICITY_PRICE = 30.0
CO2_FACTOR = 0.45

# 高負荷閾値 (%)
HIGH_LOAD_THRESHOLD = 75

# ========== 仮想スマートホーム ==========

INITIAL_APPLIANCES = {
    "ac":              {"name": "エアコン",     "power_w": 1000, "on": True,  "priority": 3},
    "ev_charger":      {"name": "EV充電器",     "power_w": 3000, "on": False, "priority": 5},
    "washing_machine": {"name": "洗濯機",       "power_w": 800,  "on": False, "priority": 4},
    "dishwasher":      {"name": "食洗機",       "power_w": 700,  "on": False, "priority": 4},
    "lighting":        {"name": "照明",         "power_w": 100,  "on": True,  "priority": 2},
    "tv":              {"name": "テレビ",       "power_w": 200,  "on": True,  "priority": 3},
    "refrigerator":    {"name": "冷蔵庫",       "power_w": 150,  "on": True,  "priority": 1},
}

INITIAL_BATTERY = {
    "capacity_kwh": 10.0,
    "current_kwh": 5.0,
    "status": "idle",  # "charging" | "discharging" | "idle"
}

# ========== データクラス ==========

@dataclass
class GridData:
    timestamp: str
    usage_rate: float          # 使用率 (%)
    demand_mw: float           # 実績需要 (MW)
    forecast_mw: float         # 予測需要 (MW)
    supply_mw: float           # 供給力 (MW)
    solar_mw: float = 0.0      # 太陽光発電 (MW)

@dataclass
class Experience:
    timestamp: str
    grid_usage_rate: float
    action: str                # エージェントが提案したアクション
    user_approved: bool        # ユーザーが承認したか
    user_note: str             # ユーザーのコメント
    reward: float              # 実際に得られた報酬
    lesson: str = ""           # Geminiが抽出した教訓

# ========== TEPCO データ取得 ==========

def fetch_tepco_data() -> Optional[GridData]:
    """TEPCOの電力需給予報CSVをリアルタイム取得・解析

    CSV構造 (行14以降):
      DATE, TIME, 当日実績(万kW), 予測値(万kW), 使用率(%), 供給力(万kW)
    実績が0の時間帯（未来）は使用率が空欄になるため、直近の実績値を使用する。
    """
    try:
        resp = requests.get(TEPCO_CSV_URL, timeout=10)
        resp.encoding = "shift_jis"

        now = datetime.now()
        demand_mankw = 0.0
        forecast_mankw = 0.0
        usage_rate = 0.0
        supply_mankw = 0.0
        latest_time = ""

        reader = csv.reader(io.StringIO(resp.text))
        header_found = False
        for row in reader:
            if not header_found:
                # ヘッダー行を探す: "DATE,TIME,当日実績(万kW),..."
                if len(row) >= 5 and row[0].strip() == "DATE":
                    header_found = True
                continue

            if len(row) < 6:
                continue

            # 実績が入っている行のみ使用 (実績>0 かつ 使用率が存在)
            try:
                demand_str = row[2].strip()
                usage_str = row[4].strip()
                supply_str = row[5].strip()
                forecast_str = row[3].strip()

                if not demand_str or not usage_str:
                    continue
                d = float(demand_str)
                u = float(usage_str)
                if d > 0 and u > 0:
                    demand_mankw = d
                    forecast_mankw = float(forecast_str) if forecast_str else d
                    usage_rate = u
                    supply_mankw = float(supply_str) if supply_str else 0.0
                    latest_time = row[1].strip()
            except (ValueError, IndexError):
                continue

        if usage_rate == 0.0:
            print("  [INFO] CSVから実績データを取得できず、予測値を使用")
            # 予測値からフォールバック
            reader2 = csv.reader(io.StringIO(resp.text))
            header_found2 = False
            for row in reader2:
                if not header_found2:
                    if len(row) >= 5 and row[0].strip() == "DATE":
                        header_found2 = True
                    continue
                try:
                    forecast_str = row[3].strip()
                    supply_str = row[5].strip()
                    if forecast_str and supply_str:
                        f = float(forecast_str)
                        s = float(supply_str)
                        if f > 0 and s > 0:
                            forecast_mankw = f
                            supply_mankw = s
                            usage_rate = round(f / s * 100, 1)
                            latest_time = row[1].strip()
                            break
                except (ValueError, IndexError):
                    continue

        # 万kW → GW 表示用に万kWのまま保持 (表示は別途)
        return GridData(
            timestamp=f"{now.strftime('%Y-%m-%d')} {latest_time or now.strftime('%H:%M')}",
            usage_rate=usage_rate,
            demand_mw=demand_mankw,    # 実際は万kW単位 (TEPCO公式単位)
            forecast_mw=forecast_mankw,
            supply_mw=supply_mankw,
            solar_mw=0.0,
        )

    except Exception as e:
        print(f"  [WARN] TEPCO API取得エラー: {e} → デモ値を使用")
        return GridData(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
            usage_rate=72.0,
            demand_mw=3300.0,
            forecast_mw=3400.0,
            supply_mw=4580.0,
            solar_mw=0.0,
        )

# ========== 報酬計算 ==========

def calc_reward(power_saved_w: float, duration_min: float, user_approved: bool) -> float:
    """
    R = α(Cost Saving) + β(CO2 Reduction) - γ(User Discomfort)
    """
    duration_h = duration_min / 60.0
    energy_saved_kwh = power_saved_w / 1000.0 * duration_h

    cost_saving = energy_saved_kwh * ELECTRICITY_PRICE
    co2_reduction = energy_saved_kwh * CO2_FACTOR

    discomfort = 0.0 if user_approved else 1.0

    reward = ALPHA * cost_saving + BETA * co2_reduction - GAMMA * discomfort
    return round(reward, 3)

# ========== 経験バッファ ==========

class ExperienceBuffer:
    def __init__(self, path: str = "experience.json"):
        self.path = path
        self.experiences: list[Experience] = []
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.experiences = [Experience(**d) for d in data]

    def _save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump([asdict(e) for e in self.experiences], f, ensure_ascii=False, indent=2)

    def add(self, exp: Experience):
        self.experiences.append(exp)
        self._save()

    def build_context_prompt(self) -> str:
        """過去の経験からシステムプロンプト用のコンテキストを生成"""
        if not self.experiences:
            return ""

        lines = ["## 過去の経験（オンライン学習）\n"]
        for e in self.experiences[-10:]:  # 直近10件
            approved = "承認" if e.user_approved else "却下"
            lines.append(
                f"- [{e.timestamp}] 使用率{e.grid_usage_rate:.0f}%時に「{e.action}」を提案 → ユーザー{approved} "
                f"(報酬: {e.reward:+.2f}) {': ' + e.user_note if e.user_note else ''}"
            )
            if e.lesson:
                lines.append(f"  教訓: {e.lesson}")

        # 却下パターンのサマリー
        rejections = [e for e in self.experiences if not e.user_approved]
        if rejections:
            lines.append("\n## 避けるべきパターン")
            for r in rejections[-5:]:
                lines.append(f"- 使用率{r.grid_usage_rate:.0f}%時に「{r.action}」は不評: {r.user_note}")

        return "\n".join(lines)

    def total_reward(self) -> float:
        return sum(e.reward for e in self.experiences)

    def total_co2_saved_kg(self) -> float:
        # 近似: 平均200W x 各経験を10分として計算
        return len([e for e in self.experiences if e.user_approved]) * 0.2 * (10/60) * CO2_FACTOR

# ========== Gemini エージェント ==========

class EcoGridAgent:
    def __init__(self, buffer: ExperienceBuffer):
        self.buffer = buffer
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY が設定されていません (.envを確認してください)")
        self.client = genai.Client(api_key=api_key)

        self.appliances = {k: v.copy() for k, v in INITIAL_APPLIANCES.items()}
        self.battery = INITIAL_BATTERY.copy()
        self.last_action_log: list[dict] = []

    def _build_system_prompt(self) -> str:
        experience_ctx = self.buffer.build_context_prompt()
        return f"""あなたは「Eco-Grid Master」、東京のスマートホームを管理するAIエージェントです。

## 役割
TEPCOの電力需給データを分析し、電力グリッドへの負荷を下げながら
ユーザーの快適性を維持する最適な家電制御を提案します。

## 判断基準
- 使用率 < 70%: 通常運転（省エネモード）
- 使用率 70-80%: 優先度4以上の家電をオフ提案
- 使用率 80-90%: 優先度3以上をオフ提案 + バッテリー放電検討
- 使用率 > 90%: 緊急節電（優先度1以外をオフ）

## 家電優先度
1 = 必須（絶対オフにしない: 冷蔵庫）
2 = 重要（照明）
3 = 通常（エアコン、テレビ）
4 = 後回し可（洗濯機、食洗機）
5 = 延期可（EV充電器）

## 報酬関数
R = α(コスト削減) + β(CO₂削減) - γ(ユーザー不満)
α={ALPHA}, β={BETA}, γ={GAMMA}

{experience_ctx}

## 応答形式
必ず以下のJSONで回答してください:
{{
  "analysis": "現在の状況の簡潔な分析（1-2文）",
  "actions": [
    {{"appliance_id": "ac", "action": "turn_off", "reason": "...", "power_saved_w": 1000}},
    {{"appliance_id": "battery", "action": "discharge", "reason": "...", "power_saved_w": 0}}
  ],
  "risk_level": "low|medium|high|critical",
  "estimated_reward": 0.5
}}
actions が空の場合は [] にしてください。
"""

    def get_home_status(self) -> dict:
        on_appliances = {k: v for k, v in self.appliances.items() if v["on"]}
        total_w = sum(v["power_w"] for v in on_appliances.values())
        return {
            "appliances": self.appliances,
            "battery": self.battery,
            "total_consumption_w": total_w,
        }

    def apply_action(self, appliance_id: str, action: str) -> tuple[bool, int]:
        """アクションを適用。(成功フラグ, 削減W数) を返す"""
        if appliance_id == "battery":
            if action == "discharge" and self.battery["current_kwh"] > 0:
                self.battery["status"] = "discharging"
                return True, 0
            return False, 0

        if appliance_id not in self.appliances:
            return False, 0

        app = self.appliances[appliance_id]
        if action == "turn_off" and app["on"]:
            app["on"] = False
            return True, app["power_w"]
        elif action == "turn_on" and not app["on"]:
            app["on"] = True
            return True, -app["power_w"]
        return False, 0

    def revert_action(self, appliance_id: str, action: str):
        """ユーザー却下時にアクションを元に戻す"""
        if appliance_id == "battery":
            self.battery["status"] = "idle"
            return
        if appliance_id not in self.appliances:
            return
        app = self.appliances[appliance_id]
        if action == "turn_off":
            app["on"] = True
        elif action == "turn_on":
            app["on"] = False

    def decide(self, grid: GridData) -> dict:
        """Geminiに現状を渡して制御判断を取得"""
        home = self.get_home_status()
        on_list = [f"{v['name']}({v['power_w']}W)" for k, v in home["appliances"].items() if v["on"]]

        prompt = f"""
現在の電力グリッド状況:
- 時刻: {grid.timestamp}
- 使用率: {grid.usage_rate:.1f}%
- 実績需要: {grid.demand_mw:.0f} MW
- 供給力: {grid.supply_mw:.0f} MW
- 太陽光発電: {grid.solar_mw:.0f} MW

現在のスマートホーム状態:
- 稼働中家電: {', '.join(on_list)}
- 総消費電力: {home['total_consumption_w']} W
- バッテリー: {self.battery['current_kwh']:.1f} / {self.battery['capacity_kwh']} kWh ({self.battery['status']})

最適な制御アクションを決定してください。
"""
        # 利用可能なモデルを順に試す
        models_to_try = ["gemini-2.5-flash", "gemini-3-flash-preview"]
        response = None
        for model_name in models_to_try:
            try:
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=self._build_system_prompt(),
                        temperature=0.3,
                    ),
                )
                break
            except Exception as e:
                print(f"  [WARN] {model_name} 失敗: {e}")
                continue

        if response is None:
            return {"analysis": "API接続エラー", "actions": [], "risk_level": "low", "estimated_reward": 0.0}

        raw = response.text.strip()
        # JSONを抽出
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # JSON解析失敗時はアクションなしで返す
            return {
                "analysis": raw[:200],
                "actions": [],
                "risk_level": "low",
                "estimated_reward": 0.0,
            }

# ========== 表示ユーティリティ ==========

RISK_COLOR = {
    "low": "\033[32m",      # 緑
    "medium": "\033[33m",   # 黄
    "high": "\033[31m",     # 赤
    "critical": "\033[35m", # マゼンタ
}
RESET = "\033[0m"
BOLD = "\033[1m"

def print_grid_status(grid: GridData):
    color = RISK_COLOR.get("low", "")
    if grid.usage_rate >= 90:
        color = RISK_COLOR["critical"]
    elif grid.usage_rate >= 80:
        color = RISK_COLOR["high"]
    elif grid.usage_rate >= 70:
        color = RISK_COLOR["medium"]

    bar_len = int(grid.usage_rate / 2)
    bar = "█" * bar_len + "░" * (50 - bar_len)
    print(f"\n{BOLD}⚡ 電力グリッド状況 [{grid.timestamp}]{RESET}")
    print(f"   使用率: {color}{grid.usage_rate:.1f}%{RESET}")
    print(f"   [{color}{bar}{RESET}]")
    print(f"   需要: {grid.demand_mw:.0f} 万kW  |  供給: {grid.supply_mw:.0f} 万kW")

def print_home_status(agent: EcoGridAgent):
    home = agent.get_home_status()
    print(f"\n{BOLD}🏠 スマートホーム状態{RESET}")
    for kid, v in home["appliances"].items():
        status = "🟢 ON " if v["on"] else "⚫ OFF"
        print(f"   {status} {v['name']:12s} ({v['power_w']:4d}W)  優先度:{v['priority']}")
    bat = home["battery"]
    pct = bat["current_kwh"] / bat["capacity_kwh"] * 100
    print(f"   🔋 バッテリー: {bat['current_kwh']:.1f}/{bat['capacity_kwh']} kWh ({pct:.0f}%)  [{bat['status']}]")
    print(f"   📊 総消費電力: {home['total_consumption_w']} W")

def print_decision(decision: dict):
    risk = decision.get("risk_level", "low")
    color = RISK_COLOR.get(risk, "")
    print(f"\n{BOLD}🤖 Geminiの判断{RESET}")
    print(f"   リスクレベル: {color}{risk.upper()}{RESET}")
    print(f"   分析: {decision.get('analysis', '')}")
    actions = decision.get("actions", [])
    if actions:
        print(f"   提案アクション ({len(actions)}件):")
        for a in actions:
            app_id = a.get("appliance_id", "?")
            action = a.get("action", "?")
            reason = a.get("reason", "")
            saved = a.get("power_saved_w", 0)
            print(f"     → {action:10s} [{app_id}]  削減: {saved}W  理由: {reason}")
    else:
        print("   → 現在は制御アクション不要")

def print_score(buffer: ExperienceBuffer):
    total_r = buffer.total_reward()
    co2 = buffer.total_co2_saved_kg()
    n = len(buffer.experiences)
    print(f"\n{BOLD}📈 累積スコア{RESET}  経験数:{n}  総報酬:{total_r:+.2f}  CO₂削減:{co2:.3f}kg")

# ========== メインループ ==========

def extract_lesson(buffer: ExperienceBuffer, exp: Experience) -> str:
    """経験から教訓を抽出（簡易ルールベース）"""
    if not exp.user_approved and exp.user_note:
        return f"使用率{exp.grid_usage_rate:.0f}%時は「{exp.action}」を避ける: {exp.user_note}"
    if exp.user_approved and exp.reward > 0:
        return f"使用率{exp.grid_usage_rate:.0f}%時の「{exp.action}」は効果的"
    return ""

def main():
    print(f"\n{'='*60}")
    print(f"{BOLD}  🌿 Eco-Grid Master  ― Era of Experience デモ{RESET}")
    print(f"{'='*60}")
    print("  TEPCOリアルタイムデータで仮想スマートホームを制御します")
    print("  Ctrl+C で終了\n")

    buffer = ExperienceBuffer(
        path=os.path.join(os.path.dirname(__file__), "experience.json")
    )
    agent = EcoGridAgent(buffer)

    cycle = 0
    try:
        while True:
            cycle += 1
            print(f"\n{'─'*60}")
            print(f"  サイクル #{cycle}  ({datetime.now().strftime('%H:%M:%S')})")
            print(f"{'─'*60}")

            # 1. TEPCOデータ取得
            print("📡 TEPCOデータ取得中...")
            grid = fetch_tepco_data()
            print_grid_status(grid)

            # 2. ホーム状態表示
            print_home_status(agent)

            # 3. 高負荷でない場合はスキップ
            if grid.usage_rate < HIGH_LOAD_THRESHOLD:
                print(f"\n✅ 使用率 {grid.usage_rate:.1f}% < {HIGH_LOAD_THRESHOLD}% → 介入不要。通常運転を継続。")
                print_score(buffer)
                print(f"\n⏳ 60秒後に再チェック... (Enter で即時更新 / Ctrl+C で終了)")
                try:
                    input()
                except (EOFError, KeyboardInterrupt):
                    break
                continue

            # 4. Geminiに判断を求める
            print(f"\n🧠 Geminiが分析中... (使用率 {grid.usage_rate:.1f}%)")
            decision = agent.decide(grid)
            print_decision(decision)

            actions = decision.get("actions", [])
            if not actions:
                print("\n✅ Geminiはアクション不要と判断しました。")
                print_score(buffer)
                time.sleep(30)
                continue

            # 5. ユーザーへの確認ループ
            total_saved_w = 0
            all_approved = True
            rejection_note = ""

            for action_item in actions:
                app_id = action_item.get("appliance_id", "")
                action = action_item.get("action", "")
                power_saved = action_item.get("power_saved_w", 0)

                app_name = agent.appliances.get(app_id, {}).get("name", app_id) if app_id != "battery" else "バッテリー"

                print(f"\n❓ 「{app_name}」を {action} します。承認しますか？")
                print("   [Enter] = 承認  /  理由を入力して Enter = 却下")
                try:
                    user_input = input("   > ").strip()
                except (EOFError, KeyboardInterrupt):
                    user_input = ""

                approved = (user_input == "")
                success, saved = agent.apply_action(app_id, action)

                if not approved:
                    # 却下 → アクションを元に戻す
                    agent.revert_action(app_id, action)
                    all_approved = False
                    rejection_note = user_input

                reward = calc_reward(
                    power_saved_w=power_saved if approved else 0,
                    duration_min=30,  # 次のサイクルまでの推定時間
                    user_approved=approved,
                )

                exp = Experience(
                    timestamp=grid.timestamp,
                    grid_usage_rate=grid.usage_rate,
                    action=f"{action} {app_name}",
                    user_approved=approved,
                    user_note=user_input if not approved else "",
                    reward=reward,
                )
                exp.lesson = extract_lesson(buffer, exp)
                buffer.add(exp)

                status_str = "✅ 承認" if approved else f"❌ 却下 ({user_input})"
                print(f"   {status_str}  →  報酬: {reward:+.3f}  |  教訓: {exp.lesson or 'なし'}")

                if approved:
                    total_saved_w += power_saved

            # 6. サイクルサマリー
            print(f"\n{'─'*60}")
            print(f"  このサイクルの削減電力: {total_saved_w} W")
            energy_kwh = total_saved_w / 1000 * 0.5
            print(f"  推定節約: {energy_kwh * ELECTRICITY_PRICE:.1f}円 / CO₂削減: {energy_kwh * CO2_FACTOR * 1000:.1f}g")
            print_score(buffer)

            print(f"\n⏳ 次のサイクルまで待機中... (Enter で即時更新)")
            try:
                input()
            except (EOFError, KeyboardInterrupt):
                break

    except KeyboardInterrupt:
        pass

    print(f"\n{'='*60}")
    print(f"  セッション終了")
    print_score(buffer)
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
