"""Collision detection and tile-based movement helpers."""

from __future__ import annotations

from typing import Tuple

from .. import settings
from ..state.entity_state import EntityState, Position
from ..state.game_state import GameState

Direction = Tuple[int, int]


def wrap_tile(tile: Tuple[int, int]) -> Tuple[int, int]:
    x, y = tile
    columns = settings.MAZE_COLUMNS
    rows = settings.MAZE_ROWS
    return x % columns, y % rows


def can_move(tile: Tuple[int, int], game_state: GameState) -> bool:
    wrapped_tile = wrap_tile(tile)
    return not game_state.tile_is_wall(wrapped_tile)


def set_direction(entity: EntityState, direction: Direction, game_state: GameState) -> bool:
    """Attempt to update the entity's travel direction."""
    if direction == (0, 0):
        entity.direction = (0, 0)
        entity.target_tile = None
        return True

    current_tile = entity.position.to_tile(settings.TILE_SIZE)
    next_tile = wrap_tile((current_tile[0] + direction[0], current_tile[1] + direction[1]))
    if can_move(next_tile, game_state):
        entity.direction = direction
        entity.target_tile = next_tile
        return True
    return False


def update_entity(entity: EntityState, delta_time: float, game_state: GameState) -> None:
    """Advance the entity towards its target tile."""
    if entity.direction == (0, 0):
        return

    if entity.target_tile is None:
        current_tile = entity.position.to_tile(settings.TILE_SIZE)
        entity.target_tile = wrap_tile(
            (current_tile[0] + entity.direction[0], current_tile[1] + entity.direction[1])
        )
        if not can_move(entity.target_tile, game_state):
            entity.direction = (0, 0)
            entity.target_tile = None
            return

    target_x = entity.target_tile[0] * settings.TILE_SIZE + settings.TILE_SIZE / 2
    target_y = entity.target_tile[1] * settings.TILE_SIZE + settings.TILE_SIZE / 2

    dx = entity.direction[0] * entity.speed
    dy = entity.direction[1] * entity.speed

    new_x = entity.position.x + dx * delta_time
    new_y = entity.position.y + dy * delta_time

    reached_x = (
        (dx >= 0 and new_x >= target_x) or (dx <= 0 and new_x <= target_x) if entity.direction[0] != 0 else True
    )
    reached_y = (
        (dy >= 0 and new_y >= target_y) or (dy <= 0 and new_y <= target_y) if entity.direction[1] != 0 else True
    )

    if reached_x and reached_y:
        entity.position = Position(target_x, target_y)
        current_tile = entity.target_tile
        next_tile = wrap_tile((current_tile[0] + entity.direction[0], current_tile[1] + entity.direction[1]))
        if can_move(next_tile, game_state):
            entity.target_tile = next_tile
        else:
            entity.direction = (0, 0)
            entity.target_tile = None
    else:
        entity.position = Position(new_x, new_y)

    # Tunnel wrapping for horizontal movement
    if entity.direction[0] != 0:
        max_x = settings.MAZE_COLUMNS * settings.TILE_SIZE
        if new_x < 0:
            entity.position = Position(max_x - settings.TILE_SIZE / 2, entity.position.y)
        elif new_x >= max_x:
            entity.position = Position(settings.TILE_SIZE / 2, entity.position.y)


