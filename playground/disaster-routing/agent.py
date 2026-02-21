"""Gemini agent for disaster routing decisions."""
import base64
import json
import os
import re

from google import genai
from google.genai import types
from dotenv import load_dotenv

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


def screenshot_to_b64(surface_bytes: bytes) -> str:
    return base64.b64encode(surface_bytes).decode()


def get_action(state: dict, screenshot_bytes: bytes | None = None) -> dict:
    """
    Ask Gemini to decide resource allocation.
    state: serializable game state dict
    screenshot_bytes: PNG bytes of the current game screen (optional)
    """
    user_content = []

    if screenshot_bytes:
        user_content.append(
            types.Part.from_bytes(data=screenshot_bytes, mime_type="image/png")
        )

    user_content.append(
        types.Part.from_text(text=f"Current game state:\n{json.dumps(state, ensure_ascii=False, indent=2)}\n\nAllocate resources now.")
    )

    response = client.models.generate_content(
        model=MODEL,
        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
        contents=user_content,
    )

    raw = response.text.strip()
    # strip markdown code fences if present
    raw = re.sub(r"^```[a-z]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"allocations": [], "reasoning": "parse error"}
