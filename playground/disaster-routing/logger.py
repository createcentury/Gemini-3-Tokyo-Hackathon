"""Online learning data logger — saves (state, action, reward) for fine-tuning."""
import json
import os
from datetime import datetime


LOG_PATH = "learning_log.jsonl"


def log_step(state: dict, action: dict, reward: float, reasoning: str = ""):
    """Append one (state, action, reward) tuple to the JSONL log."""
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "state":     state,
        "action":    action,
        "reward":    reward,
        "reasoning": reasoning,
    }
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load_log() -> list[dict]:
    if not os.path.exists(LOG_PATH):
        return []
    with open(LOG_PATH, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def get_stats() -> dict:
    entries = load_log()
    if not entries:
        return {"episodes": 0, "avg_reward": 0.0}
    rewards = [e["reward"] for e in entries]
    return {
        "episodes":   len(entries),
        "avg_reward": round(sum(rewards) / len(rewards), 3),
        "max_reward": round(max(rewards), 3),
        "min_reward": round(min(rewards), 3),
    }
