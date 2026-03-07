"""Asset loading utilities for images and sounds."""

from __future__ import annotations

import math
from array import array
from typing import Dict

import pygame

from . import settings


def load_images() -> Dict[str, pygame.Surface]:
    """Create and return sprite surfaces for the game."""
    tile = settings.TILE_SIZE
    images: Dict[str, pygame.Surface] = {}

    pacman_surface = pygame.Surface((tile, tile), pygame.SRCALPHA)
    pygame.draw.circle(
        pacman_surface,
        settings.YELLOW,
        (tile // 2, tile // 2),
        tile // 2 - 2,
    )
    mouth_rect = pygame.Rect(tile // 2, tile // 4, tile // 2, tile // 2)
    pacman_surface.fill((0, 0, 0, 0), mouth_rect)
    images["pacman"] = pacman_surface

    for name, color in (
        ("blinky", settings.RED),
        ("inky", settings.CYAN),
        ("pinky", settings.PINK),
        ("clyde", settings.ORANGE),
    ):
        ghost_surface = pygame.Surface((tile, tile), pygame.SRCALPHA)
        pygame.draw.circle(
            ghost_surface,
            color,
            (tile // 2, tile // 2 - 2),
            tile // 2 - 2,
        )
        pygame.draw.rect(
            ghost_surface,
            color,
            pygame.Rect(2, tile // 2 - 2, tile - 4, tile // 2),
        )
        eyes_color = settings.WHITE
        pygame.draw.circle(
            ghost_surface,
            eyes_color,
            (tile // 2 - 4, tile // 2 - 4),
            3,
        )
        pygame.draw.circle(
            ghost_surface,
            eyes_color,
            (tile // 2 + 4, tile // 2 - 4),
            3,
        )
        images[name] = ghost_surface

    pellet_surface = pygame.Surface((tile, tile), pygame.SRCALPHA)
    pygame.draw.circle(
        pellet_surface,
        settings.PELLET_COLOR,
        (tile // 2, tile // 2),
        4,
    )
    images["pellet"] = pellet_surface

    power_surface = pygame.Surface((tile, tile), pygame.SRCALPHA)
    pygame.draw.circle(
        power_surface,
        settings.POWER_PELLET_COLOR,
        (tile // 2, tile // 2),
        7,
    )
    images["power_pellet"] = power_surface

    wall_surface = pygame.Surface((tile, tile))
    wall_surface.fill(settings.WALL_COLOR)
    images["wall"] = wall_surface

    return images


def generate_tone(frequency: float, duration: float) -> pygame.mixer.Sound:
    """Generate a simple sine wave tone."""
    sample_rate = settings.SOUND_SAMPLE_RATE
    amplitude = 32767
    total_samples = int(duration * sample_rate)
    samples = array("h")
    for n in range(total_samples):
        value = int(amplitude * math.sin(2 * math.pi * frequency * n / sample_rate))
        samples.append(value)
    raw_sound = pygame.mixer.Sound(buffer=samples)
    raw_sound.set_volume(settings.SOUND_VOLUME)
    return raw_sound


def load_sounds() -> Dict[str, pygame.mixer.Sound]:
    """Create and return sound effects."""
    return {
        "pellet": generate_tone(850, 0.07),
        "power": generate_tone(440, 0.3),
        "ghost": generate_tone(220, 0.4),
        "loss": generate_tone(110, 0.6),
        "win": generate_tone(660, 0.6),
    }


