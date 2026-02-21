"""Gemini agent for power grid balancing — with in-context online learning."""
import json
import os
import re

from google import genai
from google.genai import types
from dotenv import load_dotenv
from logger import load_log

load_dotenv()

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
MODEL = "gemini-3-flash-preview"

SYSTEM_PROMPT = """You are an AI grid operator for the Tokyo power grid.
Each hour you must balance electricity supply and demand to avoid blackouts and
minimise carbon emissions.

Controllable source: thermal (0-100% of 8000 MW capacity).
Fixed sources: nuclear (3000 MW), hydro (1000 MW), solar (follows sun curve), wind (variable).

Goals (in priority order):
1. Keep supply within ±3% of demand (avoid blackouts AND waste)
2. Minimise thermal usage (high carbon)
3. Provide brief reasoning for your decision

Respond ONLY with valid JSON:
{
  "thermal_pct": <int 0-100>,
  "reasoning": "<one sentence>"
}
"""


def _build_few_shot_context(n: int = 3) -> str:
    """Return top-n highest-reward past steps as few-shot examples."""
    log = load_log()
    if not log:
        return ""
    top = sorted(log, key=lambda e: e["reward"], reverse=True)[:n]
    lines = ["--- Past high-reward decisions (learn from these) ---"]
    for i, entry in enumerate(top, 1):
        s = entry["state"]
        a = entry["action"]
        lines.append(
            f"\nExample {i} (reward={entry['reward']:.3f}): "
            f"hour={s.get('hour','?'):02d}:00 "
            f"demand={s.get('demand_mw','?')}MW "
            f"supply={s.get('supply_mw','?')}MW "
            f"-> thermal={a.get('thermal_pct','?')}% | {entry['reasoning']}"
        )
    lines.append("--- End of examples ---\n")
    return "\n".join(lines)


def get_action(state: dict, screenshot_bytes: bytes | None = None) -> dict:
    """
    Ask Gemini to set thermal generation percentage.
    Injects top past decisions for in-context online learning.
    """
    few_shot = _build_few_shot_context(n=3)

    user_content = []

    if screenshot_bytes:
        user_content.append(
            types.Part.from_bytes(data=screenshot_bytes, mime_type="image/png")
        )

    prompt = ""
    if few_shot:
        prompt += few_shot + "\n"
    prompt += f"Current grid state:\n{json.dumps(state, ensure_ascii=False, indent=2)}\n\nSet thermal output now."

    user_content.append(types.Part.from_text(text=prompt))

    response = client.models.generate_content(
        model=MODEL,
        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
        contents=user_content,
    )

    raw = response.text.strip()
    raw = re.sub(r"^```[a-z]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"thermal_pct": 50, "reasoning": "parse error"}
