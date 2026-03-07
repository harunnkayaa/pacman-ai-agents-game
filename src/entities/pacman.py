from __future__ import annotations

from typing import Optional, Tuple

from .. import settings
from ..agents import PacmanUtilityAgent
from ..state.game_state import GameState
from ..state.entity_state import EntityState
from ..systems import collision

Direction = Tuple[int, int]


class Pacman:
    """Handles Pac-Man specific control logic."""

    def __init__(self, state: EntityState, agent: Optional[PacmanUtilityAgent] = None) -> None:
        self.state = state
        self.agent = agent
        self.pending_direction: Direction = (0, 0)

    def set_pending_direction(self, direction: Direction) -> None:
        self.pending_direction = direction

    def update(self, game_state: GameState, delta_time: float) -> None:
        if game_state.frightened_timer > 0:
            self.state.speed = settings.PACMAN_POWER_SPEED
        else:
            self.state.speed = settings.PACMAN_SPEED

        desired_direction: Direction
        if self.agent is not None:
            desired_direction = self.agent.choose_action(self.state, game_state)
        else:
            desired_direction = self.pending_direction

        if desired_direction != (0, 0):
            collision.set_direction(self.state, desired_direction, game_state)

        collision.update_entity(self.state, delta_time, game_state)

    def current_tile(self) -> Tuple[int, int]:
        return self.state.position.to_tile(settings.TILE_SIZE)
