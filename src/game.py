from __future__ import annotations

import sys
from typing import Dict, Literal

import pygame

from . import assets, settings
from .agents import GhostUtilityAgent, PacmanUtilityAgent
from .entities import Ghost, Pacman
from .levels.loader import load_layout
from .state.game_state import GameState
from .systems.audio import AudioSystem
from .systems.input import process_events
from .systems.rendering import Renderer

Mode = Literal["human", "computer"]


def main() -> None:
    pygame.init()
    pygame.font.init()
    pygame.display.set_caption("Pac-Man AI")

    screen = pygame.display.set_mode((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT))
    images = assets.load_images()
    renderer = Renderer(screen, images)

    clock = pygame.time.Clock()

    running = True
    while running:
        mode = _mode_selection_loop(renderer)
        if mode is None:
            break
        running = _run_session(mode, renderer, clock, images)

    pygame.quit()
    sys.exit(0)


def _mode_selection_loop(renderer: Renderer) -> Mode | None:
    selected = "Human"
    while True:
        renderer.draw_menu(selected)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None
                if event.key == pygame.K_h:
                    return "human"
                if event.key == pygame.K_c:
                    return "computer"
                if event.key == pygame.K_TAB:
                    selected = "Computer" if selected == "Human" else "Human"
    return None


def _run_session(mode: Mode, renderer: Renderer, clock: pygame.time.Clock, images: Dict[str, pygame.Surface]) -> bool:
    layout = load_layout("classic")
    game_state = GameState.from_layout(layout)
    audio = AudioSystem()

    human_control = mode == "human"
    mode_label = "Human vs Computer" if human_control else "Computer vs Computer"

    pacman_agent = None if human_control else PacmanUtilityAgent()
    pacman = Pacman(game_state.pacman, agent=pacman_agent)

    ghost_wrappers: Dict[str, Ghost] = {}
    for index, (name, entity) in enumerate(game_state.ghosts.items()):
        spawn = game_state.ghost_spawns[min(index, len(game_state.ghost_spawns) - 1)]
        agent = GhostUtilityAgent(name)
        ghost_wrappers[name] = Ghost(name, entity, spawn, agent=agent)

    paused = False
    result_recorded = False

    while True:
        delta_time = clock.tick(settings.FPS) / 1000.0
        allow_input = human_control and game_state.running and not paused
        quit_requested, toggle_pause, confirm = process_events(pacman if human_control else None, allow_input)

        if quit_requested:
            return False

        if toggle_pause and game_state.running:
            paused = not paused

        if confirm and not game_state.running:
            return True

        if paused:
            renderer.draw_game(game_state, f"{mode_label} (Paused)")
            continue

        if game_state.running:
            _update_game(game_state, pacman, ghost_wrappers, delta_time, audio)
        else:
            if not result_recorded:
                controller = "Human" if human_control else "Computer"
                game_state.high_scores.append((controller, game_state.score, game_state.elapsed_time))
                game_state.high_scores.sort(key=lambda item: (-item[1], item[2]))
                game_state.high_scores = game_state.high_scores[:5]
                result_recorded = True

        renderer.draw_game(game_state, mode_label)

        if not game_state.running and result_recorded and confirm:
            return True


def _update_game(
    game_state: GameState,
    pacman: Pacman,
    ghosts: Dict[str, Ghost],
    delta_time: float,
    audio: AudioSystem,
) -> None:
    was_frightened = game_state.frightened_timer > 0

    pacman.update(game_state, delta_time)

    pacman_tile = pacman.current_tile()
    ate_pellet = pacman_tile in game_state.pellets
    ate_power = pacman_tile in game_state.power_pellets

    if ate_pellet or ate_power:
        game_state.remove_pellet(pacman_tile)
        if ate_power:
            audio.play("power")
            game_state.frighten_ghosts()
        else:
            audio.play("pellet")

    if game_state.pellets_remaining == 0:
        game_state.running = False
        game_state.result = "All pellets cleared!"
        game_state.winner = "Pac-Man"

    for ghost in ghosts.values():
        ghost.update(game_state, delta_time)

    if game_state.frightened_timer > 0:
        game_state.frightened_timer = max(0.0, game_state.frightened_timer - delta_time)
        if game_state.frightened_timer == 0:
            game_state.calm_ghosts()
            game_state.ghost_combo = 0
    elif was_frightened:
        game_state.calm_ghosts()
        game_state.ghost_combo = 0

    if game_state.frightened_timer <= 0:
        if game_state.scatter_mode:
            game_state.scatter_timer -= delta_time
            if game_state.scatter_timer <= 0:
                game_state.scatter_mode = False
                game_state.chase_timer = settings.CHASE_INTERVAL
        else:
            game_state.chase_timer -= delta_time
            if game_state.chase_timer <= 0:
                game_state.scatter_mode = True
                game_state.scatter_timer = settings.SCATTER_INTERVAL

    _handle_collisions(game_state, pacman, ghosts, audio)

    game_state.elapsed_time += delta_time


def _handle_collisions(
    game_state: GameState,
    pacman: Pacman,
    ghosts: Dict[str, Ghost],
    audio: AudioSystem,
) -> None:
    pacman_tile = pacman.current_tile()

    for ghost in ghosts.values():
        ghost_tile = ghost.current_tile()
        if not ghost.state.alive:
            continue
        if ghost_tile != pacman_tile:
            continue

        if game_state.frightened_timer > 0:
            ghost.defeat()
            audio.play("ghost")
            game_state.ghost_combo += 1
            reward = settings.GHOST_EATEN_SCORE * (2 ** (game_state.ghost_combo - 1))
            game_state.score += reward
        else:
            audio.play("loss")
            game_state.lives -= 1
            game_state.reset_pacman_position()
            game_state.reset_ghosts()
            for wrapper in ghosts.values():
                wrapper.respawn_timer = 0.0
                wrapper.state.alive = True
                wrapper.state.frightened = False
            if game_state.lives <= 0:
                game_state.running = False
                game_state.result = "Pac-Man lost all lives."
                game_state.winner = "Ghosts"
            break

    if not game_state.running and game_state.winner is None:
        game_state.winner = "Ghosts" if game_state.lives <= 0 else "Pac-Man"


if __name__ == "__main__":
    main()
