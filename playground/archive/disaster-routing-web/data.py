"""Tokyo district data with real lat/lng coordinates."""

DISTRICTS = [
    {"name": "Nerima",     "hazard": 2, "pop_density": 3, "lat": 35.7358, "lng": 139.6518},
    {"name": "Itabashi",   "hazard": 2, "pop_density": 3, "lat": 35.7514, "lng": 139.7096},
    {"name": "Kita",       "hazard": 3, "pop_density": 4, "lat": 35.7528, "lng": 139.7336},
    {"name": "Adachi",     "hazard": 5, "pop_density": 5, "lat": 35.7753, "lng": 139.8042},
    {"name": "Katsushika", "hazard": 5, "pop_density": 4, "lat": 35.7340, "lng": 139.8740},
    {"name": "Suginami",   "hazard": 2, "pop_density": 4, "lat": 35.6994, "lng": 139.6366},
    {"name": "Toshima",    "hazard": 3, "pop_density": 5, "lat": 35.7285, "lng": 139.7176},
    {"name": "Bunkyo",     "hazard": 2, "pop_density": 4, "lat": 35.7077, "lng": 139.7524},
    {"name": "Arakawa",    "hazard": 4, "pop_density": 5, "lat": 35.7312, "lng": 139.7836},
    {"name": "Edogawa",    "hazard": 5, "pop_density": 4, "lat": 35.7066, "lng": 139.8688},
    {"name": "Shibuya",    "hazard": 2, "pop_density": 4, "lat": 35.6618, "lng": 139.7038},
    {"name": "Shinjuku",   "hazard": 3, "pop_density": 5, "lat": 35.6938, "lng": 139.7034},
    {"name": "Chiyoda",    "hazard": 2, "pop_density": 3, "lat": 35.6940, "lng": 139.7536},
    {"name": "Taito",      "hazard": 4, "pop_density": 5, "lat": 35.7116, "lng": 139.7810},
    {"name": "Sumida",     "hazard": 4, "pop_density": 5, "lat": 35.7054, "lng": 139.8015},
    {"name": "Meguro",     "hazard": 2, "pop_density": 3, "lat": 35.6342, "lng": 139.6988},
    {"name": "Shinagawa",  "hazard": 3, "pop_density": 4, "lat": 35.6097, "lng": 139.7282},
    {"name": "Minato",     "hazard": 2, "pop_density": 3, "lat": 35.6581, "lng": 139.7514},
    {"name": "Koto",       "hazard": 5, "pop_density": 4, "lat": 35.6726, "lng": 139.8170},
    {"name": "Mizue",      "hazard": 4, "pop_density": 3, "lat": 35.6900, "lng": 139.8780},
    {"name": "Ota",        "hazard": 3, "pop_density": 4, "lat": 35.5613, "lng": 139.7161},
    {"name": "Setagaya",   "hazard": 2, "pop_density": 4, "lat": 35.6464, "lng": 139.6533},
    {"name": "Nakano",     "hazard": 2, "pop_density": 5, "lat": 35.7075, "lng": 139.6654},
    {"name": "Chuo",       "hazard": 4, "pop_density": 3, "lat": 35.6706, "lng": 139.7730},
    {"name": "江東南",     "hazard": 5, "pop_density": 4, "lat": 35.6450, "lng": 139.8300},
]
# rename last entry
DISTRICTS[24]["name"] = "Koto-South"

RESOURCES = {
    "ambulance":  {"count": 5, "color": "#ff3232", "icon": "🚑"},
    "fire_truck": {"count": 4, "color": "#ff8c00", "icon": "🚒"},
    "police":     {"count": 3, "color": "#3232ff", "icon": "🚔"},
}

INCIDENT_TYPES = [
    {"type": "fire",     "severity": 3, "needs": "fire_truck", "label": "Fire",     "icon": "🔥"},
    {"type": "injury",   "severity": 2, "needs": "ambulance",  "label": "Injury",   "icon": "🏥"},
    {"type": "collapse", "severity": 4, "needs": "fire_truck", "label": "Collapse", "icon": "🏚"},
    {"type": "accident", "severity": 2, "needs": "ambulance",  "label": "Accident", "icon": "🚗"},
    {"type": "riot",     "severity": 1, "needs": "police",     "label": "Riot",     "icon": "⚠️"},
]

HAZARD_COLORS = {
    1: "#287a3c",
    2: "#50a050",
    3: "#c8b428",
    4: "#dc7828",
    5: "#c83232",
}
