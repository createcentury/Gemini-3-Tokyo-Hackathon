"""Gemini agent with in-context online learning."""
import json
import os
import re

from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
MODEL  = "gemini-3-flash-preview"

SYSTEM_PROMPT = """You are an emergency dispatch AI for Tokyo.
Each turn you receive the current city state and must allocate limited emergency resources
to districts with active incidents.

Goals:
- Prioritize high-severity incidents (collapse > fire > injury/accident > riot)
- Consider district hazard level and population density
- Resolve as many incidents as possible per turn

Respond ONLY with valid JSON:
{
  "allocations": [
    {"district_idx": <int>, "resource": "<ambulance|fire_truck|police>", "count": <int>}
  ],
  "reasoning": "<one sentence explaining your strategy>"
}
"""

_log_path = os.path.join(os.path.dirname(__file__), "learning_log.jsonl")


def _few_shot(n: int = 3) -> str:
    if not os.path.exists(_log_path):
        return ""
    import json as _json
    entries = []
    with open(_log_path) as f:
        for line in f:
            try:
                entries.append(_json.loads(line))
            except Exception:
                pass
    if not entries:
        return ""
    top = sorted(entries, key=lambda e: e["reward"], reverse=True)[:n]
    lines = ["--- Past high-reward examples ---"]
    for i, e in enumerate(top, 1):
        lines.append(f"Example {i} (reward={e['reward']:.1f}): {json.dumps(e['action'])} | {e['reasoning']}")
    lines.append("---\n")
    return "\n".join(lines)


def get_action(state: dict) -> dict:
    prompt = _few_shot() + f"Current state:\n{json.dumps(state, indent=2)}\n\nAllocate resources now."
    response = client.models.generate_content(
        model=MODEL,
        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
        contents=[types.Part.from_text(text=prompt)],
    )
    raw = re.sub(r"^```[a-z]*\n?", "", response.text.strip())
    raw = re.sub(r"\n?```$", "", raw)
    try:
        return json.loads(raw)
    except Exception:
        return {"allocations": [], "reasoning": "parse error"}
