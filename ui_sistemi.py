import sys
import os
from typing import List, Sequence, Tuple

import pygame

from game_ayarlar import (
    TILE_SIZE,  HUD_HEIGHT,  COLOR_BACKGROUND,  COLOR_WALL,  COLOR_WALL_GLOW,  COLOR_PELLET,
    COLOR_POWER, COLOR_GATE,  COLOR_TEXT,  COLOR_HUD,  COLOR_SHADOW,  COLOR_GHOST_FRIGHT,
    COLOR_GHOST_FRIGHT_BLINK, FPS,  GHOST_IMAGES_DIR,
)
from entities import GameMap, Player, Ghost
from oyun_utils import manhattan_mesafe

# Tek ve çift mod skorlarını tutmak için (performans karşılaştırma)
last_human_single_result: dict | None = None
last_ai_single_result: dict | None = None


def peas_text() -> str:
    # agents dersi için pacman ortamının peas tanımını konsola basmak için metin oluşturuyor
    return (
        "PEAS Tanımı:\n"
        "P (Performance):\n"
        "  - Küçük yem toplama (+1 puan)\n"
        "  - Enerji topları (power pellet) toplama (+10 puan)\n"
        "  - Power moddayken hayalet yeme (+20 puan)\n"
        "  - Hayalete yakalanma (-20 puan) ve can kaybı\n"
        "E (Environment):\n"
        "  - Izgara harita: duvarlar (#), yollar, küçük yemler (.), enerji topları (o),\n"
        "    hayalet kafesi (g ve =), iki oyuncu (insan/bilgisayar) ve hayaletler.\n"
        "A (Actuators):\n"
        "  - Pac-Man için dört yönlü hareket (yukarı, aşağı, sol, sağ).\n"
        "  - Hayaletler için BFS tabanlı kovalama / kaçış hareketi.\n"
        "S (Sensors):\n"
        "  - Oyuncuların ve hayaletlerin ızgara konumları,\n"
        "  - Duvar / yol bilgisi,\n"
        "  - Kalan yem ve enerji topları,\n"
        "  - Skor, can ve oyun süresi bilgisi.\n"
        "    \n"
    )


