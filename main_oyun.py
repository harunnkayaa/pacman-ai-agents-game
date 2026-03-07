import sys
from typing import List, Sequence, Tuple

import pygame

from game_ayarlar import (
    TILE_SIZE,
    HUD_HEIGHT,
    FPS,
    LEVEL_LAYOUT,
    READY_DURATION,
    GHOST_RELEASE_DELAYS,
    COLOR_PLAYER_ONE,
    COLOR_PLAYER_TWO,
    GHOST_EAT_SCORE,
    PLAYER_COLLISION_PENALTY

)
from entities import GameMap, Player, Ghost, GhostState
from oyun_utils import SesYoneticisi, hayaletleri_sifirla, duzeni_normalize_et
from ui_sistemi import (
    tahta_ciz,
    hud_ciz,
    mod_menu_calistir,
    oyun_bitti_ekrani_goster,
    hayalet_gorsellerini_yukle,
)
import ui_sistemi


def oyunculari_olustur(game_map: GameMap, mode: str) -> List[Player]:
    # oyuncu 1 için yön tuşları ile kontrol seti
    controls_p1 = (
        (pygame.K_UP, (0, -1)),
        (pygame.K_LEFT, (-1, 0)),
        (pygame.K_DOWN, (0, 1)),
        (pygame.K_RIGHT, (1, 0)),
    )
    # oyuncu 2 için wasd ile kontrol seti
    controls_p2 = (
        (pygame.K_w, (0, -1)),
        (pygame.K_a, (-1, 0)),
        (pygame.K_s, (0, 1)),
        (pygame.K_d, (1, 0)),
    )

    # tek oyuncu insan modu için oyuncu nesnesi oluşturuluyor
    if mode == "human_single":
        p = Player("Oyuncu", COLOR_PLAYER_ONE, game_map.player_starts["p1"], controls_p1, is_ai=False)
        return [p]

    # tek oyuncu bilgisayar modu için ai oyuncu oluşturuluyor
    if mode == "ai_single":
        p = Player("Bilgisayar", COLOR_PLAYER_ONE, game_map.player_starts["p1"], controls_p1, is_ai=True)
        return [p]

    # insan vs ai modu için iki oyuncu ayarlanıyor
    if mode == "human_vs_ai":
        p1 = Player("Oyuncu", COLOR_PLAYER_ONE, game_map.player_starts["p1"], controls_p1, is_ai=False)
        p2 = Player("Bilgisayar", COLOR_PLAYER_TWO, game_map.player_starts["p2"], controls_p2, is_ai=True)
        return [p1, p2]

    # ai vs ai modu için iki bilgisayar oyuncusu oluşturuluyor
    if mode == "ai_vs_ai":
        p1 = Player("Bilgisayar 1", COLOR_PLAYER_ONE, game_map.player_starts["p1"], controls_p1, is_ai=True)
        p2 = Player("Bilgisayar 2", COLOR_PLAYER_TWO, game_map.player_starts["p2"], controls_p2, is_ai=True)
        return [p1, p2]

    # tanımsız mod gelirse default olarak insan tek oyuncu başlatılıyor
    p = Player("Oyuncu", COLOR_PLAYER_ONE, game_map.player_starts["p1"], controls_p1, is_ai=False)
    return [p]


