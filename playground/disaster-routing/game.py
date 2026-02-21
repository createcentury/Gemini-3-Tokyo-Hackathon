"""Disaster routing game environment (Pygame)."""
import random
import copy
import io
import pygame
from data import DISTRICTS, GRID_SIZE, RESOURCES, INCIDENT_TYPES

# Layout
CELL   = 120
MARGIN = 4
PANEL  = 280
WIDTH  = GRID_SIZE * CELL + PANEL
HEIGHT = GRID_SIZE * CELL + 80
FPS    = 30

# Colors
BG        = (20,  20,  30)
GRID_LINE = (50,  50,  70)
WHITE     = (240, 240, 240)
YELLOW    = (255, 220, 60)
RED       = (220, 60,  60)
GREEN     = (60,  200, 100)
ORANGE    = (255, 140, 0)
GRAY      = (120, 120, 140)

HAZARD_COLORS = {
    1: (40,  120, 60),
    2: (80,  160, 80),
    3: (200, 180, 40),
    4: (220, 120, 40),
    5: (200, 50,  50),
}


class DisasterGame:
    def __init__(self, seed: int = 42):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Tokyo Disaster Routing — Gemini Agent")
        self.clock  = pygame.time.Clock()
        self.font_s = pygame.font.SysFont("notosanscjkjp", 11)
        self.font_m = pygame.font.SysFont("notosanscjkjp", 14)
        self.font_l = pygame.font.SysFont("notosanscjkjp", 18, bold=True)
        self.reset(seed)

    def reset(self, seed: int = 42):
        random.seed(seed)
        self.turn      = 0
        self.score     = 0
        self.resolved  = 0
        self.missed    = 0
        self.districts = copy.deepcopy(DISTRICTS)
        for d in self.districts:
            d["incidents"] = []
            d["resources"] = {}
        self.resources_available = {k: v["count"] for k, v in RESOURCES.items()}
        self.message   = "Game started. Allocate resources!"
        self.reasoning = ""
        self._spawn_incidents()

    def _spawn_incidents(self):
        """Randomly spawn incidents weighted by hazard level."""
        for i, d in enumerate(self.districts):
            if random.random() < d["hazard"] * 0.08:
                incident = random.choice(INCIDENT_TYPES).copy()
                incident["turns_remaining"] = 3
                d["incidents"].append(incident)

    def get_state(self) -> dict:
        return {
            "turn":      self.turn,
            "score":     self.score,
            "resources": self.resources_available,
            "districts": [
                {
                    "idx":       i,
                    "name":      d["name"],
                    "hazard":    d["hazard"],
                    "pop":       d["pop_density"],
                    "incidents": [
                        {"type": inc["type"], "label": inc["label"],
                         "severity": inc["severity"], "needs": inc["needs"],
                         "turns_remaining": inc["turns_remaining"]}
                        for inc in d["incidents"]
                    ],
                }
                for i, d in enumerate(self.districts)
            ],
        }

    def apply_action(self, action: dict) -> float:
        """Apply agent allocations, resolve incidents, return reward."""
        allocations = action.get("allocations", [])
        self.reasoning = action.get("reasoning", "")

        # Apply allocations
        for alloc in allocations:
            idx      = alloc.get("district_idx", -1)
            resource = alloc.get("resource", "")
            count    = int(alloc.get("count", 0))
            if idx < 0 or idx >= len(self.districts):
                continue
            if resource not in self.resources_available:
                continue
            count = min(count, self.resources_available[resource])
            self.resources_available[resource] -= count
            d = self.districts[idx]
            d["resources"][resource] = d["resources"].get(resource, 0) + count

        # Resolve incidents
        reward = 0.0
        for d in self.districts:
            resolved = []
            for inc in d["incidents"]:
                need  = inc["needs"]
                avail = d["resources"].get(need, 0)
                if avail > 0:
                    d["resources"][need] -= 1
                    reward += inc["severity"]
                    self.resolved += 1
                    resolved.append(inc)
                else:
                    inc["turns_remaining"] -= 1
            for inc in resolved:
                d["incidents"].remove(inc)
            # Expire incidents that ran out of time
            expired = [i for i in d["incidents"] if i["turns_remaining"] <= 0]
            for inc in expired:
                d["incidents"].remove(inc)
                self.missed += 1
                reward -= inc["severity"] * 0.5

        # Return resources
        for d in self.districts:
            for res, cnt in d["resources"].items():
                self.resources_available[res] = \
                    min(RESOURCES[res]["count"],
                        self.resources_available.get(res, 0) + cnt)
            d["resources"] = {}

        self.score += reward
        self.turn  += 1
        self._spawn_incidents()
        self.message = f"Turn {self.turn}: {self.reasoning}"
        return reward

    def screenshot(self) -> bytes:
        """Return current frame as PNG bytes."""
        buf = io.BytesIO()
        pygame.image.save(self.screen, buf, "PNG")
        return buf.getvalue()

    def render(self):
        self.screen.fill(BG)
        self._draw_grid()
        self._draw_panel()
        self._draw_message()
        pygame.display.flip()
        self.clock.tick(FPS)

    def _draw_grid(self):
        for i, d in enumerate(self.districts):
            row, col = divmod(i, GRID_SIZE)
            x = col * CELL + MARGIN
            y = row * CELL + MARGIN
            w = CELL - MARGIN * 2
            h = CELL - MARGIN * 2

            # Cell background by hazard
            color = HAZARD_COLORS[d["hazard"]]
            pygame.draw.rect(self.screen, color, (x, y, w, h), border_radius=6)

            # District name
            name_surf = self.font_s.render(d["name"], True, WHITE)
            self.screen.blit(name_surf, (x + 4, y + 4))

            # Hazard badge
            haz_surf = self.font_s.render(f"危険度:{d['hazard']}", True, WHITE)
            self.screen.blit(haz_surf, (x + 4, y + 18))

            # Incidents
            for j, inc in enumerate(d["incidents"]):
                color_inc = RED if inc["severity"] >= 3 else ORANGE
                inc_surf  = self.font_s.render(
                    f"⚠ {inc['label']} ({inc['turns_remaining']}T)", True, color_inc
                )
                self.screen.blit(inc_surf, (x + 4, y + 36 + j * 16))

    def _draw_panel(self):
        px = GRID_SIZE * CELL + 10
        py = 10

        title = self.font_l.render("TOKYO 防災指令", True, YELLOW)
        self.screen.blit(title, (px, py)); py += 30

        # Score
        score_surf = self.font_m.render(f"スコア:  {self.score:.1f}", True, WHITE)
        self.screen.blit(score_surf, (px, py)); py += 22
        res_surf = self.font_m.render(f"解決済み: {self.resolved}", True, GREEN)
        self.screen.blit(res_surf, (px, py)); py += 22
        mis_surf = self.font_m.render(f"未対応:  {self.missed}", True, RED)
        self.screen.blit(mis_surf, (px, py)); py += 22
        turn_surf = self.font_m.render(f"ターン:  {self.turn}", True, GRAY)
        self.screen.blit(turn_surf, (px, py)); py += 30

        # Resources
        self.screen.blit(self.font_l.render("利用可能リソース", True, YELLOW), (px, py)); py += 24
        for res_name, info in RESOURCES.items():
            count = self.resources_available.get(res_name, 0)
            surf  = self.font_m.render(
                f"{info['emoji']} {res_name}: {count}/{info['count']}", True, info["color"]
            )
            self.screen.blit(surf, (px, py)); py += 20

        # Legend
        py += 16
        self.screen.blit(self.font_m.render("危険度カラー凡例", True, GRAY), (px, py)); py += 18
        for level, color in HAZARD_COLORS.items():
            pygame.draw.rect(self.screen, color, (px, py, 14, 14), border_radius=3)
            surf = self.font_s.render(f" Lv.{level}", True, WHITE)
            self.screen.blit(surf, (px + 16, py)); py += 18

    def _draw_message(self):
        y = GRID_SIZE * CELL + 10
        # word-wrap naively
        words = self.message[:120]
        surf  = self.font_m.render(words, True, WHITE)
        self.screen.blit(surf, (10, y))
