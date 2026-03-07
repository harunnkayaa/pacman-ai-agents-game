from collections import deque
from typing import Iterable, List, Tuple

from game_ayarlar import DIRECTION_VECTORS, GHOST_RELEASE_DELAYS, SOUNDS_DIR

import pygame


def manhattan_mesafe(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    # iki tile arasındaki manhattan mesafesini hesaplıyor
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def en_yakin_mesafe(from_tile: Tuple[int, int], targets: Iterable[Tuple[int, int]]) -> int:
    """from_tile'den hedefler kümesine Manhattan en kısa mesafe."""
    # belli bir kareden verilen hedef kümesine en kısa manhattan mesafesini buluyor
    best = 10 ** 9
    fx, fy = from_tile
    for (tx, ty) in targets:
        d = abs(tx - fx) + abs(ty - fy)
        if d < best:
            best = d
    return best if best != 10 ** 9 else best


def bfs_yolu(
    start: Tuple[int, int],
    goal: Tuple[int, int],
    game_map,
    treat_gate_as_empty: bool = False,
) -> List[Tuple[int, int]]:
    """Game map üzerinde BFS ile bir yol bulur."""
    # start ve goal aynıysa tek karelik yol döndürüyor
    if start == goal:
        return [start]
    # kuyrukta (kare, o ana kadar yol) tutuyoruz
    q = deque([(start, [])])
    seen = {start}
    while q:
        pos, path = q.popleft()
        for dx, dy in DIRECTION_VECTORS:
            nx, ny = pos[0] + dx, pos[1] + dy
            # harita dışına taşma kontrolü
            if nx < 0 or ny < 0 or nx >= game_map.width or ny >= game_map.height:
                continue
            # gate kafes çıkışında bazen boş sayılabiliyor
            blocked = game_map.walls[ny][nx] or (
                game_map.gate[ny][nx] and not treat_gate_as_empty
            )
            if blocked:
                continue
            nxt = (nx, ny)
            if nxt in seen:
                continue
            # hedefe ulaştıysa yolu geri dönüyor
            if nxt == goal:
                return path + [nxt]
            seen.add(nxt)
            q.append((nxt, path + [nxt]))
    # yol bulunamazsa boş liste dönüyor
    return []


def koridor_guvenligi(
    game_map,
    start: Tuple[int, int],
    ghost_tiles: List[Tuple[int, int]],
    max_depth: int = 8,
) -> int:
    """
    Bir noktadan (start) başlayarak BFS ile kaç kareye gidilebildiğini sayar.
    Hayaletlerin bulunduğu hücreler ve hemen çevresi 'tehlikeli' sayılır ve
    duvar gibi davranılır. Düşük değer → dar koridor / çıkmaz sokak / tuzak.
    """
    # bfs ile sınırlı derinlikte serbest dolaşılabilir alanı ölçüp sayı olarak döndürüyor
    q = deque([(start, 0)])
    seen = {start}
    count = 0

    # hayaletlerin bulunduğu yerleri ve hemen çevrelerini 'tehlikeli duvar' say
    danger_zones = set()
    for gx, gy in ghost_tiles:
        danger_zones.add((gx, gy))
        for dx, dy in DIRECTION_VECTORS:
            danger_zones.add((gx + dx, gy + dy))

    while q:
        (x, y), d = q.popleft()
        if d > max_depth:
            continue

        # bu noktaya güvenli şekilde ulaşılabiliyor sayıyoruz
        count += 1

        for dx, dy in DIRECTION_VECTORS:
            nx, ny = x + dx, y + dy
            # harita sınır kontrolü
            if nx < 0 or ny < 0 or nx >= game_map.width or ny >= game_map.height:
                continue

            # duvar, kapı, pen veya hayalet tehdit alanı ise geçilmez
            if (
                game_map.walls[ny][nx]
                or game_map.gate[ny][nx]
                or (nx, ny) in game_map.pen_tiles
                or (nx, ny) in danger_zones
            ):
                continue

            nxt = (nx, ny)
            if nxt in seen:
                continue

            seen.add(nxt)
            q.append((nxt, d + 1))

    # daha küçük count → daha dar ve riskli koridor anlamına geliyor
    return count


def hayaletleri_sifirla(ghosts, now: float) -> None:
    from entities import Ghost  # type: ignore

    # hayaletleri pen içine sıfırlayıp release zamanlarını yeniden ayarlıyor
    for i, g in enumerate(ghosts):
        assert isinstance(g, Ghost)
        g.reset()
        g.release_delay = now + GHOST_RELEASE_DELAYS[i]


def duzeni_normalize_et(layout) -> list[str]:
    # satırlardaki newline karakterlerini temizliyor
    rows = [r.rstrip("\n") for r in layout]
    # en uzun satırın genişliğini buluyor
    maxw = max(len(r) for r in rows)
    # kısa satırların sağını # ile doldurup dikdörtgen bir grid oluşturuyor
    fixed = [(r + "#" * (maxw - len(r))) for r in rows]
    return fixed


# =============================== SES YÖNETİCİSİ ================================== #


class SesYoneticisi:
    def __init__(self) -> None:
        # tüm ses referanslarını başlangıçta none yapıyoruz
        self.pellet = None
        self.power = None
        self.death = None
        self.start = None
        self.game_over = None
        self.ghost_chase = None
        self.power_happy = None

        try:
            # bütün ses dosyalarını yüklemeyi deniyor
            self.load_all_sounds()
            # === volume ayarları ===
            if self.power_happy:
                self.power_happy.set_volume(0.4)
            if self.pellet:
                self.pellet.set_volume(0.4)
            if self.power:
                self.power.set_volume(0.5)
            if self.death:
                self.death.set_volume(0.6)
            if self.game_over:
                self.game_over.set_volume(0.6)
            if self.start:
                self.start.set_volume(0.5)
            if self.ghost_chase:
                self.ghost_chase.set_volume(0.3)
        except Exception:
            # ses sistemi patlarsa oyunu sessiz modda devam ettir
            pass

    def load_sound(self, name: str):
        # verilen dosya ismine göre ses dosyasını yüklemeye çalışıyor
        path = SOUNDS_DIR / name
        if path.exists():
            try:
                return pygame.mixer.Sound(str(path))
            except Exception:
                return None
        return None

    def load_all_sounds(self) -> None:
        # tüm ses efektlerini tek noktadan yüklüyoruz
        self.pellet = self.load_sound("pellet1.wav")
        self.power = self.load_sound("power.mp3")
        self.death = self.load_sound("death.mp3")
        self.start = self.load_sound("start.mp3")
        self.game_over = self.load_sound("game_over.mp3")
        self.ghost_chase = self.load_sound("ghost_chase_loop.mp3")
        self.power_happy = self.load_sound("power_happy_eat_loop.mp3")

    def play_power_happy_loop(self) -> None:
        if self.power_happy:
            # aynı anda yeniden başlatmamak için kanal sayısını kontrol ediyor
            if self.power_happy.get_num_channels() == 0:
                self.power_happy.play(loops=-1)

    def stop_power_happy(self) -> None:
        if self.power_happy:
            self.power_happy.stop()

    def play_pellet(self) -> None:
        # yem yendiğinde çalınan kısa ses efekti
        if self.pellet:
            self.pellet.play()

    def play_power(self) -> None:
        # power pellet alınırken çalan ses
        if self.power:
            self.power.play()

    def play_death(self) -> None:
        # oyuncu öldüğünde çalan ses
        if self.death:
            self.death.play()

    def play_start(self) -> None:
        # yeni tur başladığında çalan ses
        if self.start:
            self.start.play()

    def play_game_over(self) -> None:
        # oyun bittiğinde çalan ses
        if self.game_over:
            self.game_over.play()

    def play_ghost_chase_loop(self) -> None:
        """Pacman hayaletten kaçarken çalan loop sesi."""
        if self.ghost_chase:
            # chase sesi zaten çalıyorsa tekrar tetiklemiyor
            if self.ghost_chase.get_num_channels() == 0:
                self.ghost_chase.play(loops=-1)

    def stop_ghost_chase(self) -> None:
        """Tehlike geçince chase sesini durdur."""
        if self.ghost_chase:
            self.ghost_chase.stop()
