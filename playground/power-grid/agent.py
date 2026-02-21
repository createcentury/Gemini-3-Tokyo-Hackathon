"""Gemini agent for power grid balancing decisions."""
import json
import os
import re

from google import genai
from google.genai import types
from dotenv import load_dotenv

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


def get_action(state: dict, screenshot_bytes: bytes | None = None) -> dict:
    """
    Ask Gemini to set thermal generation percentage.
    state: serializable grid state dict
    """
    from google.genai import types as gtypes

    user_content = []

    if screenshot_bytes:
        user_content.append(
            gtypes.Part.from_bytes(data=screenshot_bytes, mime_type="image/png")
        )

    user_content.append(
        gtypes.Part.from_text(
            text=f"Current grid state:\n{json.dumps(state, ensure_ascii=False, indent=2)}\n\nSet thermal output now."
        )
    )

    response = client.models.generate_content(
        model=MODEL,
        config=gtypes.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
        contents=user_content,
    )

    raw = response.text.strip()
    raw = re.sub(r"^```[a-z]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"thermal_pct": 50, "reasoning": "parse error"}
