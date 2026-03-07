# Pac-Man Agent Project Design

## Project Overview

This project recreates the classic Pac-Man experience with both human and AI-controlled gameplay. The implementation targets two playable modes selectable from the start screen:

- **Human vs Computer:** the player controls Pac-Man using the keyboard while the AI manages the ghosts.
- **Computer vs Computer:** both Pac-Man and the ghosts are controlled by utility-based agents, allowing the computer to play autonomously.

The game tracks score and elapsed time for every run. Winners are determined by maximizing score while minimizing time taken to finish (completing the map or exhausting lives).

## Requirements Recap

- Graphical interface with audio feedback (implemented with `pygame`).
- Environment elements: walls, pellets (food), power pellets (energy), ghosts.
- Track score and elapsed time; display leaderboards for fastest high scores.
- AI agent follows a utility-based decision process.
- Incorporate the PEAS (Performance, Environment, Actuators, Sensors) framework.

## PEAS Definition

| Component     | Description                                                                 |
|---------------|-----------------------------------------------------------------------------|
| **Performance** | Maximize score, minimize completion time, avoid losing all lives.           |
| **Environment** | Grid-based maze with walls, pellets, power pellets, ghosts, and tunnels.    |
| **Actuators**   | Movement commands (up/down/left/right), power-up usage, ghost movement.     |
| **Sensors**     | Visibility of nearby tiles, positions of ghosts, pellets, power-up status.  |

## High-Level Architecture

```
src/
  game.py              # Entry point, mode selection, main loop
  settings.py          # Constants and configuration
  assets.py            # Asset loading utilities
  state/
    __init__.py
    game_state.py      # Global game state container
    entity_state.py    # Entity-specific state tracking
  entities/
    __init__.py
    pacman.py          # Human + AI control
    ghost.py           # Ghost behaviors
    pellet.py          # Pellet and power pellet logic
  agents/
    __init__.py
    utility_agent.py   # Generic utility-based agent
    pacman_agent.py    # Pac-Man decision logic
    ghost_agent.py     # Ghost decision logic
  systems/
    __init__.py
    rendering.py       # Drawing routines
    audio.py           # Sound playback
    input.py           # Human control handling
    collision.py       # Collision detection and resolution
  levels/
    __init__.py
    loader.py          # Read level matrix/layout
    layouts/           # Text-based level files
tests/
  test_agents.py       # Unit tests for agent utility functions
  test_collision.py    # Collision edge cases
```

## Utility-Based Agent Design

The utility agent evaluates possible actions using a set of weighted features:

- **Pac-Man Agent Features**
  - Distance to nearest pellet (prefer smaller).
  - Distance to nearest power pellet (when ghosts are near).
  - Distance to ghosts (prefer larger when vulnerable, smaller when powered up).
  - Remaining time (penalize long paths).
  - Score change projections.

- **Ghost Agent Features**
  - Distance to Pac-Man (prefer smaller, except when frightened).
  - Proximity to scatter corners during scatter mode.
  - Hazard avoidance when Pac-Man is powered up.

Each agent computes a utility score per legal action and selects the maximum. We will implement cooling schedules or randomization to avoid deterministic loops.

## Game Flow

1. **Startup:** Load assets, show main menu, allow mode selection (human vs computer).
2. **Gameplay Loop:**
   - Process input (human or AI).
   - Update agents, move entities, resolve collisions.
   - Update scoring, time, and lives.
   - Render frame and play relevant sounds.
3. **End Conditions:** Player clears all pellets or loses all lives (Pac-Man), or timer limit reached. Display results and record high score/time.

## Scoring and Timekeeping

- Standard pellet: +10 points.
- Power pellet: +50 points.
- Eating frightened ghost: +200 points (doubling each consecutive ghost).
- Bonus fruit (optional future enhancement).
- Elapsed time recorded in seconds since mode start.

## Sound and Graphics

- Sprite sheets for Pac-Man, ghosts, pellets, and walls.
- Background music loop and sound effects for pellet consumption, power-ups, and ghost interactions.
- Assets stored in `assets/images` and `assets/sounds`.

## Testing Strategy

- Unit tests for agent utility calculations.
- Collision detection tests ensuring movement obeys walls and tunnels.
- Simulation tests verifying score/time metrics shape expected winner selection.

## Next Steps

1. Implement `settings.py` and reusable utilities (asset loading, level parser).
2. Build core entity classes and state containers.
3. Develop rendering and event systems.
4. Implement the utility-based agent logic for Pac-Man and ghosts.
5. Integrate scoring, timing, and win condition evaluation.

