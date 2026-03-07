"""Entity state helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass
class Position:
    x: float
    y: float

    def to_tile(self, tile_size: int) -> Tuple[int, int]:
        return int(self.x // tile_size), int(self.y // tile_size)


@dataclass
class Velocity:
    dx: float = 0.0
    dy: float = 0.0

    def as_tuple(self) -> Tuple[float, float]:
        return self.dx, self.dy


@dataclass
class EntityState:
    position: Position
    velocity: Velocity
    speed: float
    direction: Tuple[int, int] = (0, 0)
    target_tile: Tuple[int, int] | None = None
    alive: bool = True
    frightened: bool = False


