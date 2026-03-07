from __future__ import annotations

from typing import Optional, Tuple

import pygame

from ..entities.pacman import Pacman

Direction = Tuple[int, int]

KEY_TO_DIRECTION = {
    pygame.K_UP: (0, -1),
    pygame.K_DOWN: (0, 1),
    pygame.K_LEFT: (-1, 0),
    pygame.K_RIGHT: (1, 0),
    pygame.K_w: (0, -1),
    pygame.K_s: (0, 1),
    pygame.K_a: (-1, 0),
    pygame.K_d: (1, 0),
}


def process_events(pacman: Optional[Pacman], allow_input: bool) -> Tuple[bool, bool, bool]:
    """Return (quit_requested, toggle_pause, confirm)."""
    quit_requested = False
    toggle_pause = False
    confirm = False

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            quit_requested = True
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                quit_requested = True
            elif event.key == pygame.K_SPACE:
                toggle_pause = True
            elif event.key == pygame.K_RETURN:
                confirm = True
            elif allow_input and pacman is not None:
                direction = KEY_TO_DIRECTION.get(event.key)
                if direction:
                    pacman.set_pending_direction(direction)
    return quit_requested, toggle_pause, confirm
