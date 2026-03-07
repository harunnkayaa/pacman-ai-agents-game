"""Game state container and helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from .. import settings
from .entity_state import EntityState, Position, Velocity

Grid = List[List[str]]
Tile = Tuple[int, int]


@dataclass
class GameState:
    """Holds the mutable state of the game world."""

    grid: Grid
    pellets: Set[Tile]
    power_pellets: Set[Tile]
    pacman: EntityState
    ghosts: Dict[str, EntityState]
    scatter_mode: bool = True
    frightened_timer: float = 0.0
    scatter_timer: float = settings.SCATTER_INTERVAL
    chase_timer: float = 0.0
    score: int = 0
    lives: int = settings.MAX_LIVES
    elapsed_time: float = 0.0
    running: bool = True
    result: Optional[str] = None
    winner: Optional[str] = None
    high_scores: List[Tuple[str, int, float]] = field(default_factory=list)
    ghost_combo: int = 0

    pacman_spawn: Tile = (0, 0)
    ghost_spawns: List[Tile] = field(default_factory=list)

    def tile_is_wall(self, tile: Tile) -> bool:
        x, y = tile
        if 0 <= y < len(self.grid) and 0 <= x < len(self.grid[y]):
            return self.grid[y][x] == "#"
        return True

    def remove_pellet(self, tile: Tile) -> None:
        if tile in self.pellets:
            self.pellets.remove(tile)
            self.score += settings.PELLET_SCORE
        elif tile in self.power_pellets:
            self.power_pellets.remove(tile)
            self.score += settings.POWER_PELLET_SCORE
            self.frightened_timer = settings.POWER_UP_DURATION
            self.ghost_combo = 0

    def reset_pacman_position(self) -> None:
        x, y = self.pacman_spawn
        self.pacman.position = Position(
            x * settings.TILE_SIZE + settings.TILE_SIZE / 2,
            y * settings.TILE_SIZE + settings.TILE_SIZE / 2,
        )
        self.pacman.velocity = Velocity()
        self.pacman.direction = (0, 0)

    def reset_ghosts(self) -> None:
        for index, (name, entity) in enumerate(self.ghosts.items()):
            spawn = self.ghost_spawns[min(index, len(self.ghost_spawns) - 1)]
            entity.position = Position(
                spawn[0] * settings.TILE_SIZE + settings.TILE_SIZE / 2,
                spawn[1] * settings.TILE_SIZE + settings.TILE_SIZE / 2,
            )
            entity.velocity = Velocity()
            entity.direction = (0, 0)
            entity.alive = True
            entity.frightened = False

    @property
    def pellets_remaining(self) -> int:
        return len(self.pellets) + len(self.power_pellets)

    @classmethod
    def from_layout(cls, layout: List[str]) -> "GameState":
        grid: Grid = [list(row) for row in layout]
        pellets: Set[Tile] = set()
        power_pellets: Set[Tile] = set()
        pacman_spawn = (1, 1)
        ghost_spawns: List[Tile] = []

        for y, row in enumerate(grid):
            for x, cell in enumerate(row):
                if cell == ".":
                    pellets.add((x, y))
                elif cell == "o":
                    power_pellets.add((x, y))
                elif cell == "P":
                    pacman_spawn = (x, y)
                    grid[y][x] = " "
                elif cell == "G":
                    ghost_spawns.append((x, y))
                    grid[y][x] = " "

        pacman_state = EntityState(
            position=Position(
                pacman_spawn[0] * settings.TILE_SIZE + settings.TILE_SIZE / 2,
                pacman_spawn[1] * settings.TILE_SIZE + settings.TILE_SIZE / 2,
            ),
            velocity=Velocity(),
            speed=settings.PACMAN_SPEED,
        )
        ghost_names = ["blinky", "pinky", "inky", "clyde"]
        ghosts: Dict[str, EntityState] = {}
        for index, name in enumerate(ghost_names):
            spawn = ghost_spawns[min(index, len(ghost_spawns) - 1)] if ghost_spawns else pacman_spawn
            ghosts[name] = EntityState(
                position=Position(
                    spawn[0] * settings.TILE_SIZE + settings.TILE_SIZE / 2,
                    spawn[1] * settings.TILE_SIZE + settings.TILE_SIZE / 2,
                ),
                velocity=Velocity(),
                speed=settings.GHOST_SPEED,
            )

        return cls(
            grid=grid,
            pellets=pellets,
            power_pellets=power_pellets,
            pacman=pacman_state,
            ghosts=ghosts,
            pacman_spawn=pacman_spawn,
            ghost_spawns=ghost_spawns or [pacman_spawn],
        )

    def frighten_ghosts(self) -> None:
        for entity in self.ghosts.values():
            entity.frightened = True

    def calm_ghosts(self) -> None:
        for entity in self.ghosts.values():
            entity.frightened = False


