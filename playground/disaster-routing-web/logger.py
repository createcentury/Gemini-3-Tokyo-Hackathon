"""Online learning data logger."""
import json
import os
from datetime import datetime

LOG_PATH = os.path.join(os.path.dirname(__file__), "learning_log.jsonl")


def log_step(state: dict, action: dict, reward: float, reasoning: str = ""):
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "state":     state,
        "action":    action,
        "reward":    reward,
        "reasoning": reasoning,
    }
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def get_stats() -> dict:
    if not os.path.exists(LOG_PATH):
        return {"steps": 0, "avg_reward": 0.0}
    entries = []
    with open(LOG_PATH) as f:
        for line in f:
            try:
                entries.append(json.loads(line))
            except Exception:
                pass
    if not entries:
        return {"steps": 0, "avg_reward": 0.0}
    rewards = [e["reward"] for e in entries]
    return {
        "steps":      len(entries),
        "avg_reward": round(sum(rewards) / len(rewards), 3),
        "max_reward": round(max(rewards), 3),
    }
