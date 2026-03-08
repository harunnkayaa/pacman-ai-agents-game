from __future__ import annotations

from typing import Dict

import pygame

from .. import settings
from ..state.game_state import GameState


class Renderer:
    """Handles all drawing operations for the game."""

    def __init__(self, screen: pygame.Surface, images: Dict[str, pygame.Surface]) -> None:
        self.screen = screen
        self.images = images
        self.font = pygame.font.Font(None, 28)
        self.big_font = pygame.font.Font(None, 48)
        self._menu_bg: pygame.Surface | None = None

    def _get_menu_background(self) -> pygame.Surface:
        """Menü arka planı: assets/images/menu_bg.png görseli (yoksa koyu gradient yedek)."""
        if self._menu_bg is not None:
            return self._menu_bg
        w, h = settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT
        path = settings.IMAGE_DIR / "menu_bg.png"
        try:
            if path.exists():
                img = pygame.image.load(str(path)).convert()
                self._menu_bg = pygame.transform.smoothscale(img, (w, h))
                return self._menu_bg
        except Exception:
            pass
        self._menu_bg = pygame.Surface((w, h))
        for y in range(h):
            t = y / h
            r = int(5 + 20 * (1 - t))
            g = int(5 + 15 * (1 - t))
            b = int(25 + 35 * (1 - t))
            pygame.draw.line(self._menu_bg, (r, g, b), (0, y), (w, y))
        dot_color = (255, 204, 0, 28)
        dot_surf = pygame.Surface((8, 8), pygame.SRCALPHA)
        pygame.draw.circle(dot_surf, dot_color, (4, 4), 3)
        step = 32
        for y in range(0, h, step):
            for x in range(0, w, step):
                if (x // step + y // step) % 2 == 0:
                    self._menu_bg.blit(dot_surf, (x, y))
        return self._menu_bg

    def draw_menu(self, selected: str) -> None:
        self.screen.blit(self._get_menu_background(), (0, 0))
        title = self.big_font.render("Pac-Man AI", True, settings.YELLOW)
        self.screen.blit(title, title.get_rect(center=(settings.SCREEN_WIDTH // 2, 120)))

        instructions = [
            "Press H to control Pac-Man",
            "Press C to watch AI vs AI",
            "Press ESC to quit",
        ]
        for idx, line in enumerate(instructions, start=1):
            text = self.font.render(line, True, settings.WHITE)
            self.screen.blit(
                text,
                text.get_rect(center=(settings.SCREEN_WIDTH // 2, 180 + idx * 36)),
            )

        selection_text = self.font.render(f"Current selection: {selected}", True, settings.HUD_TEXT)
        self.screen.blit(
            selection_text,
            selection_text.get_rect(center=(settings.SCREEN_WIDTH // 2, settings.SCREEN_HEIGHT - 60)),
        )
        pygame.display.flip()

    def draw_game(self, game_state: GameState, mode_label: str) -> None:
        self.screen.fill(settings.BLACK)
        self._draw_grid(game_state)
        self._draw_entities(game_state)
        self._draw_hud(game_state, mode_label)
        if not game_state.running and game_state.result:
            self._draw_result(game_state)
        pygame.display.flip()

    def _draw_grid(self, game_state: GameState) -> None:
        tile = settings.TILE_SIZE
        wall_surface = self.images["wall"]
        pellet_surface = self.images["pellet"]
        power_surface = self.images["power_pellet"]

        for y, row in enumerate(game_state.grid):
            for x, cell in enumerate(row):
                if cell == "#":
                    self.screen.blit(wall_surface, (x * tile, y * tile))

        for (x, y) in game_state.pellets:
            self.screen.blit(pellet_surface, (x * tile, y * tile))

        for (x, y) in game_state.power_pellets:
            self.screen.blit(power_surface, (x * tile, y * tile))

    def _draw_entities(self, game_state: GameState) -> None:
        tile = settings.TILE_SIZE
        pacman_pos = (
            int(game_state.pacman.position.x - tile / 2),
            int(game_state.pacman.position.y - tile / 2),
        )
        self.screen.blit(self.images["pacman"], pacman_pos)

        for name, ghost in game_state.ghosts.items():
            if not ghost.alive:
                continue
            sprite = self.images.get(name, self.images["blinky"])
            ghost_pos = (
                int(ghost.position.x - tile / 2),
                int(ghost.position.y - tile / 2),
            )
            if ghost.frightened:
                frightened_surface = sprite.copy()
                frightened_surface.fill((0, 0, 150, 150), special_flags=pygame.BLEND_RGBA_MULT)
                sprite = frightened_surface
            self.screen.blit(sprite, ghost_pos)

    def _draw_hud(self, game_state: GameState, mode_label: str) -> None:
        hud_y = settings.MAZE_ROWS * settings.TILE_SIZE + 10
        score_text = self.font.render(f"Score: {game_state.score}", True, settings.HUD_TEXT)
        time_text = self.font.render(f"Time: {game_state.elapsed_time:05.1f}s", True, settings.HUD_TEXT)
        lives_text = self.font.render(f"Lives: {game_state.lives}", True, settings.HUD_TEXT)
        mode_text = self.font.render(mode_label, True, settings.HUD_TEXT)

        self.screen.blit(score_text, (20, hud_y))
        self.screen.blit(time_text, (220, hud_y))
        self.screen.blit(lives_text, (420, hud_y))
        self.screen.blit(mode_text, (620, hud_y))

    def _draw_result(self, game_state: GameState) -> None:
        overlay = pygame.Surface((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        result_text = self.big_font.render(game_state.result or "Game Over", True, settings.WHITE)
        winner_text = self.font.render(f"Winner: {game_state.winner or 'N/A'}", True, settings.YELLOW)

        result_rect = result_text.get_rect(center=(settings.SCREEN_WIDTH // 2, settings.SCREEN_HEIGHT // 2 - 40))
        winner_rect = winner_text.get_rect(center=(settings.SCREEN_WIDTH // 2, settings.SCREEN_HEIGHT // 2 + 10))

        self.screen.blit(result_text, result_rect)
        self.screen.blit(winner_text, winner_rect)
