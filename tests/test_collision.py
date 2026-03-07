from src.state.game_state import GameState
from src.systems import collision
from src import settings


def test_pacman_cannot_walk_through_wall() -> None:
    layout = [
        "#####",
        "#P#.#",
        "#####",
    ]
    game_state = GameState.from_layout(layout)
    pacman = game_state.pacman

    allowed = collision.set_direction(pacman, (1, 0), game_state)
    assert not allowed
    assert pacman.direction == (0, 0)


def test_wrap_tile_horizontal() -> None:
    tile = collision.wrap_tile((settings.MAZE_COLUMNS, 0))
    assert tile == (0, 0)
