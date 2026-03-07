from __future__ import annotations

from typing import Optional, Tuple

from .. import settings
from ..agents import GhostUtilityAgent
from ..state.entity_state import EntityState, Position, Velocity
from ..state.game_state import GameState
from ..systems import collision

Direction = Tuple[int, int]


class Ghost:
    """Represents a ghost and encapsulates respawn / frightened logic."""

    def __init__(
        self,
        name: str,
        state: EntityState,
        spawn_tile: Tuple[int, int],
        agent: Optional[GhostUtilityAgent] = None,
    ) -> None:
        self.name = name
        self.state = state
        self.spawn_tile = spawn_tile
        self.agent = agent
        self.respawn_timer: float = 0.0

    def current_tile(self) -> Tuple[int, int]:
        return self.state.position.to_tile(settings.TILE_SIZE)

    def respawn(self) -> None:
        self.state.position = Position(
            self.spawn_tile[0] * settings.TILE_SIZE + settings.TILE_SIZE / 2,
            self.spawn_tile[1] * settings.TILE_SIZE + settings.TILE_SIZE / 2,
        )
        self.state.velocity = Velocity()
        self.state.direction = (0, 0)
        self.state.target_tile = None
        self.state.alive = True
        self.state.frightened = False
        self.respawn_timer = 0.0

    def defeat(self) -> None:
        self.state.alive = False
        self.state.frightened = False
        self.respawn_timer = 3.0

    def update(self, game_state: GameState, delta_time: float) -> None:
        if not self.state.alive:
            self.respawn_timer -= delta_time
            if self.respawn_timer <= 0.0:
                self.respawn()
            return

        frightened = game_state.frightened_timer > 0
        self.state.frightened = frightened

        if frightened:
            self.state.speed = settings.FRIGHTENED_SPEED
        else:
            self.state.speed = settings.GHOST_SPEED

        desired_direction: Direction
        if self.agent is not None:
            desired_direction = self.agent.choose_action(self.state, game_state)
            if frightened:
                # Ensure frightened ghosts do not aggressively chase.
                reverse = (-self.state.direction[0], -self.state.direction[1])
                if desired_direction == reverse:
                    desired_direction = self.state.direction
        else:
            desired_direction = self.state.direction

        if desired_direction != (0, 0):
            collision.set_direction(self.state, desired_direction, game_state)

        collision.update_entity(self.state, delta_time, game_state)