def hayalet_gorsellerini_yukle() -> List[pygame.Surface]:
    # hayalet görsellerinin dosya yollarını toplamak için liste hazırlanıyor
    files = []
    d = GHOST_IMAGES_DIR
    if d.exists():
        for n in os.listdir(d):
            # sadece resim uzantılı dosyalar alınıyor
            if n.lower().endswith((".png", ".jpg", ".jpeg")):
                files.append(d / n)

    images: List[pygame.Surface] = []
    # en fazla 4 hayalet görselini yükleyip tile boyutuna ölçekliyoruz
    for p in sorted(files)[:4]:
        img = pygame.image.load(str(p)).convert_alpha()
        images.append(pygame.transform.smoothscale(img, (TILE_SIZE, TILE_SIZE)))

    # eğer yeterli hayalet görseli yoksa basit kırmızı daire ile placeholder üret
    while len(images) < 4:
        surf = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        pygame.draw.circle(
            surf,
            (255, 0, 0, 255),
            (TILE_SIZE // 2, TILE_SIZE // 2),
            TILE_SIZE // 2 - 2,
        )
        images.append(surf)
    # tam olarak 4 tane döndürüyoruz
    return images[:4]


def tahta_ciz(
    surface: pygame.Surface,
    game_map: GameMap,
    players: Sequence[Player],
    ghosts: Sequence[Ghost],
    now: float,
    power_end: float,
) -> None:
    # oyun alanını arkaplan rengi ile dolduruyor
    surface.fill(COLOR_BACKGROUND, pygame.Rect(0, 0, game_map.pixel_width, game_map.pixel_height))

    wall_line_width = 6
    half = TILE_SIZE // 2

    # grid karesinin piksel merkezini hesaplayan yardımcı fonksiyon
    def cell_center(x: int, y: int) -> Tuple[int, int]:
        return (x * TILE_SIZE + half, y * TILE_SIZE + half)

    # duvarların arkasına hafif glow efekti için kare kare boyuyoruz
    glow_rect = pygame.Rect(0, 0, TILE_SIZE, TILE_SIZE)
    for y in range(game_map.height):
        for x in range(game_map.width):
            if game_map.walls[y][x]:
                glow_rect.topleft = (x * TILE_SIZE, y * TILE_SIZE)
                pygame.draw.rect(surface, COLOR_WALL_GLOW, glow_rect)

    # komşu duvar kareleri arasında çizgiler çekip klasik pacman tarzı duvar şekli veriyoruz
    for y in range(game_map.height):
        for x in range(game_map.width):
            if not game_map.walls[y][x]:
                continue
            cx, cy = cell_center(x, y)

            if y > 0 and game_map.walls[y - 1][x]:
                nx, ny = cell_center(x, y - 1)
                pygame.draw.line(surface, COLOR_WALL, (cx, cy), (nx, ny), wall_line_width)
            if y < game_map.height - 1 and game_map.walls[y + 1][x]:
                nx, ny = cell_center(x, y + 1)
                pygame.draw.line(surface, COLOR_WALL, (cx, cy), (nx, ny), wall_line_width)
            if x > 0 and game_map.walls[y][x - 1]:
                nx, ny = cell_center(x - 1, y)
                pygame.draw.line(surface, COLOR_WALL, (cx, cy), (nx, ny), wall_line_width)
            if x < game_map.width - 1 and game_map.walls[y][x + 1]:
                nx, ny = cell_center(x + 1, y)
                pygame.draw.line(surface, COLOR_WALL, (cx, cy), (nx, ny), wall_line_width)

            # köşelere minik disk koyup duvar birleşimlerini yumuşatıyoruz
            pygame.draw.circle(surface, COLOR_WALL, (cx, cy), wall_line_width // 2)

    # küçük yem pellet noktaları çiziliyor
    for (px, py) in game_map.pellets:
        center = (px * TILE_SIZE + TILE_SIZE // 2, py * TILE_SIZE + TILE_SIZE // 2)
        pygame.draw.circle(surface, COLOR_PELLET, center, 4)

    # power pelletler içi boş daire ve içte dolu daire olarak çiziliyor
    for (px, py) in game_map.powers:
        center = (px * TILE_SIZE + TILE_SIZE // 2, py * TILE_SIZE + TILE_SIZE // 2)
        pygame.draw.circle(surface, COLOR_POWER, center, 7, width=2)
        pygame.draw.circle(surface, COLOR_POWER, center, 3)

    # oyuncuların çizimi, iki oyuncu aynı karedeyse dikey offset ile üst üste binmeyi biraz açıyoruz
    for i, p in enumerate(players):
        offset_y = 0
        if len(players) == 2:
            other = players[1 - i]
            if p.tile_position() == other.tile_position():
                offset_y = -3 if i == 0 else 3

        pygame.draw.circle(
            surface,
            p.color,
            (int(p.position.x), int(p.position.y + offset_y)),
            TILE_SIZE // 2 - 3,
        )

    # gate çizgileri (hayalet kafesi kapısı) yatay çizgi ile gösteriliyor
    for y in range(game_map.height):
        for x in range(game_map.width):
            if game_map.gate[y][x]:
                rect = pygame.Rect(
                    x * TILE_SIZE,
                    y * TILE_SIZE + TILE_SIZE // 2 - 2,
                    TILE_SIZE,
                    4,
                )
                pygame.draw.rect(surface, COLOR_GATE, rect)

    # power mod aktif mi ve bitmeye ne kadar kaldı bilgisi
    power_active = power_end > now
    remaining = max(0.0, power_end - now)
    # sürenin son 2 saniyesinde hayaletleri yanıp sönerek blinky yapmak için blink flag
    blink = power_active and remaining <= 2.0 and (int(now * 6) % 2 == 0)

    # hayalet çizimleri, power modda renkleri tintleniyor
    for g in ghosts:
        pos = (int(g.position.x - TILE_SIZE / 2), int(g.position.y - TILE_SIZE / 2))

        if power_active:
            base = g.image
            img = base.copy()
            tint_color = COLOR_GHOST_FRIGHT_BLINK if blink else COLOR_GHOST_FRIGHT

            overlay = pygame.Surface(img.get_size(), pygame.SRCALPHA)
            overlay.fill((*tint_color, 140))
            img.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            surface.blit(img, pos)
        else:
            surface.blit(g.image, pos)


def hud_ciz(
    surface: pygame.Surface,
    game_map: GameMap,
    players: Sequence[Player],
    font: pygame.font.Font,
    sub_font: pygame.font.Font,
    mode_label: str,
    elapsed_time: float,
) -> None:
    # oyun alanının altına hud barını çiziyor
    hud_rect = pygame.Rect(0, game_map.pixel_height, game_map.pixel_width, HUD_HEIGHT)
    surface.fill(COLOR_HUD, hud_rect)
    # her oyuncu için isim, skor ve can sayısını tek satırda birleştiriyoruz
    score_text = "   ".join(f"{p.name}: {int(p.score)}  |  ♥{p.lives}" for p in players)

    score_surface = font.render(score_text, True, COLOR_TEXT)
    score_rect = score_surface.get_rect(midtop=hud_rect.midtop)
    score_rect.move_ip(0, 6)
    surface.blit(score_surface, score_rect)

    # seçili modun etiketi hud alt kısmında gösteriliyor
    mode_surface = sub_font.render(mode_label, True, COLOR_TEXT)
    mode_rect = mode_surface.get_rect(midbottom=hud_rect.midbottom)
    mode_rect.move_ip(0, -8)
    surface.blit(mode_surface, mode_rect)

    # geçen süreyi saniye cinsinden yazdırıyoruz
    time_text = f"Süre: {elapsed_time:5.1f} sn"
    time_surface = sub_font.render(time_text, True, COLOR_TEXT)
    time_rect = time_surface.get_rect(midright=(game_map.pixel_width - 10, hud_rect.centery))
    surface.blit(time_surface, time_rect)


def performans_karsilastir_goster(
    surface: pygame.Surface,
    clock: pygame.time.Clock,
    game_map: GameMap,
    font: pygame.font.Font,
    sub_font: pygame.font.Font,
) -> None:
    # global skor kayıtlarına erişmek için global değişkenler
    global last_human_single_result, last_ai_single_result

    # arkaplanı temizliyoruz
    surface.fill(COLOR_BACKGROUND)

    # iki moddan da sonuç yoksa uyarı mesajı gösterip herhangi bir tuşla menüye dönüyoruz
    if last_human_single_result is None or last_ai_single_result is None:
        msg = "Karşılaştırma için önce hem 'Oyuncu (tek)' hem 'Bilgisayar (tek)' modlarını oynayın."
        title = font.render("Performans Karşılaştırma", True, COLOR_TEXT)
        text = sub_font.render(msg, True, COLOR_TEXT)

        surface.blit(
            title,
            title.get_rect(center=(game_map.pixel_width // 2, game_map.pixel_height // 2 - 40)),
        )
        surface.blit(
            text,
            text.get_rect(center=(game_map.pixel_width // 2, game_map.pixel_height // 2 + 10)),
        )

        hint = sub_font.render("Herhangi bir tuş: Menüye dön", True, COLOR_TEXT)
        surface.blit(
            hint,
            hint.get_rect(center=(game_map.pixel_width // 2, game_map.pixel_height // 2 + 60)),
        )

        pygame.display.flip()

        # kullanıcı bir tuşa basana kadar bekleme döngüsü
        waiting = True
        while waiting:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit(0)
                if e.type == pygame.KEYDOWN:
                    waiting = False
            clock.tick(FPS)
        return

    # human ve ai tek oyuncu sonuçlarını unpack ediyoruz
    h = last_human_single_result
    a = last_ai_single_result

    h_score = h["score"]
    a_score = a["score"]
    h_dur = h["duration"]
    a_dur = a["duration"]

    # önce skor, eşitse süreye göre kazananı belirliyoruz
    if h_score > a_score:
        winner_text = "Kazanan: İnsan (tek oyuncu)"
    elif a_score > h_score:
        winner_text = "Kazanan: Bilgisayar (tek oyuncu)"
    else:
        if h_dur < a_dur:
            winner_text = "Kazanan: İnsan (tek oyuncu) (süre daha kısa)"
        elif a_dur < h_dur:
            winner_text = "Kazanan: Bilgisayar (tek oyuncu) (süre daha kısa)"
        else:
            winner_text = "Berabere!"

    surface.fill(COLOR_BACKGROUND)
    title = font.render("İnsan vs Bilgisayar (Tek Oyuncu Karşılaştırma)", True, COLOR_TEXT)
    surface.blit(
        title,
        title.get_rect(center=(game_map.pixel_width // 2, game_map.pixel_height // 2 - 100)),
    )

    # insan ve ai skor/süre bilgilerini ayrı satırlarda gösteriyoruz
    line1 = sub_font.render(
        f"İnsan → Skor: {int(h_score)}, Süre: {h_dur:5.1f} sn",
        True,
        COLOR_TEXT,
    )
    line2 = sub_font.render(
        f"Bilgisayar → Skor: {int(a_score)}, Süre: {a_dur:5.1f} sn",
        True,
        COLOR_TEXT,
    )
    line3 = sub_font.render(winner_text, True, COLOR_TEXT)
    hint = sub_font.render("Herhangi bir tuş: Menüye dön", True, COLOR_TEXT)

    surface.blit(
        line1,
        line1.get_rect(center=(game_map.pixel_width // 2, game_map.pixel_height // 2 - 30)),
    )
    surface.blit(
        line2,
        line2.get_rect(center=(game_map.pixel_width // 2, game_map.pixel_height // 2 + 5)),
    )
    surface.blit(
        line3,
        line3.get_rect(center=(game_map.pixel_width // 2, game_map.pixel_height // 2 + 50)),
    )
    surface.blit(
        hint,
        hint.get_rect(center=(game_map.pixel_width // 2, game_map.pixel_height // 2 + 100)),
    )

    pygame.display.flip()

    # ekrandan çıkmak için herhangi bir tuşa basılmasını bekliyoruz
    waiting = True
    while waiting:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)
            if e.type == pygame.KEYDOWN:
                waiting = False
        clock.tick(FPS)


def mod_menu_calistir(
    surface: pygame.Surface,
    clock: pygame.time.Clock,
    game_map: GameMap,
    font: pygame.font.Font,
    sub_font: pygame.font.Font,
) -> str:
    from ui_sistemi import performans_karsilastir_goster, peas_text  # self import için

    # ana menü döngüsü, kullanıcı mod seçeneği yapana kadar dönüyor
    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)
            if e.type == pygame.KEYDOWN:
                # tek oyuncu insan modu
                if e.key == pygame.K_1:
                    return "human_single"
                # tek oyuncu ai modu
                if e.key == pygame.K_2:
                    return "ai_single"
                # insan vs ai
                if e.key == pygame.K_3:
                    return "human_vs_ai"
                # ai vs ai demo
                if e.key == pygame.K_4:
                    return "ai_vs_ai"
                # performans karşılaştırma ekranını aç
                if e.key == pygame.K_c or e.key == pygame.K_C:
                    performans_karsilastir_goster(surface, clock, game_map, font, sub_font)
                # peas tanımını konsola yazdır
                if e.key == pygame.K_p:
                    print(peas_text())
                # esc ile tamamen çık
                if e.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit(0)

        # menü arkaplanını boyuyoruz
        surface.fill(COLOR_BACKGROUND)
        title = font.render("Pacman", True, COLOR_TEXT)

        # menü seçenekleri yazıları
        line1 = sub_font.render("1: Oyuncu (tek oyuncu)", True, COLOR_TEXT)
        line2 = sub_font.render("2: Bilgisayar (tek oyuncu)", True, COLOR_TEXT)
        line3 = sub_font.render("3: Oyuncu + Bilgisayar (2 oyuncu)", True, COLOR_TEXT)
        line4 = sub_font.render("4: Bilgisayar vs Bilgisayar (demo)", True, COLOR_TEXT)
        line5 = sub_font.render("C: İnsan vs Bilgisayar performans karşılaştırma", True, COLOR_TEXT)
        hint = sub_font.render("P: PEAS Tanımı (konsola)  |  ESC: Çıkış", True, COLOR_TEXT)

        # başlık ve seçeneklerin ekranda konumlandırılması
        surface.blit(
            title,
            title.get_rect(center=(game_map.pixel_width // 2, game_map.pixel_height // 4)),
        )
        surface.blit(
            line1,
            line1.get_rect(center=(game_map.pixel_width // 2, game_map.pixel_height // 2 - 60)),
        )
        surface.blit(
            line2,
            line2.get_rect(center=(game_map.pixel_width // 2, game_map.pixel_height // 2 - 30)),
        )
        surface.blit(
            line3,
            line3.get_rect(center=(game_map.pixel_width // 2, game_map.pixel_height // 2)),
        )
        surface.blit(
            line4,
            line4.get_rect(center=(game_map.pixel_width // 2, game_map.pixel_height // 2 + 30)),
        )
        surface.blit(
            line5,
            line5.get_rect(center=(game_map.pixel_width // 2, game_map.pixel_height // 2 + 60)),
        )
        surface.blit(
            hint,
            hint.get_rect(center=(game_map.pixel_width // 2, game_map.pixel_height // 2 + 100)),
        )

        pygame.display.flip()
        clock.tick(FPS)


def oyun_bitti_ekrani_goster(
    surface: pygame.Surface,
    clock: pygame.time.Clock,
    game_map: GameMap,
    players: Sequence[Player],
    fonts,
    duration: float,
    sounds,
) -> str:
    font, sub_font = fonts

    # tek oyuncu veya boş liste durumunda bitiş mesajını basit tutuyoruz
    if len(players) <= 1:
        p = players[0] if players else None
        if p is not None:
            headline_text = f"Oyun bitti! {p.name} skoru: {int(p.score)}"
        else:
            headline_text = "Oyun bitti!"

        lines = [
            f"Toplam süre: {duration:5.1f} sn",
            "R: Aynı modda tekrar oyna",
            "M: Moda geri dön",
            "ESC: Çık",
        ]
    else:
        # çok oyunculu durumda kazananı belirlemek için main_oyun içinden fonksiyon çağırıyoruz
        from main_oyun import kazanan_belirle  # circular için burada import

        winner = kazanan_belirle(players)
        headline_text = "Berabere!" if winner is None else f"Kazanan: {winner.name}"
        lines = [
            f"Toplam süre: {duration:5.1f} sn",
            "R: Aynı modda tekrar oyna",
            "M: Moda geri dön",
            "ESC: Çık",
        ]

    # oyun bittiğinde ilgili ses efektini çalıyoruz
    if sounds:
        sounds.play_game_over()

    # oyun sonu ekranı olay döngüsü, kullanıcı seçim yapana kadar dönüyor
    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_r:
                    return "restart"
                if e.key == pygame.K_m:
                    return "menu"
                if e.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit(0)

        # arkada son oyun durumunu tekrar çiziyoruz
        now = pygame.time.get_ticks() / 1000.0
        tahta_ciz(surface, game_map, players, [], now, 0.0)
        hud_ciz(surface, game_map, players, font, sub_font, "Oyun bitti", duration)

        # üstüne yarı saydam gölge overlay bırakıyoruz
        overlay = pygame.Surface((game_map.pixel_width, game_map.pixel_height), pygame.SRCALPHA)
        overlay.fill(COLOR_SHADOW)
        surface.blit(overlay, (0, 0))

        # başlık (kazanan / skor) yazısı
        headline = font.render(headline_text, True, COLOR_TEXT)
        surface.blit(
            headline,
            headline.get_rect(center=(game_map.pixel_width // 2, game_map.pixel_height // 2 - 60)),
        )

        # alt satırlara yönerge metinlerini yazıyoruz
        for i, line in enumerate(lines):
            t = sub_font.render(line, True, COLOR_TEXT)
            surface.blit(
                t,
                t.get_rect(
                    center=(
                        game_map.pixel_width // 2,
                        game_map.pixel_height // 2 + 10 + 28 * i,
                    )
                ),
            )

        pygame.display.flip()
        clock.tick(FPS)
