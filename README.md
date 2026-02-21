# Real-World AI Agent Training Environments

> **Gemini 3 Tokyo Hackathon 2026** — Problem Statement 1 & 2

## Concept

Games where **Gemini 3 agents learn from real-world data** — and the trained agent's improved decisions directly help solve real societal problems.

```
Real-world data → Interactive game env → Gemini agent plays
                                              ↓
                               (state, action, reward) logged
                                              ↓
                         Past successes injected back into prompt
                                              ↓
                         Agent improves with each episode (online learning)
                                              ↓
                         Learned policy → applied to real-world decisions
```

This is the environment design that aligns with DeepMind's SIMA 2 and Gemini's
agentic online learning research direction.

---

## Projects

### 🚨 [disaster-routing](./playground/disaster-routing/) — Tokyo Emergency Dispatch

| | |
|---|---|
| **Real data** | Tokyo hazard map (earthquake/flood risk per ward) |
| **Game** | 5×5 grid of Tokyo wards; Gemini allocates ambulances, fire trucks, police |
| **Online learning** | Top past decisions injected as few-shot examples each turn |
| **Real impact** | Routing logic transferable to actual emergency dispatch systems |

```bash
cd playground/disaster-routing
pip install -r requirements.txt
cp .env.example .env  # add GEMINI_API_KEY
python main.py
```

### ⚡ [power-grid](./playground/power-grid/) — Tokyo Power Grid Balancing

| | |
|---|---|
| **Real data** | TEPCO demand curve + real solar/wind profiles for Tokyo |
| **Game** | Gemini controls thermal output % each hour to balance supply/demand |
| **Online learning** | High-reward hour decisions fed back as examples for next episode |
| **Real impact** | Decision policy usable for low-carbon grid dispatch optimisation |

```bash
cd playground/power-grid
pip install -r requirements.txt
cp .env.example .env  # add GEMINI_API_KEY
python main.py
```

---

## Online Learning Loop

Both environments implement the same self-improvement cycle:

```
Episode N:
  Gemini sees: current state + screenshot + top-3 past successes
  Gemini decides: action
  Environment returns: reward
  Log: (state, action, reward) → learning_log.jsonl

Episode N+1:
  Gemini now has better examples → better decisions → higher rewards
```

The `learning_log.jsonl` files are formatted for direct use in
Gemini fine-tuning / RLHF pipelines.

---

## Repository Structure

```
.
├── playground/
│   ├── disaster-routing/     # Tokyo emergency dispatch game
│   │   ├── main.py           # Entry point (python main.py)
│   │   ├── game.py           # Pygame environment
│   │   ├── agent.py          # Gemini 3 agent + in-context learning
│   │   ├── data.py           # Real Tokyo hazard data
│   │   ├── logger.py         # JSONL learning log
│   │   └── learning_log.jsonl
│   ├── power-grid/           # Tokyo power grid balancing game
│   │   ├── main.py
│   │   ├── game.py
│   │   ├── agent.py
│   │   ├── data.py
│   │   ├── logger.py
│   │   └── learning_log.jsonl
│   └── api-examples/         # Gemini API usage examples
└── doc/
    └── gemini-agent-online-learning.md  # Research notes
```

---

## Research Foundation

Based on DeepMind's published research:
- [SIMA 2](https://deepmind.google/blog/sima-2-an-agent-that-plays-reasons-and-learns-with-you-in-virtual-3d-worlds/) — Gemini-powered agent online learning in game environments
- [Gemini 3](https://deepmind.google/models/gemini/) — Agentic capabilities & tool use
- [Genie 3](https://deepmind.google/blog/genie-3-a-new-frontier-for-world-models/) — World model generation
