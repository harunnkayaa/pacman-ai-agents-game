from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .. import settings
from ..state.entity_state import EntityState
from ..state.game_state import GameState, Tile
from ..systems import collision

Direction = Tuple[int, int]
DIRECTIONS: Tuple[Direction, ...] = ((1, 0), (-1, 0), (0, 1), (0, -1))


@dataclass
class ActionEvaluation:
    direction: Direction
    utility: float
    features: Dict[str, float]


def _shortest_distance(
    start: Tile,
    targets: Iterable[Tile],
    game_state: GameState,
    max_depth: int = 100,
) -> Optional[int]:
    """Return tile distance using BFS, or None if unreachable."""
    target_set = set(targets)
    if not target_set:
        return None

    visited = {start}
    queue: deque[Tuple[Tile, int]] = deque([(start, 0)])

    while queue:
        tile, dist = queue.popleft()
        if tile in target_set:
            return dist
        if dist >= max_depth:
            continue
        for direction in DIRECTIONS:
            next_tile = collision.wrap_tile((tile[0] + direction[0], tile[1] + direction[1]))
            if next_tile in visited or game_state.tile_is_wall(next_tile):
                continue
            visited.add(next_tile)
            queue.append((next_tile, dist + 1))
    return None


def _distance_to_entities(
    start: Tile,
    entities: Sequence[EntityState],
    game_state: GameState,
    max_depth: int = 100,
) -> Optional[int]:
    targets = [entity.position.to_tile(settings.TILE_SIZE) for entity in entities if entity.alive]
    return _shortest_distance(start, targets, game_state, max_depth=max_depth)


class UtilityAgent:
    """Base class for utility-based decision making."""

    def __init__(self, rng: Optional[random.Random] = None) -> None:
        self.random = rng or random.Random()

    def legal_actions(self, entity: EntityState, game_state: GameState) -> List[Direction]:
        current_tile = entity.position.to_tile(settings.TILE_SIZE)
        actions: List[Direction] = []
        for direction in DIRECTIONS:
            next_tile = collision.wrap_tile((current_tile[0] + direction[0], current_tile[1] + direction[1]))
            if not game_state.tile_is_wall(next_tile):
                actions.append(direction)
        return actions

    def evaluate(self, entity: EntityState, game_state: GameState) -> ActionEvaluation:
        raise NotImplementedError

    def choose_action(self, entity: EntityState, game_state: GameState) -> Direction:
        legal = self.legal_actions(entity, game_state)
        if not legal:
            return (0, 0)

        evaluations = [self.evaluate_for_direction(entity, game_state, direction) for direction in legal]
        evaluations.sort(key=lambda item: item.utility, reverse=True)
        top_utility = evaluations[0].utility
        best = [item for item in evaluations if abs(item.utility - top_utility) < 1e-6]
        choice = self.random.choice(best)
        return choice.direction

    def evaluate_for_direction(
        self, entity: EntityState, game_state: GameState, direction: Direction
    ) -> ActionEvaluation:
        raise NotImplementedError


