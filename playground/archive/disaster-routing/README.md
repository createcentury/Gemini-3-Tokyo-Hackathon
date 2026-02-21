# Tokyo Disaster Routing — Gemini Agent

AI agent that allocates emergency resources (ambulances / fire trucks / police) across Tokyo districts in response to real-time disaster incidents.

## Concept

| Layer | Detail |
|-------|--------|
| **Real data** | Tokyo hazard map (earthquake/flood risk per district) |
| **Game** | 5×5 grid of Tokyo wards; incidents spawn weighted by real hazard scores |
| **Gemini agent** | Sees game screenshot + JSON state → decides resource allocation |
| **Online learning** | Every (state, action, reward) tuple saved to `learning_log.jsonl` for fine-tuning |
| **Real-world impact** | Trained agent's routing logic can inform actual emergency dispatch systems |

## Quick Start

```bash
cp .env.example .env
# edit .env and set GEMINI_API_KEY

pip install -r requirements.txt

# AI mode (Gemini plays)
python main.py

# Human mode
python main.py --human
```

## Controls

| Key | Action |
|-----|--------|
| `SPACE` | Advance to next turn |
| `Q` | Quit |

## Learning Log

Each turn is logged to `learning_log.jsonl`:

```jsonc
{
  "timestamp": "2026-02-21T10:00:00",
  "state":     { "turn": 3, "districts": [...], "resources": {...} },
  "action":    { "allocations": [...], "reasoning": "Prioritised Katsushika..." },
  "reward":    4.5,
  "reasoning": "Prioritised Katsushika due to severity-4 collapse incident"
}
```

This format is directly usable for Gemini fine-tuning / RLHF pipelines.

## Architecture

```
game.py   — Pygame environment (state, render, apply_action)
agent.py  — Gemini 2.0 Flash multimodal agent (screenshot + text → action)
logger.py — JSONL logger for online learning data
data.py   — Real Tokyo hazard data + district definitions
main.py   — Game loop
```
