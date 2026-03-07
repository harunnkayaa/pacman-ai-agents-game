from collections import deque
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import pygame

from game_ayarlar import (
    TILE_SIZE,
    PLAYER_SPEED_PIXELS_PER_SECOND,
    GHOST_SPEED_PIXELS_PER_SECOND,
    PELLET_SCORE,
    POWER_SCORE,
    GHOST_EAT_SCORE,
    PLAYER_COLLISION_PENALTY,
    PLAYER_DEATH_UTILITY,
    W_DOT_NORMAL,
    W_POWER_NORMAL,
    W_GHOST_SAFETY,
    W_DOT_POWER,
    W_POWER_POWER,
    W_GHOST_CHASE,
    POWER_DURATION,
    REV_PENALTY,
    REV_PENALTY_POWER,
    DIRECTION_VECTORS,
)
from oyun_utils import (
    manhattan_mesafe,
    bfs_yolu,
    koridor_guvenligi,
    en_yakin_mesafe,
)


class GameMap:
    """Harita + duvar / pellet / power / spawn bilgisi."""

    def __init__(self, layout: Sequence[str]) -> None:
        # harita satırları boş olamaz
        if not layout:
            raise ValueError("Layout must contain at least one row.")
        # satırlardaki newline karakterlerini temizleyip saklıyoruz
        self.layout = [row.rstrip("\n") for row in layout]
        self.height = len(self.layout)
        self.width = len(self.layout[0])
        self.pixel_width = self.width * TILE_SIZE
        self.pixel_height = self.height * TILE_SIZE

        # duvar ve gate matrixleri false ile başlatılıyor
        self.walls = [[False] * self.width for _ in range(self.height)]
        self.gate = [[False] * self.width for _ in range(self.height)]
        # pen alanı, pellet ve power konumları, oyuncu başlangıç kareleri
        self.pen_tiles: List[Tuple[int, int]] = []
        self.initial_pellets: List[Tuple[int, int]] = []
        self.initial_powers: List[Tuple[int, int]] = []
        self.player_starts: Dict[str, Tuple[int, int]] = {}

        # layout karakterlerini parse edip harita yapısını dolduruyoruz
        self.parse_layout()
        # pen içinden çıkış için üst ve alt duvarlarda açıklık açıyoruz
        self.carve_pen_exits()
        # oyun başı pellet/power setlerini aktifleştiriyoruz
        self.reset()

    def carve_pen_exits(self) -> None:
        """Pen'in üst ve alt duvarına (gate hizasında) 3 hücrelik açıklık aç."""
        # pen tanımlı değilse çıkış açmaya gerek yok
        if not self.pen_tiles:
            return
        # pen içindeki en küçük ve en büyük y değerleri bulunuyor
        min_y = min(y for _, y in self.pen_tiles)
        max_y = max(y for _, y in self.pen_tiles)
        # penin ortasına denk gelen x konumlarının ortalaması alınıyor
        xs = [x for x, y in self.pen_tiles if y == (min_y + max_y) // 2]
        cx = (sum(xs) // len(xs)) if xs else (self.width // 2)

        # penin üst ve alt duvar satırları
        top_wall_y = min_y - 1
        bot_wall_y = max_y + 1
        # ortadaki x in etrafındaki 3 hücrede kapıyı açıyoruz
        for x in (cx - 1, cx, cx + 1):
            if 0 <= x < self.width:
                if 0 <= top_wall_y < self.height:
                    self.walls[top_wall_y][x] = False
                if 0 <= bot_wall_y < self.height:
                    self.walls[bot_wall_y][x] = False

    def parse_layout(self) -> None:
        # layouttaki her satırı ve sütunu gezerek sembollerle haritayı kuruyoruz
        for y, row in enumerate(self.layout):
            if len(row) != self.width:
                raise ValueError("All layout rows must have the same width.")
            for x, t in enumerate(row):
                if t == "#":
                    self.walls[y][x] = True
                elif t == "=":
                    self.gate[y][x] = True
                elif t == "g":
                    self.pen_tiles.append((x, y))
                elif t == ".":
                    self.initial_pellets.append((x, y))
                elif t == "o":
                    self.initial_powers.append((x, y))
                elif t == "1":
                    self.player_starts["p1"] = (x, y)
                elif t == "2":
                    self.player_starts["p2"] = (x, y)
                elif t == " ":
                    pass
                else:
                    raise ValueError(f"Unsupported tile '{t}' at ({x},{y})")

        # hem p1 hem p2 start konumları zorunlu
        if "p1" not in self.player_starts or "p2" not in self.player_starts:
            raise ValueError("Missing player spawns 1 and/or 2.")

    def reset(self) -> None:
        # pellet ve powerlar oyun başındaki konumlarına göre setlere dolduruluyor
        self.pellets: set[Tuple[int, int]] = set(self.initial_pellets)
        self.powers: set[Tuple[int, int]] = set(self.initial_powers)

    def is_blocked(self, x: int, y: int) -> bool:
        # harita sınırı dışındaysa otomatik bloklu say
        if x < 0 or y < 0 or x >= self.width or y >= self.height:
            return True
        # duvar olan kareler bloklu
        return self.walls[y][x]

    def can_move(self, tile: Tuple[int, int], direction: pygame.Vector2) -> bool:
        # yön vektörü sıfırsa hareket yok
        dx, dy = int(direction.x), int(direction.y)
        if dx == 0 and dy == 0:
            return False
        nx, ny = tile[0] + dx, tile[1] + dy
        # harita dışına çıkılıyorsa hareket yasak
        if nx < 0 or ny < 0 or nx >= self.width or ny >= self.height:
            return False
        # hedef kare duvar değilse hareket serbest
        return not self.is_blocked(nx, ny)


class Player:
    def __init__(
        self,
        name: str,
        color: Tuple[int, int, int],
        start_tile: Tuple[int, int],
        controls: Sequence[Tuple[int, Tuple[int, int]]],
        is_ai: bool = False,
        speed: int = PLAYER_SPEED_PIXELS_PER_SECOND,
    ) -> None:
        # oyuncu temel özellikleri ve parametreleri atanıyor
        self.name = name
        self.lives = 3
        self.color = color
        self.start_tile = start_tile
        self.controls = list(controls)
        self.is_ai = is_ai
        self.speed = float(speed)

        # konum ve yön vektörleri
        self.position = pygame.Vector2(0, 0)
        self.direction = pygame.Vector2(0, 0)
        self.next_direction = pygame.Vector2(0, 0)
        # grid üzerinde hedef kare ve piksel pozisyonu
        self.target_tile: Optional[Tuple[int, int]] = None
        self.target_pixel: Optional[pygame.Vector2] = None
        # ai için önceden hesaplanmış yol
        self.ai_path: List[Tuple[int, int]] = []
        self.score = 0
        self.power_mode_until = 0.0
        self.last_score_time: float = 0.0
        # başlangıç konumuna sıfırlama
        self.reset()

    def reset(self) -> None:
        # oyuncu başlangıç karesinin ortasına yerleştiriliyor
        self.position.update(
            self.start_tile[0] * TILE_SIZE + TILE_SIZE / 2,
            self.start_tile[1] * TILE_SIZE + TILE_SIZE / 2,
        )
        # yön bilgileri ve hedefler temizleniyor
        self.direction.update(0, 0)
        self.next_direction.update(0, 0)
        self.target_tile = None
        self.target_pixel = None
        self.ai_path.clear()
        self.score = 0
        self.power_mode_until = 0.0
        self.last_score_time = 0.0

    def tile_position(self) -> Tuple[int, int]:
        # piksel konumundan grid (kare) konumuna geçiş
        return int(self.position.x // TILE_SIZE), int(self.position.y // TILE_SIZE)

    def process_input(self, pressed) -> None:
        # ai ise klavye girdisi işlenmiyor
        if self.is_ai:
            return
        # tanımlı control tuşları üzerinden sırayla bakıp basılı olana göre yön seçiliyor
        for key, delta in self.controls:
            if pressed[key]:
                self.next_direction = pygame.Vector2(delta)
                return

    def update(
        self,
        dt: float,
        game_map: "GameMap",
        now: float,
        ghosts: Sequence["Ghost"],
        sounds,
    ) -> None:
        # ai oyuncu ise her frame utility tabanlı yön kararı verdiriyoruz
        if self.is_ai:
            self.ai_yon_sec(game_map, ghosts, now)

        # sıradaki grid hedefi seçiliyor
        self.sonraki_hedefi_sec(game_map)
        # seçilen hedefe doğru hareket ediyoruz
        self.hedefe_hareket_et(dt)

        # kare merkezine vardığımızda yem ve power kontrolü
        if self.target_tile is None:
            t = self.tile_position()
            if t in game_map.pellets:
                game_map.pellets.remove(t)
                self.score += PELLET_SCORE
                self.last_score_time = now
                if sounds:
                    sounds.play_pellet()
            elif t in game_map.powers:
                game_map.powers.remove(t)
                self.score += POWER_SCORE
                self.power_mode_until = now + POWER_DURATION
                self.last_score_time = now
                if sounds:
                    sounds.play_power()

    def sonraki_hedefi_sec(self, game_map: "GameMap") -> None:
        # zaten bir hedef kareye doğru giderken tekrar hedef seçmiyoruz
        if self.target_tile is not None:
            return

        cur = self.tile_position()

        # önce oyuncunun istediği next_direction mümkünse onu aktif yön yapıyoruz
        if self.next_direction.length_squared() > 0 and game_map.can_move(cur, self.next_direction):
            self.direction = self.next_direction.copy()
        elif not game_map.can_move(cur, self.direction):
            # mevcut yön tıkandıysa hareket sıfırlanıyor
            self.direction.update(0, 0)

        # yön yoksa hiç bir yere gitmiyoruz
        if self.direction.length_squared() == 0:
            return

        # bir sonraki kare hesaplanıyor
        nx = cur[0] + int(self.direction.x)
        ny = cur[1] + int(self.direction.y)

        # pen içi karelere girmesine izin vermiyoruz
        if (nx, ny) in game_map.pen_tiles:
            return
        # gate karelerinden pacman geçmesin
        if game_map.gate[ny][nx]:
            return

        # duvar kontrolü, hareket mümkün değilse iptal
        if not game_map.can_move(cur, self.direction):
            return

        # hedef kare ve hedef piksel koordinatı atanıyor
        self.target_tile = (nx, ny)
        self.target_pixel = pygame.Vector2(
            nx * TILE_SIZE + TILE_SIZE / 2,
            ny * TILE_SIZE + TILE_SIZE / 2,
        )

    def hedefe_hareket_et(self, dt: float) -> None:
        # hedef yoksa bulunduğu kare merkezine snap ediyoruz
        if self.target_tile is None or self.target_pixel is None:
            cx, cy = self.tile_position()
            self.position.update(
                cx * TILE_SIZE + TILE_SIZE / 2,
                cy * TILE_SIZE + TILE_SIZE / 2,
            )
            return

        # hedef piksele olan vektör ve mesafe
        vec = self.target_pixel - self.position
        d = vec.length()

        # hedeften sapma yoksa hedefi bitmiş sayıyoruz
        if d == 0:
            self.target_tile = None
            self.target_pixel = None
            return

        # bu frame gideceğimiz mesafe
        travel = self.speed * dt
        if travel >= d:
            # hedefi geçtiysek direkt hedef piksele snap ediyoruz
            self.position.update(self.target_pixel)
            self.target_tile = None
            self.target_pixel = None
        else:
            # normalleştirilmiş vektör ile adım adım ilerliyoruz
            self.position += vec.normalize() * travel

    # ========================== UTILITY-BASED AI ================================ #

    def ai_yon_sec(
        self,
        game_map: "GameMap",
        ghosts: ["Ghost"],
        now: float,
    ) -> None:
        # utility tabanlı karar için şu anki grid konumunu alıyoruz
        cur = self.tile_position()

        # geçerli olabilecek yön adaylarını topluyoruz
        candidates: List[pygame.Vector2] = []
        for dx, dy in DIRECTION_VECTORS:
            nxt = (cur[0] + dx, cur[1] + dy)

            # pen karelerine girmesin
            if nxt in game_map.pen_tiles:
                continue
            # gate karelerine girmesin
            if game_map.gate[nxt[1]][nxt[0]]:
                continue

            v = pygame.Vector2(dx, dy)
            if game_map.can_move(cur, v):
                candidates.append(v)

        # hareket edebileceği yön yoksa ai kilitleniyor
        if not candidates:
            return

        # pen dışındaki hayaletlerin konumları
        ghost_tiles = [g.tile_position() for g in ghosts if g.state != GhostState.IN_PEN]

        # power mode aktif mi ve ne kadar süre kaldı bilgisi
        is_power = self.power_mode_until > now
        power_remaining = max(0.0, self.power_mode_until - now)

        # hayaletle ilgili güvenlik ve kovalama mesafe eşikleri
        DANGER_RADIUS = 7
        CHASE_RADIUS_MAX = 50

        best_dir: Optional[pygame.Vector2] = None
        best_u = -float("inf")

        # her yön için utility skoru hesaplanıyor
        for d in candidates:
            nx, ny = cur[0] + int(d.x), cur[1] + int(d.y)
            nxt_tile = (nx, ny)

            # bu kareden hayalete, yeme ve power a en yakın mesafeler
            d_ghost = en_yakin_mesafe(nxt_tile, ghost_tiles) if ghost_tiles else 10 ** 9
            d_dot = en_yakin_mesafe(nxt_tile, game_map.pellets)
            d_power = en_yakin_mesafe(nxt_tile, game_map.powers)

            score_util = 0.0 #yem/power/hayalet yeme gibi pozitif faydalar.
            ghost_penalty = 0.0 #yem/power/hayalet yeme gibi pozitif faydalar.
            safety_score = 0.0 #bfs ile koridor güvenliği (tuzak/çıkmaz sokak) cezası.

            # power mode aktifken davranış
            if is_power:
                # kalan süreye göre chase vs yem toplama arasında ağırlık kaydırma
                phase = (
                    min(1.0, max(0.0, power_remaining / POWER_DURATION))
                    if POWER_DURATION > 0
                    else 0.0
                )

                # menzil içindeki hayaletlere doğru gitmek için chase faydası
                if ghost_tiles and d_ghost < CHASE_RADIUS_MAX:
                    chase_util = W_GHOST_CHASE / (1 + d_ghost)
                else:
                    chase_util = 0.0

                # yem toplamanın utility katkısı
                dot_util = 0.0
                if d_dot < 10 ** 8:
                    dot_util = W_DOT_POWER / (1 + d_dot)

                # power süresi başta hayalet kovalamaya, sonda yem toplamaya kayıyor
                score_util += phase * chase_util + (1.0 - phase) * dot_util

                # direkt hayalet karesine basıyorsa büyük bir hayalet yeme bonusu veriyoruz
                if ghost_tiles and nxt_tile in ghost_tiles:
                    score_util += 50.0 * GHOST_EAT_SCORE
                    ghost_penalty = 0.0
                    safety_score = 0.0
                else:
                    # power bitmeye yakınken hala hayalete çok yaklaşma cezası veriyoruz
                    if ghost_tiles and power_remaining < 1.5:
                        if d_ghost == 0:
                            ghost_penalty -= PLAYER_DEATH_UTILITY
                        elif d_ghost <= 1:
                            ghost_penalty -= PLAYER_DEATH_UTILITY * 0.7
                        elif d_ghost < DANGER_RADIUS:
                            ghost_penalty -= (W_GHOST_SAFETY * 0.5) / (d_ghost ** 2)

                    # hem hayalet yakınsa hem de power süresi düşükse koridor tuzağı kontrolü
                    if ghost_tiles and (d_ghost < DANGER_RADIUS or power_remaining < 2.0):
                        free_tiles = koridor_guvenligi(game_map, nxt_tile, ghost_tiles, max_depth=6)
                        if free_tiles < 4:
                            safety_score -= 4000.0

            else:
                # rescue_mode: hayalet baskısı varken powera yönlenme modu
                rescue_mode = False

                if ghost_tiles:
                    # hayalet bitişikse direkt ölüm cezası
                    if d_ghost == 1:
                        ghost_penalty -= PLAYER_DEATH_UTILITY
                    else:
                        # power yeri hayaletten daha yakınsa powera kaçma moduna gir
                        if d_power < 10 ** 8 and d_ghost < 10 ** 8 and d_power <= d_ghost:
                            rescue_mode = True

                        # normalde hayalete yaklaşma cezası
                        if not rescue_mode:
                            if d_ghost <= 3:
                                ghost_penalty -= PLAYER_DEATH_UTILITY * 0.7
                            elif d_ghost < DANGER_RADIUS:
                                ghost_penalty -= W_GHOST_SAFETY / (d_ghost ** 2)

                            # hayalet yakınken çıkmaz sokaklara girmeyi ağır cezalandır
                            if d_ghost < DANGER_RADIUS:
                                free_tiles = koridor_guvenligi(
                                    game_map, nxt_tile, ghost_tiles, max_depth=6
                                )
                                if free_tiles < 4:
                                    safety_score -= 8000.0

                # normal modda yem toplamanın utility katkısı
                if d_dot < 10 ** 8:
                    score_util += W_DOT_NORMAL / (1 + d_dot)

                # powerlara olan mesafeye bağlı utility, rescue modda ağırlık artıyor
                if d_power < 10 ** 8:
                    weight = W_POWER_NORMAL * (3.0 if rescue_mode else 1.0)
                    score_util += weight / (1 + d_power)

                    # power karesinin üstündeyse ekstra bonus
                    if nxt_tile in game_map.powers:
                        score_util += 20.0 * POWER_SCORE

            # toplam utility = puan faydası + hayalet cezası + koridor güvenliği
            util = score_util + ghost_penalty + safety_score

            # ani geri dönüşleri cezalandırıyoruz ki zigzag spam olmasın
            if self.direction.length_squared() > 0:
                if (int(d.x), int(d.y)) == (-int(self.direction.x), -int(self.direction.y)):
                    if is_power:
                        util -= REV_PENALTY_POWER
                    else:
                        util -= REV_PENALTY

            # en yüksek utilityli yönü seçiyoruz
            if util > best_u:
                best_u = util
                best_dir = d

        # bir yön seçildiyse next_direction olarak kaydediyoruz
        if best_dir is not None:
            self.next_direction = best_dir


class GhostState:
    IN_PEN = 0
    EXITING = 1
    CHASE = 2


class Ghost:
    def __init__(
        self,
        image: pygame.Surface,
        start_tile: Tuple[int, int],
        release_delay: float,
        behavior_index: int = 0,
    ):
        # hayalet sprite resmi ve başlangıç grid konumu
        self.image = image
        self.start_tile = start_tile
        # temel hız ve release gecikmesi
        self.speed = float(GHOST_SPEED_PIXELS_PER_SECOND)
        self.base_speed = float(GHOST_SPEED_PIXELS_PER_SECOND)
        self.release_delay = release_delay
        # davranış tipi indeks (blinky, pinky tarzı roller)
        self.behavior_index = behavior_index
        self.position = pygame.Vector2(0, 0)
        # başlangıçta pen içinde
        self.state = GhostState.IN_PEN
        # hayaletin izleyeceği grid yolu
        self.path: List[Tuple[int, int]] = []
        self.target_tile: Optional[Tuple[int, int]] = None
        self.target_pixel: Optional[pygame.Vector2] = None
        # başlangıç durumuna sıfırlama
        self.reset()

    def reset(self) -> None:
        # hayalet başlangıç karesinin ortasına yerleştiriliyor
        self.position.update(
            self.start_tile[0] * TILE_SIZE + TILE_SIZE / 2,
            self.start_tile[1] * TILE_SIZE + TILE_SIZE / 2,
        )
        # pen içine geri dönüyor ve yol bilgileri temizleniyor
        self.state = GhostState.IN_PEN
        self.path.clear()
        self.target_tile = None
        self.target_pixel = None
        self.lives = 3
        self.speed = self.base_speed

    def tile_position(self) -> Tuple[int, int]:
        # piksel konumundan grid kare konumuna geçiş
        return int(self.position.x // TILE_SIZE), int(self.position.y // TILE_SIZE)

    def update(
        self,
        dt: float,
        game_map: "GameMap",
        players: Sequence[Player],
        now: float,
        gate_exit: Tuple[int, int],
    ) -> None:
        # power mode varken hayalet yavaşlıyor, yoksa normal hıza dönüyor
        if any(p.power_mode_until > now for p in players):
            self.speed = self.base_speed * 0.6
        else:
            self.speed = self.base_speed

        # pen içindeyken release_delay zamanı gelince çıkış yolunu hesaplayıp exiting moduna geçiyor
        if self.state == GhostState.IN_PEN:
            if now >= self.release_delay:
                self.path = bfs_yolu(
                    self.tile_position(), gate_exit, game_map, treat_gate_as_empty=True
                )
                self.state = GhostState.EXITING

        # exiting durumunda çıkış yolunu takip ediyor
        if self.state == GhostState.EXITING:
            self.yol_takip_et(dt)
            # gate çıkış karesine gelince chase moduna geçiyor
            if self.tile_position() == gate_exit:
                self.state = GhostState.CHASE
                self.path.clear()
                self.target_tile = None
                self.target_pixel = None

        # chase durumunda oyuncuları kovalama veya kaçma davranışı çalışıyor
        if self.state == GhostState.CHASE:
            self.kovala(dt, game_map, players, now)

    def kovala(
        self,
        dt: float,
        game_map: "GameMap",
        players: Sequence[Player],
        now: float,
    ) -> None:
        # hayaletin mevcut grid konumu
        my = self.tile_position()

        # power modda olan oyuncular ve normal oyuncular ayrı tutuluyor
        scary_players = [p for p in players if p.power_mode_until > now]
        normal_players = [p for p in players if p.power_mode_until <= now]

        target_tile = None

        # eğer power modda oyuncu varsa önce ondan kaçmayı deniyor
        if scary_players:
            danger_player = min(scary_players, key=lambda p: manhattan_mesafe(p.tile_position(), my))
            danger_pos = danger_player.tile_position()

            # çok yakınsa direkt kaçış modu
            if manhattan_mesafe(danger_pos, my) < 8:
                self.path = []
                self.kac(danger_pos, game_map)
                self.yol_takip_et(dt)
                return
            else:
                # uzaksa normal oyunculardan birini kovalamayı tercih edebilir
                if normal_players:
                    target_tile = self.chase_target_sec(normal_players, game_map)
        elif normal_players:
            # power yokken en yakın normal oyuncuyu hedef seçiyor
            target_tile = self.chase_target_sec(normal_players, game_map)

        # bir hedef kare varsa oraya bfs ile yol çizdiriyoruz
        if target_tile:
            if not self.path or self.path[-1] != target_tile:
                self.path = bfs_yolu(my, target_tile, game_map)

        # güncel path üzerinden hareket
        self.yol_takip_et(dt)

    def chase_target_sec(
        self,
        players: Sequence[Player],
        game_map: "GameMap",
    ) -> Optional[Tuple[int, int]]:
        # oyuncu yoksa takip edilecek kimse yok
        if not players:
            return None
        my_tile = self.tile_position()
        # manhattan mesafesi en küçük oyuncu baz alınacak
        nearest = min(players, key=lambda p: manhattan_mesafe(p.tile_position(), my_tile))
        base_tile = nearest.tile_position()
        idx = self.behavior_index

        # idx 0: direkt oyuncunun olduğu kareye koş
        if idx == 0:
            return base_tile

        # idx 1: oyuncunun ilerlediği yönde bir kaç kare ilerisini hedefle (pinky benzeri davranış)
        if idx == 1:
            dir_vec = nearest.direction
            dx, dy = int(dir_vec.x), int(dir_vec.y)
            tx, ty = base_tile
            steps_ahead = 2
            if dx == 0 and dy == 0:
                return base_tile
            ax = tx + dx * steps_ahead
            ay = ty + dy * steps_ahead
            if (
                0 <= ax < game_map.width
                and 0 <= ay < game_map.height
                and not game_map.walls[ay][ax]
            ):
                return (ax, ay)
            return base_tile

        # idx 2: iki oyuncunun orta noktası gibi daha akıllı bir hedef belirleme
        if idx == 2:
            if len(players) >= 2:
                t1 = players[0].tile_position()
                t2 = players[1].tile_position()
                mx = (t1[0] + t2[0]) // 2
                my = (t1[1] + t2[1]) // 2
                if (
                    0 <= mx < game_map.width
                    and 0 <= my < game_map.height
                    and not game_map.walls[my][mx]
                ):
                    return (mx, my)
            return base_tile

        # idx 3 ve üzeri: oyuncuya yakınken köşe kamplama benzeri davranış
        CLOSE_RADIUS = 4
        dist = manhattan_mesafe(base_tile, my_tile)
        if dist <= CLOSE_RADIUS:
            corner_candidates = [
                (1, game_map.height - 2),
                (game_map.width - 2, game_map.height - 2),
                (1, 1),
                (game_map.width - 2, 1),
            ]
            for (cx, cy) in corner_candidates:
                if (
                    0 <= cx < game_map.width
                    and 0 <= cy < game_map.height
                    and not game_map.walls[cy][cx]
                ):
                    return (cx, cy)
        return base_tile

    def kac(
        self,
        scared_tile: Tuple[int, int],
        game_map: "GameMap",
        max_depth: int = 7,
        min_depth: int = 2,
    ) -> None:
        # kaçış davranışı için bfs ile uzak ve güvenli noktaya rota arıyoruz
        start = self.tile_position()
        q = deque([(start, 0)])
        seen = {start}
        best_target: Optional[Tuple[int, int]] = None
        best_score = -1

        while q:
            (x, y), d = q.popleft()
            if d > max_depth:
                continue

            # belirli derinlikten sonra, duvar ve gate olmayan noktaları aday kabul ediyoruz
            if d >= min_depth:
                if not game_map.walls[y][x] and not game_map.gate[y][x]:
                    dist = manhattan_mesafe((x, y), scared_tile)
                    if dist > best_score:
                        best_score = dist
                        best_target = (x, y)

            # bfs ile etrafı keşfediyoruz
            for dx, dy in DIRECTION_VECTORS:
                nx, ny = x + dx, y + dy
                if 0 <= nx < game_map.width and 0 <= ny < game_map.height:
                    if game_map.walls[ny][nx] or game_map.gate[ny][nx]:
                        continue
                    nxt = (nx, ny)
                    if nxt in seen:
                        continue
                    seen.add(nxt)
                    q.append((nxt, d + 1))

        # uygun kaçış hedefi bulunduysa ona giden yolu hesaplıyoruz
        if best_target:
            self.path = bfs_yolu(start, best_target, game_map)
        else:
            self.path = []

    def yol_takip_et(self, dt: float) -> None:
        # eğer bir path yoksa bulunduğu karenin ortasına gitmeye çalışıyoruz
        if not self.path:
            cx, cy = self.tile_position()
            self.target_pixel = pygame.Vector2(
                cx * TILE_SIZE + TILE_SIZE / 2,
                cy * TILE_SIZE + TILE_SIZE / 2,
            )
        else:
            # pathin ilk elemanı bir sonraki hedef kare
            nxt = self.path[0]
            self.target_tile = nxt
            self.target_pixel = pygame.Vector2(
                nxt[0] * TILE_SIZE + TILE_SIZE / 2,
                nxt[1] * TILE_SIZE + TILE_SIZE / 2,
            )

        if self.target_pixel is None:
            return

        # hedef piksele doğru hareket vektörü ve mesafe
        vec = self.target_pixel - self.position
        d = vec.length()

        # hedefe çok yaklaştıysa oraya snap edip pathin ilk adımını tüketiyoruz
        if d < 0.5:
            self.position.update(self.target_pixel)
            if self.path and self.path[0] == self.tile_position():
                self.path.pop(0)
            self.target_tile = None
            self.target_pixel = None
            return

        travel = self.speed * dt
        # bir frame de hedefe tamamen yetişebiliyorsak direkt hedefe zıplıyoruz
        if travel >= d:
            self.position.update(self.target_pixel)
            if self.path and self.path[0] == self.tile_position():
                self.path.pop(0)
            self.target_tile = None
            self.target_pixel = None
        else:
            # yoksa normalleştirilmiş yön vektörü ile adım adım ilerliyoruz
            self.position += vec.normalize() * travel
