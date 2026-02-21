"""Gemini agent for disaster routing decisions — with in-context online learning."""
import base64
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

SYSTEM_PROMPT = """You are an emergency dispatch AI for Tokyo.
Each turn you receive the current city state and must allocate limited emergency resources
to districts with active incidents.

Your goal:
- Prioritize high-severity incidents
- Consider district hazard levels and population density
- Leave some resources in reserve for future incidents
- Resolve as many incidents as possible per turn

Respond ONLY with valid JSON in this exact format:
{
  "allocations": [
    {"district_idx": <int>, "resource": "<ambulance|fire_truck|police>", "count": <int>}
  ],
  "reasoning": "<one sentence explaining your strategy>"
}
"""


def _build_few_shot_context(n: int = 3) -> str:
    """Return the top-n highest-reward past experiences as few-shot examples."""
    log = load_log()
    if not log:
        return ""
    top = sorted(log, key=lambda e: e["reward"], reverse=True)[:n]
    lines = ["--- Past high-reward examples (learn from these) ---"]
    for i, entry in enumerate(top, 1):
        lines.append(f"\nExample {i} (reward={entry['reward']:.1f}):")
        lines.append(f"  Action taken: {json.dumps(entry['action'], ensure_ascii=False)}")
        lines.append(f"  Reasoning: {entry['reasoning']}")
    lines.append("--- End of examples ---\n")
    return "\n".join(lines)


def get_action(state: dict, screenshot_bytes: bytes | None = None) -> dict:
    """
    Ask Gemini to decide resource allocation.
    Injects top past experiences into the prompt for online learning.
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
    prompt += f"Current game state:\n{json.dumps(state, ensure_ascii=False, indent=2)}\n\nAllocate resources now."

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
        return {"allocations": [], "reasoning": "parse error"}
