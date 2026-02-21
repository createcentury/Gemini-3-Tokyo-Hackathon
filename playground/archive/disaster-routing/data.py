"""
Tokyo district hazard data (simplified from Tokyo Metropolitan Government open data)
https://www.bousai.metro.tokyo.lg.jp/taisaku/torikumi/1000902/index.html
"""

# 5x5 grid of Tokyo districts
# hazard_level: 1 (low) - 5 (high) based on earthquake/flood risk
DISTRICTS = [
    # row 0 (north)
    {"name": "Nerima",    "hazard": 2, "pop_density": 3},
    {"name": "Itabashi",  "hazard": 2, "pop_density": 3},
    {"name": "Kita",      "hazard": 3, "pop_density": 4},
    {"name": "Adachi",    "hazard": 5, "pop_density": 5},
    {"name": "Katsushika","hazard": 5, "pop_density": 4},
    # row 1
    {"name": "Suginami",  "hazard": 2, "pop_density": 4},
    {"name": "Toshima",   "hazard": 3, "pop_density": 5},
    {"name": "Bunkyo",    "hazard": 2, "pop_density": 4},
    {"name": "Arakawa",   "hazard": 4, "pop_density": 5},
    {"name": "Edogawa",   "hazard": 5, "pop_density": 4},
    # row 2 (center)
    {"name": "Shibuya",   "hazard": 2, "pop_density": 4},
    {"name": "Shinjuku",  "hazard": 3, "pop_density": 5},
    {"name": "Chiyoda",   "hazard": 2, "pop_density": 3},
    {"name": "Taito",     "hazard": 4, "pop_density": 5},
    {"name": "Sumida",    "hazard": 4, "pop_density": 5},
    # row 3
    {"name": "Meguro",    "hazard": 2, "pop_density": 3},
    {"name": "Shinagawa", "hazard": 3, "pop_density": 4},
    {"name": "Minato",    "hazard": 2, "pop_density": 3},
    {"name": "Koto",      "hazard": 5, "pop_density": 4},
    {"name": "Katsushika2","hazard": 4, "pop_density": 3},
    # row 4 (south)
    {"name": "Ota",       "hazard": 3, "pop_density": 4},
    {"name": "Setagaya",  "hazard": 2, "pop_density": 4},
    {"name": "Nakano",    "hazard": 2, "pop_density": 5},
    {"name": "Chuo",      "hazard": 4, "pop_density": 3},
    {"name": "Koto2",     "hazard": 5, "pop_density": 4},
]

GRID_SIZE = 5

# Resource types
RESOURCES = {
    "ambulance":   {"count": 5, "color": (255, 50,  50),  "emoji": "🚑"},
    "fire_truck":  {"count": 4, "color": (255, 140, 0),   "emoji": "🚒"},
    "police":      {"count": 3, "color": (50,  50,  255), "emoji": "🚔"},
}

# Incident types with severity weights
INCIDENT_TYPES = [
    {"type": "fire",      "severity": 3, "needs": "fire_truck",  "label": "Fire"},
    {"type": "injury",    "severity": 2, "needs": "ambulance",   "label": "Injury"},
    {"type": "collapse",  "severity": 4, "needs": "fire_truck",  "label": "Collapse"},
    {"type": "accident",  "severity": 2, "needs": "ambulance",   "label": "Accident"},
    {"type": "riot",      "severity": 1, "needs": "police",      "label": "Riot"},
]
