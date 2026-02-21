"""
Japan power demand/supply data (simplified from TEPCO open data)
https://www.tepco.co.jp/forecast/html/download-j.html
"""

# Typical weekday demand curve (relative, 0.0-1.0) for Tokyo area
# Index = hour of day (0-23)
DEMAND_CURVE = [
    0.58, 0.54, 0.52, 0.51, 0.52, 0.56,  # 0-5  (night/early morning)
    0.64, 0.74, 0.83, 0.88, 0.91, 0.93,  # 6-11 (morning ramp-up)
    0.94, 0.93, 0.92, 0.91, 0.93, 0.96,  # 12-17 (daytime / evening peak)
    0.99, 1.00, 0.95, 0.88, 0.78, 0.66,  # 18-23 (evening / night)
]

# Max capacity in MW (simplified for simulation)
CAPACITY = {
    "thermal":  8000,   # controllable
    "nuclear":  3000,   # fixed baseload
    "hydro":    1000,   # fixed baseload
    "solar":    4000,   # follows sun curve
    "wind":     2000,   # variable
}

# Total max demand (MW)
PEAK_DEMAND = 14000

# Solar generation curve (relative, 0.0-1.0)
SOLAR_CURVE = [
    0.00, 0.00, 0.00, 0.00, 0.00, 0.02,  # 0-5
    0.10, 0.25, 0.45, 0.65, 0.80, 0.90,  # 6-11
    0.95, 0.90, 0.80, 0.65, 0.40, 0.15,  # 12-17
    0.03, 0.00, 0.00, 0.00, 0.00, 0.00,  # 18-23
]

# Carbon intensity (kg-CO2/MWh)
CARBON = {
    "thermal": 450,
    "nuclear": 12,
    "hydro":   11,
    "solar":   0,
    "wind":    0,
}

# Color palette for UI
COLORS = {
    "thermal": (220, 80,  40),
    "nuclear": (180, 60, 220),
    "hydro":   (40,  120, 220),
    "solar":   (255, 210, 40),
    "wind":    (80,  200, 120),
    "demand":  (200, 200, 200),
    "surplus": (80,  200, 80),
    "deficit": (220, 60,  60),
}
