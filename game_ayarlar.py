from pathlib import Path
from typing import Sequence, Tuple



TILE_SIZE = 32
HUD_HEIGHT = 80
FPS = 60

COLOR_BACKGROUND = (12, 12, 20)
COLOR_WALL = (32, 64, 220)
COLOR_WALL_GLOW = (18, 18, 40)
COLOR_PELLET = (230, 220, 180)
COLOR_POWER = (255, 230, 120)
COLOR_PLAYER_ONE = (255, 255, 0)
COLOR_PLAYER_TWO = (255, 105, 180)
COLOR_TEXT = (240, 240, 240)
COLOR_HUD = (8, 8, 8)
COLOR_SHADOW = (0, 0, 0, 140)
COLOR_GATE = (180, 220, 255)

# power modundaki hayalet renkleri
COLOR_GHOST_FRIGHT = (0, 80, 255)
COLOR_GHOST_FRIGHT_BLINK = (240, 240, 240)

PLAYER_SPEED_PIXELS_PER_SECOND = 140
GHOST_SPEED_PIXELS_PER_SECOND = 120



PELLET_SCORE = 1.0        # küçük yem
POWER_SCORE = 10.0        # power pellet
GHOST_EAT_SCORE = 20.0    # hayalet yeme

PLAYER_COLLISION_PENALTY = 20.0      # hayalete yakalanınca -20 puan ve 1 can
PLAYER_DEATH_UTILITY = 1000.0        # utility tarafında ölüm cezası

# Normal mod: hayatta kalma > skor
W_DOT_NORMAL = 2.0
W_POWER_NORMAL = 8.0
W_GHOST_SAFETY = 200.0   # hayalet yakınken kaçma isteği

# Power mod: hayalet kovalamak değerli
W_DOT_POWER = 1.0
W_POWER_POWER = 0.0
W_GHOST_CHASE = 50.0

POWER_DURATION = 6.0

# Reverse (geri dönme) cezaları
REV_PENALTY = 2.0
REV_PENALTY_POWER = 1.0



LEVEL_LAYOUT: Sequence[str] = [
    "############################",
    "#............##............#",
    "#.####.#####.##.#####.####.#",
    "#o####.#####.##.#####.####o#",
    "#.####.#####.##.#####.####.#",
    "#..........................#",
    "#.####.##.########.##.####.#",
    "#.####.##.########.##.####.#",
    "#......##.....o....##......#",
    "######.##### ## #####.######",
    "######.##### ## #####.######",
    "######.##    =     ##.######",
    "######.## #gg  gg# ##.######",
    "#     .   #gggggg#   .     #",
    "######.## #gggggg# ##.######",
    "######.## ######## ##.######",
    "######.##          ##.######",
    "######.## ######## ##.######",
    "#o...........##...........o#",
    "#.####.#####.##.#####.####.#",
    "#.####.#####.##.#####.####.#",
    "#...##.......12.......##...#",
    "###.##.##.########.##.##.###",
    "###.##.##.########.##.##.###",
    "#......##..........##......#",
    "#.##########.##.##########.#",
    "#.##########.##.##########.#",
    "#..........................#",
    "############################",
]

DIRECTION_VECTORS: Tuple[Tuple[int, int], ...] = (
    (1, 0),
    (-1, 0),
    (0, 1),
    (0, -1),
)

READY_DURATION = 2.0  # READY! yazısının ekranda kalma süresi
GHOST_RELEASE_DELAYS = [0.0, 2.0, 4.0, 6.0]



PROJE_KOK_DIZIN = Path(__file__).parent
GHOST_IMAGES_DIR = PROJE_KOK_DIZIN / "assets" / "ghost_images"
SOUNDS_DIR = PROJE_KOK_DIZIN / "assets" / "sounds"
