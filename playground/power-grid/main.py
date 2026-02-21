"""Entry point — runs the power grid game with Gemini agent."""
import sys
import pygame
from game import PowerGridGame
from agent import get_action
from logger import log_step, get_stats

MAX_HOURS = 48   # 2 simulated days
AI_MODE   = "--human" not in sys.argv


def main():
    game = PowerGridGame(seed=0)
    print(f"Mode: {'AI (Gemini)' if AI_MODE else 'Human'}")
    print("Press Q to quit, SPACE to step (human mode).\n")

    running = True
    paused  = False

    while running and game.hour < MAX_HOURS:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    running = False
                if event.key == pygame.K_SPACE:
                    paused = not paused

        if AI_MODE and not paused:
            state      = game.get_state()
            screenshot = game.screenshot()
            action     = get_action(state, screenshot)
            thermal_pct = int(action.get("thermal_pct", 50))
            game.reasoning = action.get("reasoning", "")
            state, reward  = game.step(thermal_pct)
            log_step(state, action, reward, game.reasoning)
            print(
                f"Hour {game.hour:3d} | thermal={thermal_pct:3d}% "
                f"| demand={state['demand_mw']:,}MW "
                f"| supply={state['supply_mw']:,}MW "
                f"| reward={reward:+.3f} | {game.reasoning}"
            )
            pygame.time.wait(400)   # slow down so UI is visible

        game.render(state if AI_MODE else None)

    # Final stats
    stats = get_stats()
    print(f"\n=== Simulation Complete ===")
    print(f"Hours simulated : {game.hour}")
    print(f"Total reward    : {game.total_reward:.2f}")
    print(f"Total CO₂       : {game.carbon_total:.1f} t")
    print(f"Log stats       : {stats}")
    pygame.time.wait(3000)
    pygame.quit()


if __name__ == "__main__":
    main()