def hayaletleri_olustur(game_map: GameMap, imgs: List[pygame.Surface]) -> Tuple[List[Ghost], Tuple[int, int]]:
    # hayalet kafesi için haritadaki pen kareleri alınıyor
    pen = sorted(game_map.pen_tiles)
    # eğer pen alanları yetersizse ortadan küçük bir pen alanı oluşturuluyor
    if len(pen) < 8:
        cx, cy = game_map.width // 2, game_map.height // 2
        pen = [
            (cx - 1, cy),
            (cx, cy),
            (cx + 1, cy),
            (cx, cy + 1),
            (cx - 1, cy + 1),
            (cx + 1, cy + 1),
        ]
    # dört hayalet için doğacağı kareler seçiliyor
    spawns = [pen[1], pen[3], pen[5], pen[7] if len(pen) > 7 else pen[-1]]
    ghosts: List[Ghost] = []
    # her hayalet için nesne oluşturuluyor ve hızları hafifçe farklılaştırılıyor
    for i in range(4):
        g = Ghost(imgs[i], spawns[i % len(spawns)], GHOST_RELEASE_DELAYS[i], behavior_index=i)
        g.speed = g.speed * (0.95 + 0.03 * i)
        g.base_speed = g.speed
        ghosts.append(g)

    # gate kareleri bulunup hayaletlerin çıkışı için hedef belirleniyor
    gate_tiles = [
        (x, y)
        for y in range(game_map.height)
        for x in range(game_map.width)
        if game_map.gate[y][x]
    ]
    if not gate_tiles:
        gate_target = spawns[0]
    else:
        gate_tiles.sort()
        gate_target = gate_tiles[len(gate_tiles) // 2]
    return ghosts, gate_target


def kazanan_belirle(players: Sequence[Player]):
    # oyuncu yoksa kazanan yok
    if not players:
        return None
    # tek oyuncu varsa otomatik kazanan o
    if len(players) == 1:
        return players[0]

    # iki oyuncu skorlarına göre karşılaştırılıyor
    p1, p2 = players[0], players[1]

    if p1.score > p2.score:
        return p1
    if p2.score > p1.score:
        return p2

    # skor eşitse son puan alma zamanına göre karar veriliyor
    t1, t2 = p1.last_score_time, p2.last_score_time

    if t1 <= 0.0 and t2 <= 0.0:
        return None

    if 0.0 < t1 < t2:
        return p1
    if 0.0 < t2 < t1:
        return p2

    return None


def mod_etiketi(mode: str) -> str:
    # seçilen moda göre hud üzerinde görünecek metin hazırlanıyor
    if mode == "human_single":
        return "Mod: Tek Oyuncu (İnsan)"
    if mode == "ai_single":
        return "Mod: Tek Oyuncu (Bilgisayar)"
    if mode == "human_vs_ai":
        return "Mod: Oyuncu + Bilgisayar"
    if mode == "ai_vs_ai":
        return "Mod: Bilgisayar vs Bilgisayar"
    return "Mod: Bilinmiyor"


def tur_oyna(
    surface: pygame.Surface,
    clock: pygame.time.Clock,
    game_map: GameMap,
    players: Sequence[Player],
    ghosts: Sequence[Ghost],
    gate_exit: Tuple[int, int],
    fonts,
    mode_tag: str,
    sounds: SesYoneticisi | None,
) -> float:
    # hud ve ara yazılar için kullanılan fontlar ayrılıyor
    font, sub_font = fonts
    running = True
    # tur başlangıç zamanı kaydediliyor
    start_time = pygame.time.get_ticks() / 1000.0
    round_start_time = start_time

    # oyuncu öldüğünde kaç saniye beklenip yeniden doğacağı
    death_pause = 1.2

    # oyun başı sesi çalınıyor
    if sounds:
        sounds.play_start()

    # ana tur döngüsü
    while running:
        now = pygame.time.get_ticks() / 1000.0
        dt = clock.tick(FPS) / 1000.0

        # olaylar işleniyor
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit(0)

        # ready yazısı ekranda kalacağı süre kontrolü
        ready_active = (now - start_time <= READY_DURATION)

        # klavye durumu alınıyor
        pressed = pygame.key.get_pressed()
        # ready bitene kadar oyuncu girişleri işlenmiyor
        if not ready_active:
            for p in players:
                p.process_input(pressed)

        # ready süresi bittiyse oyuncular ve hayaletler güncelleniyor
        if not ready_active:
            for p in players:
                p.update(dt, game_map, now, ghosts, sounds)
            for g in ghosts:
                g.update(dt, game_map, players, now, gate_exit)

        # çarpışma kontrolü ve can/sayı güncellemeleri
        if not ready_active:
            for g in ghosts:
                gt = g.tile_position()
                for p in players:
                    if p.tile_position() != gt:
                        continue

                    # oyuncu güç modundaysa hayaleti yiyip puan alıyor
                    if p.power_mode_until > now:
                        p.score += GHOST_EAT_SCORE
                        p.last_score_time = now
                        if sounds:
                            sounds.play_death()
                        g.reset()
                        g.release_delay = now + 3.0
                    else:
                        # sadece kovalamaca modundaki hayaletler oyuncuya zarar veriyor
                        if g.state != GhostState.CHASE:
                            continue

                        # oyuncunun skoru ve canı azaltılıyor
                        p.score = max(0, p.score - PLAYER_COLLISION_PENALTY)
                        p.lives -= 1
                        if sounds:
                            sounds.play_death()

                        # oyuncu başlangıç karesine sıfırlanıyor
                        p.position.update(
                            p.start_tile[0] * TILE_SIZE + TILE_SIZE / 2,
                            p.start_tile[1] * TILE_SIZE + TILE_SIZE / 2,
                        )
                        p.direction.update(0, 0)
                        p.next_direction.update(0, 0)
                        p.target_tile = None
                        p.target_pixel = None

                        # tüm hayaletler başlangıç haline getiriliyor
                        hayaletleri_sifirla(ghosts, now)
                        # ölüm sonrası kısa ready bekleme süresi başlatılıyor
                        start_time = now + death_pause

            # herhangi bir oyuncunun canı bittiyse tur sona eriyor
            if any(p.lives <= 0 for p in players):
                running = False

        # tur boyunca geçen toplam süre hesaplanıyor
        elapsed_round_time = now - round_start_time

        # oyuncular arasında en geç power mode bitiş zamanı alınıyor
        power_end = max((p.power_mode_until for p in players), default=0.0)

        # ses mantığı: power mode ve danger durumuna göre looplar kontrol ediliyor
        if sounds:
            power_active = power_end > now

            if power_active:
                sounds.play_power_happy_loop()
                sounds.stop_ghost_chase()
            else:
                sounds.stop_power_happy()

                danger_active = False
                if ghosts and any(g.state == GhostState.CHASE for g in ghosts):
                    danger_active = True

                if danger_active:
                    sounds.play_ghost_chase_loop()
                else:
                    sounds.stop_ghost_chase()

        # oyun tahtası ve hud her frame çiziliyor
        tahta_ciz(surface, game_map, players, ghosts, now, power_end)
        hud_ciz(surface, game_map, players, font, sub_font, mode_tag, elapsed_round_time)

        # ready overlay görüntüsü ve yazısı
        if ready_active:
            overlay = pygame.Surface((game_map.pixel_width, game_map.pixel_height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 80))
            surface.blit(overlay, (0, 0))
            ready_font = pygame.font.Font(None, 48)
            r = ready_font.render("READY!", True, (255, 220, 0))
            surface.blit(
                r,
                r.get_rect(center=(game_map.pixel_width // 2, game_map.pixel_height // 2 + 10)),
            )

        pygame.display.flip()

        # tüm pellet ve powerlar bitince tur sona eriyor
        if not game_map.pellets and not game_map.powers:
            running = False

    round_end_time = pygame.time.get_ticks() / 1000.0
    # turun toplam süresi döndürülüyor
    return round_end_time - round_start_time


def main() -> None:
    # pygame ve ses sistemi başlatılıyor
    pygame.init()
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init()
    except Exception:
        print("Uyarı: Ses sistemi başlatılamadı, oyun sessiz çalışacak.")

    # seviye düzeni normalize edilip game_map oluşturuluyor
    norm_layout = duzeni_normalize_et(LEVEL_LAYOUT)
    game_map = GameMap(norm_layout)

    # ekran boyutu haritanın piksel boyutuna ve hud yüksekliğine göre ayarlanıyor
    screen = pygame.display.set_mode(
        (game_map.pixel_width, game_map.pixel_height + HUD_HEIGHT),
        pygame.SCALED | pygame.DOUBLEBUF,
    )
    pygame.display.set_caption("Pacman")
    clock = pygame.time.Clock()

    # başlık ve hud yazıları için fontlar yükleniyor
    title_font = pygame.font.Font(None, 42)
    hud_font = pygame.font.Font(None, 28)
    sub_font = pygame.font.Font(None, 22)

    # hayalet görselleri ve ses yöneticisi hazırlanıyor
    ghost_imgs = hayalet_gorsellerini_yukle()
    sounds = SesYoneticisi()

    # başlangıçta mod seçimi menüsü gösteriliyor
    mode = mod_menu_calistir(screen, clock, game_map, title_font, sub_font)

    # oyun bitene kadar tur döngüsü
    while True:
        # her tur başında harita ve oyuncu durumu sıfırlanıyor
        game_map.reset()
        players = oyunculari_olustur(game_map, mode)
        ghosts, gate_exit = hayaletleri_olustur(game_map, ghost_imgs)

        # tek tur oynanıyor ve süresi alınıyor
        duration = tur_oyna(
            screen,
            clock,
            game_map,
            players,
            ghosts,
            gate_exit,
            (hud_font, sub_font),
            mod_etiketi(mode),
            sounds,
        )

        # son skorlar ui modülü üzerinden istatistik için tutuluyor
        if mode == "human_single" and players:
            p = players[0]
            ui_sistemi.last_human_single_result = {
                "name": p.name,
                "score": float(p.score),
                "duration": float(duration),
            }
        if mode == "ai_single" and players:
            p = players[0]
            ui_sistemi.last_ai_single_result = {
                "name": p.name,
                "score": float(p.score),
                "duration": float(duration),
            }

        # oyun bitti ekranı ile oyuncudan sonraki adım isteniyor
        decision = oyun_bitti_ekrani_goster(
            screen,
            clock,
            game_map,
            players,
            (hud_font, sub_font),
            duration,
            sounds,
        )
        # restart seçilirse aynı modda yeni tura geçiliyor
        if decision == "restart":
            continue
        # menu seçilirse mod menüsüne geri dönülüyor
        if decision == "menu":
            mode = mod_menu_calistir(screen, clock, game_map, title_font, sub_font)
            continue
        # farklı bir şeyse tamamen oyundan çıkılıyor
        break

    pygame.quit()


if __name__ == "__main__":
    # dosya direkt çalıştırıldığında main fonksiyonu çağrılıyor
    main()
