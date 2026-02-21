"""Disaster routing game logic (no Pygame — state only, for web backend)."""
import random
import copy
from data import DISTRICTS, RESOURCES, INCIDENT_TYPES


class DisasterGame:
    def __init__(self, seed: int = 42):
        self.reset(seed)

    def reset(self, seed: int = 42):
        random.seed(seed)
        self.turn      = 0
        self.score     = 0.0
        self.resolved  = 0
        self.missed    = 0
        self.reasoning = ""
        self.districts = copy.deepcopy(DISTRICTS)
        for d in self.districts:
            d["incidents"] = []
            d["resources"] = {}
        self.resources_available = {k: v["count"] for k, v in RESOURCES.items()}
        self._spawn_incidents()

    def _spawn_incidents(self):
        for d in self.districts:
            if random.random() < d["hazard"] * 0.10:
                inc = random.choice(INCIDENT_TYPES).copy()
                inc["turns_remaining"] = 3
                inc["id"] = f"{d['name']}-{self.turn}-{random.randint(0,9999)}"
                d["incidents"].append(inc)

    def get_state(self) -> dict:
        return {
            "turn":      self.turn,
            "score":     round(self.score, 1),
            "resolved":  self.resolved,
            "missed":    self.missed,
            "resources": self.resources_available,
            "districts": [
                {
                    "idx":       i,
                    "name":      d["name"],
                    "hazard":    d["hazard"],
                    "lat":       d["lat"],
                    "lng":       d["lng"],
                    "pop":       d["pop_density"],
                    "incidents": list(d["incidents"]),
                }
                for i, d in enumerate(self.districts)
            ],
        }

    def apply_action(self, action: dict) -> tuple[float, list[dict]]:
        """
        Apply agent allocations, resolve incidents.
        Returns (reward, dispatch_events) where dispatch_events is a list of
        {from_lat, from_lng, to_lat, to_lng, resource, district_name} for animation.
        """
        allocations    = action.get("allocations", [])
        self.reasoning = action.get("reasoning", "")
        dispatch_events = []

        # HQ lat/lng (approximate center of Tokyo)
        HQ_LAT, HQ_LNG = 35.6895, 139.6917

        for alloc in allocations:
            idx      = alloc.get("district_idx", -1)
            resource = alloc.get("resource", "")
            count    = int(alloc.get("count", 0))
            if idx < 0 or idx >= len(self.districts):
                continue
            if resource not in self.resources_available:
                continue
            count = min(count, self.resources_available[resource])
            if count <= 0:
                continue
            self.resources_available[resource] -= count
            d = self.districts[idx]
            d["resources"][resource] = d["resources"].get(resource, 0) + count
            dispatch_events.append({
                "from_lat":      HQ_LAT,
                "from_lng":      HQ_LNG,
                "to_lat":        d["lat"],
                "to_lng":        d["lng"],
                "resource":      resource,
                "district_name": d["name"],
                "count":         count,
            })

        reward = 0.0
        resolved_incidents = []
        for d in self.districts:
            still_active = []
            for inc in d["incidents"]:
                need  = inc["needs"]
                avail = d["resources"].get(need, 0)
                if avail > 0:
                    d["resources"][need] -= 1
                    reward += inc["severity"]
                    self.resolved += 1
                    resolved_incidents.append({
                        "lat":   d["lat"],
                        "lng":   d["lng"],
                        "label": inc["label"],
                        "icon":  inc["icon"],
                    })
                else:
                    inc["turns_remaining"] -= 1
                    if inc["turns_remaining"] > 0:
                        still_active.append(inc)
                    else:
                        self.missed += 1
                        reward -= inc["severity"] * 0.5
            d["incidents"] = still_active

        for d in self.districts:
            d["resources"] = {}
        self.resources_available = {k: v["count"] for k, v in RESOURCES.items()}

        self.score += reward
        self.turn  += 1
        self._spawn_incidents()

        return reward, dispatch_events, resolved_incidents
