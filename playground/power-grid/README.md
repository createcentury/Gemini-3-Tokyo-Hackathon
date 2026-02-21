# Tokyo Power Grid — Gemini Agent

AI agent that balances electricity supply and demand for the Tokyo grid hour-by-hour, minimising blackouts and carbon emissions.

## Concept

| Layer | Detail |
|-------|--------|
| **Real data** | TEPCO demand curve + realistic solar/wind profiles for Tokyo |
| **Game** | 24-hour simulation; agent controls thermal output % each hour |
| **Gemini agent** | Sees grid screenshot + JSON state → sets thermal_pct |
| **Online learning** | Every (state, action, reward) saved to `learning_log.jsonl` |
| **Real-world impact** | Policy learned here can guide actual grid operators on low-carbon dispatch |

## Quick Start

```bash
cp .env.example .env
# edit .env and set GEMINI_API_KEY

pip install -r requirements.txt

# AI mode (Gemini plays)
python main.py

# Human mode (SPACE to pause/resume)
python main.py --human
```

## Reward Function

```
reward = 1.0
       - |balance_MW| / demand_MW × 10   # imbalance penalty
       - thermal_MW / thermal_max × 0.05  # carbon penalty
```

A perfect balance with zero thermal = reward ≈ +1.0
A 10 % imbalance = reward ≈ 0.0

## Learning Log

Each hour is logged to `learning_log.jsonl`:

```jsonc
{
  "timestamp": "2026-02-21T11:00:00",
  "state":  { "hour": 8, "demand_mw": 11200, "supply_mw": 11350, ... },
  "action": { "thermal_pct": 62, "reasoning": "Morning ramp-up..." },
  "reward": 0.87
}
```

## Architecture

```
game.py   — Pygame environment (state, step, render)
agent.py  — Gemini 2.0 Flash multimodal agent (screenshot + text → thermal_pct)
logger.py — JSONL logger for online learning data
data.py   — Real TEPCO demand curve + solar/wind/capacity data
main.py   — Simulation loop
```
