#!/usr/bin/env python3
"""
Tokyo Risk - アバター画像を事前生成するバッチスクリプト

使い方:
    python generate_avatars.py

static/avatars/ に player_001.png 〜 ai_010.png (合計20枚) を保存します。
サーバーを起動する前に一度だけ実行してください。
"""

import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

OUTPUT_DIR = Path(__file__).parent / "static" / "avatars"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── エージェント番号 → キャラクターアーキタイプ ──────────────────────────
ARCHETYPES = [
    "scout ninja with headband, agile and stealthy, short hair",
    "heavy armored infantry, muscular and stoic, full plate armor",
    "sharpshooter sniper, focused and calm, scoped rifle",
    "field medic, gentle and determined, medical cross on uniform",
    "tactical field commander, confident leader, binoculars",
    "combat engineer, inventive, gadgets and tools belt",
    "strategist officer, intelligent, holographic map in hand",
    "martial arts brawler, fierce and energetic, battle stance",
    "stealth infiltrator, mysterious, sleek dark bodysuit",
    "demolitions expert, bold and reckless, explosive gear",
]

# Nano Banana Pro (gemini-3-pro-image-preview) はレート制限があるため逐次処理
MODEL = "gemini-3-pro-image-preview"  # Nano Banana Pro


async def generate_one(agent_id: str, owner: str) -> None:
    out_path = OUTPUT_DIR / f"{agent_id}.png"
    if out_path.exists():
        print(f"  ⏭  {agent_id}: スキップ（既存）")
        return

    agent_num = int(agent_id.split("_")[1])
    archetype = ARCHETYPES[(agent_num - 1) % 10]
    team_style = (
        "blue uniform with cyan highlights, blue eyes, cool blue color palette"
        if owner == "player"
        else "dark red uniform with crimson highlights, red eyes, red and black palette"
    )
    prompt = (
        f"Anime-style character portrait: {archetype}, {team_style}, "
        f"clean white circular background, close-up face and upper body, "
        f"high quality anime illustration, bold linework, vibrant colors, "
        f"game avatar icon style, no text, no watermark, no border"
    )

    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"],
                ),
            ),
        )
        # レスポンスから画像バイトを取得
        candidates = response.candidates or []
        if not candidates or not candidates[0].content:
            print(f"  ⚠️  {agent_id}: レスポンスに候補なし")
            return
        for part in candidates[0].content.parts or []:
            if part.inline_data is not None and part.inline_data.data is not None:
                out_path.write_bytes(bytes(part.inline_data.data))
                print(f"  ✅ {agent_id}: 生成完了 → {out_path.name}")
                return
        print(f"  ⚠️  {agent_id}: レスポンスに画像なし")
    except Exception as e:
        print(f"  ❌ {agent_id}: 失敗 - {e}")


async def main() -> None:
    agents = (
        [(f"player_{i:03d}", "player") for i in range(1, 11)]
        + [(f"ai_{i:03d}", "ai") for i in range(1, 11)]
    )

    print(f"🎨 アバター画像を生成します（{len(agents)}体）")
    print(f"   出力先: {OUTPUT_DIR}\n")

    # Nano Banana Pro のレート制限を考慮して逐次処理
    for aid, owner in agents:
        await generate_one(aid, owner)
        await asyncio.sleep(1)  # 連続リクエストを避ける

    generated = len(list(OUTPUT_DIR.glob("*.png")))
    print(f"\n✨ 完了: {generated}/{len(agents)} 枚")


if __name__ == "__main__":
    asyncio.run(main())
