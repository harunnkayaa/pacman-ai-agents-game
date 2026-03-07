import random

from src.agents import GhostUtilityAgent, PacmanUtilityAgent
from src.state.game_state import GameState
from src import settings


def _make_simple_state() -> GameState:
    layout = [
        "#####",
        "#P..#",
        "#...#",
        "#..G#",
        "#####",
    ]
    return GameState.from_layout(layout)


def test_pacman_agent_prefers_pellet_direction() -> None:
    game_state = _make_simple_state()
    agent = PacmanUtilityAgent(rng=random.Random(1))
    action = agent.choose_action(game_state.pacman, game_state)
    start_tile = game_state.pacman.position.to_tile(settings.TILE_SIZE)
    next_tile = (start_tile[0] + action[0], start_tile[1] + action[1])
    assert next_tile in game_state.pellets


def test_ghost_agent_chases_pacman_in_chase_mode() -> None:
    game_state = _make_simple_state()
    ghost_state = next(iter(game_state.ghosts.values()))
    tile = settings.TILE_SIZE
    ghost_state.position.x = 3 * tile + tile / 2
    ghost_state.position.y = 3 * tile + tile / 2
    game_state.pacman.position.x = 2 * tile + tile / 2
    game_state.pacman.position.y = 1 * tile + tile / 2
    game_state.scatter_mode = False

    agent = GhostUtilityAgent("blinky", rng=random.Random(2))
    direction = agent.choose_action(ghost_state, game_state)
    assert direction in {(-1, 0), (0, -1)}


def test_ghost_agent_avoids_pacman_when_frightened() -> None:
    game_state = _make_simple_state()
    ghost_state = next(iter(game_state.ghosts.values()))
    tile = settings.TILE_SIZE
    ghost_state.position.x = 2 * tile + tile / 2
    ghost_state.position.y = 2 * tile + tile / 2
    game_state.pacman.position.x = 2 * tile + tile / 2
    game_state.pacman.position.y = 1 * tile + tile / 2
    game_state.frightened_timer = 5.0

    agent = GhostUtilityAgent("blinky", rng=random.Random(3))
    direction = agent.choose_action(ghost_state, game_state)
    assert direction != (0, -1)
