"""Power grid balance game environment (Pygame)."""
import random
import io
import pygame
from data import (
    DEMAND_CURVE, SOLAR_CURVE, CAPACITY, PEAK_DEMAND, CARBON, COLORS
)

WIDTH  = 900
HEIGHT = 620
FPS    = 30

BG    = (15,  20,  30)
WHITE = (240, 240, 240)
GRAY  = (110, 110, 130)
YELLOW= (255, 220, 60)


class PowerGridGame:
    def __init__(self, seed: int = 0):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Tokyo Power Grid — Gemini Agent")
        self.clock  = pygame.time.Clock()
        self.font_s = pygame.font.SysFont("Arial", 11)
        self.font_m = pygame.font.SysFont("Arial", 14)
        self.font_l = pygame.font.SysFont("Arial", 18, bold=True)
        self.reset(seed)

    def reset(self, seed: int = 0):
        random.seed(seed)
        self.hour         = 0
        self.total_reward = 0.0
        self.carbon_total = 0.0
        self.history      = []
        self.reasoning    = ""
        self.thermal_pct  = 50
        self._wind_state  = random.uniform(0.3, 0.8)

    def _wind(self) -> float:
        """Slowly varying wind generation (0-1)."""
        self._wind_state += random.uniform(-0.08, 0.08)
        self._wind_state  = max(0.1, min(1.0, self._wind_state))
        return self._wind_state

    def get_state(self) -> dict:
        hour       = self.hour % 24
        demand_mw  = DEMAND_CURVE[hour] * PEAK_DEMAND
        solar_mw   = SOLAR_CURVE[hour]  * CAPACITY["solar"]
        wind_mw    = self._wind_state   * CAPACITY["wind"]
        nuclear_mw = CAPACITY["nuclear"]
        hydro_mw   = CAPACITY["hydro"]
        thermal_mw = self.thermal_pct / 100 * CAPACITY["thermal"]
        supply_mw  = thermal_mw + nuclear_mw + hydro_mw + solar_mw + wind_mw
        balance_mw = supply_mw - demand_mw

        return {
            "hour":           hour,
            "thermal_pct":    self.thermal_pct,
            "demand_mw":      round(demand_mw),
            "supply_mw":      round(supply_mw),
            "balance_mw":     round(balance_mw),
            "sources": {
                "thermal":  round(thermal_mw),
                "nuclear":  round(nuclear_mw),
                "hydro":    round(hydro_mw),
                "solar":    round(solar_mw),
                "wind":     round(wind_mw),
            },
            "next_hour_demand_mw": round(DEMAND_CURVE[(hour + 1) % 24] * PEAK_DEMAND),
        }

    def step(self, thermal_pct: int) -> tuple[dict, float]:
        """Advance one hour with the given thermal_pct. Returns (state, reward)."""
        self.thermal_pct = max(0, min(100, thermal_pct))
        self._wind()
        state      = self.get_state()
        demand_mw  = state["demand_mw"]
        supply_mw  = state["supply_mw"]
        balance_mw = state["balance_mw"]
        thermal_mw = state["sources"]["thermal"]

        imbalance_pct = abs(balance_mw) / demand_mw
        reward = 1.0 - imbalance_pct * 10
        reward -= thermal_mw / CAPACITY["thermal"] * 0.05

        carbon = thermal_mw * CARBON["thermal"] / 1000
        self.carbon_total  += carbon
        self.total_reward  += reward

        self.history.append({**state, "reward": round(reward, 3)})
        self.hour += 1
        return state, reward

    def screenshot(self) -> bytes:
        buf = io.BytesIO()
        pygame.image.save(self.screen, buf, "PNG")
        return buf.getvalue()

    def render(self, state: dict | None = None):
        self.screen.fill(BG)
        if state is None:
            state = self.get_state()
        self._draw_bars(state)
        self._draw_history()
        self._draw_panel(state)
        pygame.display.flip()
        self.clock.tick(FPS)

    def _draw_bars(self, state: dict):
        """Draw stacked supply bar vs demand bar."""
        BAR_X   = 40
        BAR_Y   = 60
        BAR_W   = 80
        BAR_H   = 400
        GAP     = 30

        max_mw  = PEAK_DEMAND * 1.1
        sources = state["sources"]

        # Supply stacked bar
        y_cursor = BAR_Y + BAR_H
        for src in ["thermal", "nuclear", "hydro", "solar", "wind"]:
            mw    = sources[src]
            h     = int(mw / max_mw * BAR_H)
            color = COLORS[src]
            pygame.draw.rect(self.screen, color,
                             (BAR_X, y_cursor - h, BAR_W, h))
            y_cursor -= h

        self.screen.blit(self.font_m.render("Supply", True, WHITE),
                         (BAR_X + 15, BAR_Y + BAR_H + 6))

        # Demand bar
        demand_h = int(state["demand_mw"] / max_mw * BAR_H)
        dx = BAR_X + BAR_W + GAP
        pygame.draw.rect(self.screen, COLORS["demand"],
                         (dx, BAR_Y + BAR_H - demand_h, BAR_W, demand_h))
        self.screen.blit(self.font_m.render("Demand", True, WHITE),
                         (dx + 10, BAR_Y + BAR_H + 6))

        # Balance indicator
        bal   = state["balance_mw"]
        color = COLORS["surplus"] if bal >= 0 else COLORS["deficit"]
        self.screen.blit(self.font_l.render(f"Balance: {bal:+,} MW", True, color),
                         (BAR_X, BAR_Y - 36))

        # Source legend
        lx = BAR_X
        ly = BAR_Y + BAR_H + 30
        for src in ["thermal", "nuclear", "hydro", "solar", "wind"]:
            pygame.draw.rect(self.screen, COLORS[src], (lx, ly, 12, 12))
            t = self.font_s.render(f" {src}: {sources[src]:,}MW", True, WHITE)
            self.screen.blit(t, (lx + 14, ly))
            ly += 17

    def _draw_history(self):
        """Draw mini reward sparkline."""
        if len(self.history) < 2:
            return
        HX, HY, HW, HH = 260, 80, 320, 120
        pygame.draw.rect(self.screen, (30, 30, 45), (HX, HY, HW, HH))
        self.screen.blit(self.font_s.render("Reward History", True, GRAY),
                         (HX + 4, HY + 2))

        rewards = [h["reward"] for h in self.history[-HW:]]
        mn, mx  = -1.0, 1.0
        pts = []
        for i, r in enumerate(rewards):
            px = HX + int(i / max(len(rewards) - 1, 1) * HW)
            py = HY + HH - int((r - mn) / (mx - mn) * (HH - 20)) - 4
            pts.append((px, py))
        if len(pts) >= 2:
            pygame.draw.lines(self.screen, YELLOW, False, pts, 2)

        # demand forecast sparkline
        forecast = [DEMAND_CURVE[(self.hour + j) % 24] for j in range(24)]
        pts2 = []
        for i, v in enumerate(forecast):
            px = HX + int(i / 23 * HW)
            py = HY + HH - int(v * (HH - 20)) - 4
            pts2.append((px, py))
        if len(pts2) >= 2:
            pygame.draw.lines(self.screen, COLORS["demand"], False, pts2, 1)

    def _draw_panel(self, state: dict):
        px, py = 600, 40

        self.screen.blit(self.font_l.render("TOKYO POWER GRID", True, YELLOW), (px, py)); py += 30

        items = [
            (f"Time:        {state['hour']:02d}:00",          WHITE),
            (f"Demand:      {state['demand_mw']:,} MW",       WHITE),
            (f"Supply:      {state['supply_mw']:,} MW",       WHITE),
            (f"Thermal:     {self.thermal_pct}%",             COLORS["thermal"]),
            (f"Total Reward:{self.total_reward:.2f}",         YELLOW),
            (f"Total CO2:   {self.carbon_total:.1f} t",       GRAY),
            (f"Next demand: {state['next_hour_demand_mw']:,} MW", GRAY),
        ]
        for text, color in items:
            self.screen.blit(self.font_m.render(text, True, color), (px, py))
            py += 22

        py += 10
        self.screen.blit(self.font_m.render("Gemini reasoning:", True, GRAY), (px, py)); py += 18
        words = self.reasoning or "-"
        line  = ""
        for w in words.split():
            if len(line) + len(w) > 28:
                self.screen.blit(self.font_s.render(line, True, WHITE), (px, py)); py += 15
                line = w + " "
            else:
                line += w + " "
        if line:
            self.screen.blit(self.font_s.render(line, True, WHITE), (px, py))
