"""
Tokyo district hazard data (simplified from Tokyo Metropolitan Government open data)
https://www.bousai.metro.tokyo.lg.jp/taisaku/torikumi/1000902/index.html
"""

# 5x5 grid of Tokyo districts
# hazard_level: 1 (low) - 5 (high) based on earthquake/flood risk
DISTRICTS = [
    # row 0 (north)
    {"name": "練馬区",   "hazard": 2, "pop_density": 3},
    {"name": "板橋区",   "hazard": 2, "pop_density": 3},
    {"name": "北区",     "hazard": 3, "pop_density": 4},
    {"name": "足立区",   "hazard": 5, "pop_density": 5},
    {"name": "葛飾区",   "hazard": 5, "pop_density": 4},
    # row 1
    {"name": "杉並区",   "hazard": 2, "pop_density": 4},
    {"name": "豊島区",   "hazard": 3, "pop_density": 5},
    {"name": "文京区",   "hazard": 2, "pop_density": 4},
    {"name": "荒川区",   "hazard": 4, "pop_density": 5},
    {"name": "江戸川区", "hazard": 5, "pop_density": 4},
    # row 2 (center)
    {"name": "渋谷区",   "hazard": 2, "pop_density": 4},
    {"name": "新宿区",   "hazard": 3, "pop_density": 5},
    {"name": "千代田区", "hazard": 2, "pop_density": 3},
    {"name": "台東区",   "hazard": 4, "pop_density": 5},
    {"name": "墨田区",   "hazard": 4, "pop_density": 5},
    # row 3
    {"name": "目黒区",   "hazard": 2, "pop_density": 3},
    {"name": "品川区",   "hazard": 3, "pop_density": 4},
    {"name": "港区",     "hazard": 2, "pop_density": 3},
    {"name": "江東区",   "hazard": 5, "pop_density": 4},
    {"name": "葛飾区2",  "hazard": 4, "pop_density": 3},
    # row 4 (south)
    {"name": "大田区",   "hazard": 3, "pop_density": 4},
    {"name": "世田谷区", "hazard": 2, "pop_density": 4},
    {"name": "中野区",   "hazard": 2, "pop_density": 5},
    {"name": "中央区",   "hazard": 4, "pop_density": 3},
    {"name": "江東区2",  "hazard": 5, "pop_density": 4},
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
    {"type": "fire",      "severity": 3, "needs": "fire_truck",  "label": "火災"},
    {"type": "injury",    "severity": 2, "needs": "ambulance",   "label": "負傷者"},
    {"type": "collapse",  "severity": 4, "needs": "fire_truck",  "label": "建物倒壊"},
    {"type": "accident",  "severity": 2, "needs": "ambulance",   "label": "交通事故"},
    {"type": "riot",      "severity": 1, "needs": "police",      "label": "群衆混乱"},
]
