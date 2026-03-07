"""Global configuration constants for the Pac-Man project."""

from pathlib import Path


# Paths -----------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
ASSET_DIR = BASE_DIR / "assets"
IMAGE_DIR = ASSET_DIR / "images"
SOUND_DIR = ASSET_DIR / "sounds"
LEVEL_DIR = BASE_DIR / "src" / "levels" / "layouts"


# Display ---------------------------------------------------------------------
TILE_SIZE = 24
MAZE_COLUMNS = 28
MAZE_ROWS = 31
SCREEN_WIDTH = TILE_SIZE * MAZE_COLUMNS
SCREEN_HEIGHT = TILE_SIZE * MAZE_ROWS + 80  # Extra space for HUD
FPS = 60


# Gameplay --------------------------------------------------------------------
PACMAN_SPEED = 4
PACMAN_POWER_SPEED = 5
GHOST_SPEED = 4
FRIGHTENED_SPEED = 3
POWER_UP_DURATION = 8.0  # seconds
SCATTER_INTERVAL = 7.0
CHASE_INTERVAL = 20.0
MAX_LIVES = 3
PELLET_SCORE = 10
POWER_PELLET_SCORE = 50
GHOST_EATEN_SCORE = 200


# Colors ----------------------------------------------------------------------
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
YELLOW = (255, 204, 0)
RED = (255, 0, 0)
CYAN = (0, 255, 255)
ORANGE = (255, 128, 0)
PINK = (255, 105, 180)
BLUE = (0, 51, 255)
HUD_TEXT = (240, 240, 240)
WALL_COLOR = (33, 33, 222)
PELLET_COLOR = (255, 200, 200)
POWER_PELLET_COLOR = (255, 255, 255)


# Audio -----------------------------------------------------------------------
SOUND_SAMPLE_RATE = 22050
SOUND_VOLUME = 0.3


