"""Entry point — runs the disaster routing game with Gemini agent."""
import sys
import pygame
from game import DisasterGame
from agent import get_action
from logger import log_step, get_stats

MAX_TURNS = 20
AI_MODE   = "--human" not in sys.argv   # default: AI plays


def main():
    game = DisasterGame(seed=42)
    print(f"Mode: {'AI (Gemini)' if AI_MODE else 'Human'}")
    print("Close window or press Q to quit.\n")

    running = True
    waiting = False   # waiting for keypress before next AI turn

    while running and game.turn < MAX_TURNS:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    running = False
                if event.key == pygame.K_SPACE and waiting:
                    waiting = False

        if not waiting:
            game.render()

            if AI_MODE:
                state          = game.get_state()
                screenshot     = game.screenshot()
                action         = get_action(state, screenshot)
                reward         = game.apply_action(action)
                log_step(state, action, reward, action.get("reasoning", ""))
                print(f"Turn {game.turn:2d} | reward={reward:+.1f} | {action.get('reasoning','')}")
                pygame.time.wait(800)   # brief pause so screen is readable
            else:
                # Human mode: advance turn on SPACE
                waiting = True

        game.render()

    # Final stats
    game.render()
    stats = get_stats()
    print(f"\n=== Game Over ===")
    print(f"Final score : {game.score:.1f}")
    print(f"Resolved    : {game.resolved}")
    print(f"Missed      : {game.missed}")
    print(f"Log stats   : {stats}")
    pygame.time.wait(3000)
    pygame.quit()


if __name__ == "__main__":
    main()
