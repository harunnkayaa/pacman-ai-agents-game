from __future__ import annotations

from typing import Dict

import pygame

from .. import settings
from .. import assets


class AudioSystem:
    """Wrapper around pygame.mixer to manage sound playback."""

    def __init__(self) -> None:
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=settings.SOUND_SAMPLE_RATE)
        self.sounds: Dict[str, pygame.mixer.Sound] = assets.load_sounds()

    def play(self, name: str) -> None:
        sound = self.sounds.get(name)
        if sound is not None:
            sound.play()

    def stop_all(self) -> None:
        for sound in self.sounds.values():
            sound.stop()