class PacmanUtilityAgent(UtilityAgent):
    """Utility agent that guides Pac-Man towards pellets while avoiding danger."""

    pellet_weight = 6.0
    power_weight = 4.5
    ghost_avoid_weight = 8.0
    ghost_hunt_weight = 5.5
    inertia_bonus = 0.3
    time_penalty = 0.01

    def evaluate_for_direction(
        self, entity: EntityState, game_state: GameState, direction: Direction
    ) -> ActionEvaluation:
        current_tile = entity.position.to_tile(settings.TILE_SIZE)
        next_tile = collision.wrap_tile((current_tile[0] + direction[0], current_tile[1] + direction[1]))

        features: Dict[str, float] = {}
        utility = 0.0

        pellet_distance = _shortest_distance(next_tile, game_state.pellets, game_state)
        power_distance = _shortest_distance(next_tile, game_state.power_pellets, game_state)
        ghost_distance = _distance_to_entities(next_tile, list(game_state.ghosts.values()), game_state)

        if pellet_distance is not None:
            features["pellet_score"] = 1.0 / (pellet_distance + 1)
            utility += self.pellet_weight * features["pellet_score"]
        else:
            features["pellet_score"] = 0.0

        if power_distance is not None:
            features["power_score"] = 1.0 / (power_distance + 1)
            utility += self.power_weight * features["power_score"]
        else:
            features["power_score"] = 0.0

        if ghost_distance is not None:
            danger_score = 1.0 / (ghost_distance + 1)
            if game_state.frightened_timer > 0:
                utility += self.ghost_hunt_weight * danger_score
                features["ghost_score"] = danger_score
            else:
                utility -= self.ghost_avoid_weight * danger_score
                features["ghost_score"] = -danger_score
        else:
            features["ghost_score"] = 0.0

        if direction == entity.direction:
            utility += self.inertia_bonus
            features["inertia"] = self.inertia_bonus
        else:
            features["inertia"] = 0.0

        prospective_score = 0.0
        if next_tile in game_state.pellets:
            prospective_score += settings.PELLET_SCORE
        if next_tile in game_state.power_pellets:
            prospective_score += settings.POWER_PELLET_SCORE
        features["prospective_score"] = prospective_score
        utility += 0.002 * prospective_score

        features["time_penalty"] = -self.time_penalty * game_state.elapsed_time
        utility += features["time_penalty"]

        jitter = self.random.uniform(-0.05, 0.05)
        features["jitter"] = jitter
        utility += jitter

        return ActionEvaluation(direction=direction, utility=utility, features=features)


class GhostUtilityAgent(UtilityAgent):
    """Utility agent controlling ghost behavior based on scatter/chase modes."""

    chase_weight = 7.0
    scatter_weight = 3.5
    frightened_weight = 9.0
    inertia_bonus = 0.2
    reverse_penalty = 0.4

    scatter_targets: Dict[str, Tile] = {
        "blinky": (settings.MAZE_COLUMNS - 2, 1),
        "pinky": (1, 1),
        "inky": (settings.MAZE_COLUMNS - 2, settings.MAZE_ROWS - 2),
        "clyde": (1, settings.MAZE_ROWS - 2),
    }

    def __init__(self, ghost_name: str, rng: Optional[random.Random] = None) -> None:
        super().__init__(rng=rng)
        self.ghost_name = ghost_name

    def evaluate_for_direction(
        self, entity: EntityState, game_state: GameState, direction: Direction
    ) -> ActionEvaluation:
        current_tile = entity.position.to_tile(settings.TILE_SIZE)
        next_tile = collision.wrap_tile((current_tile[0] + direction[0], current_tile[1] + direction[1]))

        features: Dict[str, float] = {}
        utility = 0.0

        pacman_tile = game_state.pacman.position.to_tile(settings.TILE_SIZE)
        pacman_distance = _shortest_distance(next_tile, [pacman_tile], game_state)

        frightened = game_state.frightened_timer > 0

        if frightened:
            if pacman_distance is not None:
                avoid_score = pacman_distance + 1
                features["avoid_pacman"] = float(avoid_score)
                utility += self.frightened_weight * avoid_score
            else:
                features["avoid_pacman"] = 0.0
        else:
            if pacman_distance is not None:
                features["chase"] = 1.0 / (pacman_distance + 1)
                if game_state.scatter_mode:
                    utility -= self.scatter_weight * features["chase"]
                else:
                    utility += self.chase_weight * features["chase"]
            else:
                features["chase"] = 0.0

        if game_state.scatter_mode and not frightened:
            target = self.scatter_targets.get(self.ghost_name, (settings.MAZE_COLUMNS - 2, 1))
            scatter_distance = _shortest_distance(next_tile, [target], game_state)
            if scatter_distance is not None:
                features["scatter"] = 1.0 / (scatter_distance + 1)
                utility += self.scatter_weight * features["scatter"]
            else:
                features["scatter"] = 0.0
        else:
            features["scatter"] = 0.0

        if direction == (-entity.direction[0], -entity.direction[1]) and entity.direction != (0, 0):
            utility -= self.reverse_penalty
            features["reverse"] = -self.reverse_penalty
        else:
            features["reverse"] = 0.0

        if direction == entity.direction:
            utility += self.inertia_bonus
            features["inertia"] = self.inertia_bonus
        else:
            features["inertia"] = 0.0

        jitter = self.random.uniform(-0.03, 0.03)
        features["jitter"] = jitter
        utility += jitter

        return ActionEvaluation(direction=direction, utility=utility, features=features)
