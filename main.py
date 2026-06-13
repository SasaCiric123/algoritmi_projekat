import pygame
import sys

from game_state import GameState
from ai import AIPlayer

pygame.init()
pygame.font.init()

WIDTH, HEIGHT = 800, 600
BOARD_SIZE = 600
SQUARE_SIZE = BOARD_SIZE // 8

WIN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Царев друм: Српске епске даме")

CRNA = (0, 0, 0)
BELA = (255, 255, 255)
DRVO_SVETLO = (235, 210, 175)
DRVO_TAMNO = (139, 69, 19)
BRAZDA_BOJA = (218, 165, 32)
INFO_POZA = (40, 40, 40)
SELEKTOVANO = (0, 255, 0)
MOGUCI_POTEZ = (0, 0, 255)
OKLOP_BOJA = (100, 180, 255)
VINO_BOJA = (180, 0, 180)
TOPUZ_BOJA = (255, 50, 50)
SARAC_BOJA = (255, 140, 0)

FONT_GL = pygame.font.SysFont('Arial', 22, bold=True)
FONT_ML = pygame.font.SysFont('Arial', 16)
FONT_NAZ = pygame.font.SysFont('Times New Roman', 28, bold=True)

UNDO = pygame.Rect(BOARD_SIZE + 15, HEIGHT - 80, 80, 35)
REDO = pygame.Rect(BOARD_SIZE + 105, HEIGHT - 80, 80, 35)
GORNJA_RECT = pygame.Rect(BOARD_SIZE // 2 - 175, HEIGHT // 2 - 190, 350, 160)
DONJA_RECT = pygame.Rect(BOARD_SIZE // 2 - 175, HEIGHT // 2 + 10, 350, 160)
REPLAY_RECT = pygame.Rect(BOARD_SIZE // 2 - 110, HEIGHT // 2 + 50, 220, 40)

FPS = 60


def draw_board(win, game_state):
    for row in range(8):
        for col in range(8):
            color = DRVO_SVETLO if (row + col) % 2 == 0 else DRVO_TAMNO
            pygame.draw.rect(win, color, (col * SQUARE_SIZE, row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))
    for idx in (12, 19):
        rc = game_state.board.index_to_row_col(idx)
        if rc:
            r, c = rc
            pygame.draw.rect(win, BRAZDA_BOJA,
                             (c * SQUARE_SIZE + 2, r * SQUARE_SIZE + 2, SQUARE_SIZE - 4, SQUARE_SIZE - 4), 3)


def draw_pieces(win, game_state, selected, valid_moves):
    board = game_state.board
    oklop_targets = game_state.get_oklop_targets()
    vino_targets = set()
    for color in ("W", "B"):
        if game_state.vino_trajanje[color] > 0 and game_state.vino_figura[color] is not None:
            vino_targets.add(game_state.vino_figura[color])

    for idx in range(32):
        piece = board.state[idx]
        if not piece:
            continue
        row, col = board.index_to_row_col(idx)
        center_x = col * SQUARE_SIZE + SQUARE_SIZE // 2
        center_y = row * SQUARE_SIZE + SQUARE_SIZE // 2
        radius = SQUARE_SIZE // 2 - 8
        fill = BELA if board.get_piece_color(piece) == "W" else CRNA
        text_color = CRNA if fill == BELA else BELA

        pygame.draw.circle(win, fill, (center_x, center_y), radius)
        pygame.draw.circle(win, (128, 128, 128), (center_x, center_y), radius, 2)

        if idx in game_state.inventory["W"]["topuz"] or idx in game_state.inventory["B"]["topuz"]:
            pygame.draw.circle(win, TOPUZ_BOJA, (center_x, center_y), radius + 5, 2)
        if idx in game_state.inventory["W"]["sarac"] or idx in game_state.inventory["B"]["sarac"]:
            pygame.draw.circle(win, SARAC_BOJA, (center_x, center_y), radius + 7, 2)

        if idx in oklop_targets:
            pygame.draw.circle(win, OKLOP_BOJA, (center_x, center_y), radius + 5, 3)
        if idx in vino_targets:
            pygame.draw.circle(win, VINO_BOJA, (center_x, center_y), radius + 5, 3)
        if idx == selected:
            pygame.draw.circle(win, SELEKTOVANO, (center_x, center_y), radius + 3, 3)

        letter = "J" if "_J" in piece else ("K" if "_K" in piece else "M")
        surf = FONT_GL.render(letter, True, text_color)
        win.blit(surf, surf.get_rect(center=(center_x, center_y)))

    drawn = set()
    for move in valid_moves:
        end_index = move[2] if move[0] == 'quiet' else move[3]
        if end_index in drawn:
            continue
        drawn.add(end_index)
        r, c = board.index_to_row_col(end_index)
        pygame.draw.circle(win, MOGUCI_POTEZ, (c * SQUARE_SIZE + SQUARE_SIZE // 2, r * SQUARE_SIZE + SQUARE_SIZE // 2),
                           12)


def draw_info(win, game_state):
    pygame.draw.rect(win, INFO_POZA, (BOARD_SIZE, 0, WIDTH - BOARD_SIZE, HEIGHT))
    win.blit(FONT_NAZ.render("Царев Друм", True, BRAZDA_BOJA), (BOARD_SIZE + 20, 20))

    if game_state.game_over:
        if game_state.winner == "W":
            status = "Крај: Победа (Бели)"
        elif game_state.winner == "B":
            status = "Крај: Победа (Црни)"
        else:
            status = "Крај: Нерешено(40 потеза)"
    else:
        status = "Твој потез (Бели)" if game_state.current_player == "W" else "Противник размишља..."
    win.blit(FONT_GL.render(status, True, BELA), (BOARD_SIZE + 20, 80))

    brojac_boja = (255, 255, 255) if game_state.halfmove_clock < 30 else (255, 100, 100)
    brojac_tekst = f"Потези до мира: {game_state.halfmove_clock}/40"
    win.blit(FONT_ML.render(brojac_tekst, True, brojac_boja), (BOARD_SIZE + 20, 110))

    def inv_line(player, y_start):
        inv = game_state.inventory[player]
        label = "Твој Инвентар:" if player == "W" else "АИ Инвентар:"
        win.blit(FONT_GL.render(label, True, DRVO_SVETLO), (BOARD_SIZE + 20, y_start))

        has_topuz = len(game_state.inventory[player]["topuz"]) > 0
        has_sarac = len(game_state.inventory[player]["sarac"]) > 0

        topuz_txt = "Да" if has_topuz else "Не"
        sarac_txt = "Да" if has_sarac else "Не"

        if game_state.oklop_trajanje[player] > 0:
            oklop_txt = f"Активан ({game_state.oklop_trajanje[player]} пот.)"
        else:
            oklop_txt = "Не"

        win.blit(FONT_ML.render(f"• Топуз: {topuz_txt}", True, BELA), (BOARD_SIZE + 40, y_start + 35))
        win.blit(FONT_ML.render(f"• Шарац: {sarac_txt}", True, BELA), (BOARD_SIZE + 40, y_start + 58))
        win.blit(FONT_ML.render(f"• Оклоп: {oklop_txt}", True, BELA), (BOARD_SIZE + 40, y_start + 81))
        if game_state.vino_trajanje[player] > 0:
            win.blit(FONT_ML.render(f"Вино: Колебање ({game_state.vino_trajanje[player]} пот.)", True, (255, 100, 100)),
                     (BOARD_SIZE + 40, y_start + 104))

    inv_line("W", 130)
    inv_line("B", 270)

    win.blit(FONT_GL.render("Реликвије:", True, BRAZDA_BOJA), (BOARD_SIZE + 20, 410))
    top = game_state.carev_drum.get_first()
    bot = game_state.carev_drum.get_last()
    win.blit(FONT_ML.render(f"Горња: {top.upper() if top else 'Празно'}", True, BELA), (BOARD_SIZE + 30, 445))
    win.blit(FONT_ML.render(f"Доња:  {bot.upper() if bot else 'Празно'}", True, BELA), (BOARD_SIZE + 30, 468))

    pygame.draw.rect(win, (80, 80, 80), UNDO, border_radius=5)
    pygame.draw.rect(win, (80, 80, 80), REDO, border_radius=5)
    win.blit(FONT_ML.render("UNDO", True, BELA), (UNDO.x + 16, UNDO.y + 8))
    win.blit(FONT_ML.render("REDO", True, BELA), (REDO.x + 16, REDO.y + 8))


def draw_game_over(win, winner):
    overlay = pygame.Surface((BOARD_SIZE, HEIGHT))
    overlay.set_alpha(200)
    overlay.fill((0, 0, 0))
    win.blit(overlay, (0, 0))

    if winner == "W":
        txt = "Честитамо на победи!!!"
        col = (0, 255, 0)
        sub_txt = "Све противничке фигуре су елиминисане."
    elif winner == "B":
        txt = "Противник је победио!"
        col = (255, 0, 0)
        sub_txt = "Ваше фигуре су елиминисане."
    else:
        txt = "Нерешено!"
        col = (255, 165, 0)
        sub_txt = "Прошло је 40 потеза без једења и промоције."

    s1 = FONT_GL.render(txt, True, col)
    s3 = FONT_ML.render("Притисните ESC за излаз.", True, (200, 200, 200))
    s2 = FONT_ML.render(sub_txt, True, (200, 200, 200))
    win.blit(s1, (BOARD_SIZE // 2 - s1.get_width() // 2, HEIGHT // 2 - 30))
    win.blit(s2, (BOARD_SIZE // 2 - s2.get_width() // 2, HEIGHT // 2 + 10))
    win.blit(s3, (BOARD_SIZE // 2 - s3.get_width() // 2, HEIGHT // 2 + 50))

    pygame.draw.rect(win, DRVO_TAMNO, REPLAY_RECT, border_radius=6)
    pygame.draw.rect(win, BRAZDA_BOJA, REPLAY_RECT, width=2, border_radius=6)
    lbl_btn = FONT_GL.render("Погледај Репродукцију", True, BELA)
    win.blit(lbl_btn, (REPLAY_RECT.x + (REPLAY_RECT.width - lbl_btn.get_width()) // 2, REPLAY_RECT.y + 10))

def run_replay_mode(win, game_state):
    hronologija = []

    def obidji_stablo(cvor):
        if cvor != game_state.history_tree.root:
            hronologija.append(cvor)
        for dete in cvor.children:
            obidji_stablo(dete)

    if hasattr(game_state, 'history_tree') and game_state.history_tree.root:
        obidji_stablo(game_state.history_tree.root)
    if not hronologija:
        class DummyNode:
            def __init__(self, gs):
                self.game_state_snapshot = gs
                self.move_data = ["Крај игре", 0, 0, 0]
                self.parent = None
                self.children = []

        hronologija.append(DummyNode(game_state))

    index = 0
    izlaz_dugme = pygame.Rect(BOARD_SIZE + 15, HEIGHT - 80, 170, 35)

    BRZINA_ANIMACIJE = 1000
    poslednje_osvezenje = pygame.time.get_ticks()
    local_clock = pygame.time.Clock()

    reprodukcija_aktivna = True
    while reprodukcija_aktivna:
        local_clock.tick(60)
        trenutno_vreme = pygame.time.get_ticks()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                reprodukcija_aktivna = False

            if event.type == pygame.MOUSEBUTTONDOWN:
                m_pos = pygame.mouse.get_pos()
                if izlaz_dugme.collidepoint(m_pos):
                    reprodukcija_aktivna = False

        if trenutno_vreme - poslednje_osvezenje >= BRZINA_ANIMACIJE:
            if index < len(hronologija) - 1:
                index += 1
                poslednje_osvezenje = trenutno_vreme

        trenutni_cvor = hronologija[index]
        prikazano_stanje = trenutni_cvor.game_state_snapshot

        draw_board(win, prikazano_stanje)
        draw_pieces(win, prikazano_stanje, None, [])

        pygame.draw.rect(win, INFO_POZA, (BOARD_SIZE, 0, WIDTH - BOARD_SIZE, HEIGHT))
        win.blit(FONT_NAZ.render("Репродукција", True, BRAZDA_BOJA), (BOARD_SIZE + 20, 20))

        tekst_poteza = f"Потез: {index + 1} / {len(hronologija)}"
        win.blit(FONT_GL.render(tekst_poteza, True, BELA), (BOARD_SIZE + 20, 80))

        if hasattr(trenutni_cvor, "move_data") and trenutni_cvor.move_data:
            potez = trenutni_cvor.move_data
            detalji = f"Тип потеза: {potez[0].upper()}"
            win.blit(FONT_ML.render(detalji, True, (200, 200, 200)), (BOARD_SIZE + 20, 120))
            if trenutni_cvor.parent and len(trenutni_cvor.parent.children) > 1:
                win.blit(FONT_ML.render("Ундо грана одлучивања", True, (255, 140, 0)), (BOARD_SIZE + 20, 150))

        pygame.draw.rect(win, (80, 80, 80), izlaz_dugme, border_radius=5)
        win.blit(FONT_ML.render("ЗАВРШИ ПРЕГЛЕД", True, BELA), (izlaz_dugme.x + 22, izlaz_dugme.y + 8))

        pygame.display.update()



KARTE_INFO = {
    "topuz": ("Топуз", "Разорни ударац",
              ["Поједи противника без прескакања —",
               "фигура стаје на његово поље.",
               "Нема лачаног jedenja."]),
    "sarac": ("Шарац", "Шарчев скок",
              ["Ова фигура (и Марко) могу",
               "прескочити своју фигуру,",
               "jednom по потезу."]),
    "oklop": ("Тока од челика", "Оклоп",
              ["Штити ову фигуру 1 потез",
               "(2 за Марка Краљевића)."]),
    "vino": ("Мешина рујног вина", "Поглед испод обрва",
             ["Замрзава најближег противника",
              "— не може да се kreće 2 потеза.",
              "Марко је имун."]),
    "blago": ("Три товара блага", "Крунисање",
              ["Ова фигура одмах постаје Краљевић."]),
}


def draw_relic_screen(win, gornja, donja):
    overlay = pygame.Surface((BOARD_SIZE, HEIGHT))
    overlay.set_alpha(220)
    overlay.fill((0, 0, 0))
    win.blit(overlay, (0, 0))
    title = FONT_GL.render("ИЗАБЕРИТЕ РЕЛИКВИЈУ", True, BRAZDA_BOJA)
    win.blit(title, (BOARD_SIZE // 2 - title.get_width() // 2, HEIGHT // 2 - 230))

    def draw_card(rect, key, label):
        pygame.draw.rect(win, (50, 50, 70), rect, border_radius=10)
        pygame.draw.rect(win, BRAZDA_BOJA, rect, width=3, border_radius=10)
        win.blit(FONT_ML.render(label, True, (200, 200, 200)), (rect.x + 15, rect.y + 10))
        info = KARTE_INFO.get(key, (str(key).capitalize(), "?", []))
        win.blit(FONT_GL.render(info[0], True, BRAZDA_BOJA), (rect.x + 15, rect.y + 32))
        win.blit(FONT_ML.render(f"Способност: {info[1]}", True, BELA), (rect.x + 15, rect.y + 60))
        for i, red in enumerate(info[2]):
            win.blit(FONT_ML.render(red, True, (180, 180, 180)), (rect.x + 15, rect.y + 88 + i * 18))

    draw_card(GORNJA_RECT, gornja, "Горња карта  [клик за избор]")
    draw_card(DONJA_RECT, donja, "Доња карта   [клик за избор]")


def end_idx(move):
    return move[2] if move[0] == 'quiet' else move[3]


def mouse_to_rc(pos):
    x, y = pos
    return y // SQUARE_SIZE, x // SQUARE_SIZE


def main():
    clock = pygame.time.Clock()
    game_state = GameState()
    ai = AIPlayer(color="B", max_depth=4)

    selected = None
    sel_moves = []
    relic_open = False
    g_karta = d_karta = None

    run = True
    while run:
        clock.tick(FPS)

        if (game_state.current_player == "B" and not game_state.game_over and not relic_open):
            draw_board(WIN, game_state)
            draw_pieces(WIN, game_state, selected, [])
            draw_info(WIN, game_state)
            pygame.display.update()

            ai_move = ai.get_best_move(game_state)
            if ai_move:
                pygame.time.wait(1000)
                game_state.execute_player_move(ai_move)
                end_index = end_idx(ai_move)
                if game_state.board.is_brazda(end_index) and game_state.current_player == "B":
                    front = game_state.carev_drum.get_first()
                    back = game_state.carev_drum.get_last()
                    pri = {"blago": 5, "oklop": 4, "topuz": 3, "sarac": 2, "vino": 1}
                    ch = "front" if pri.get(front, 0) >= pri.get(back, 0) else "back"
                    game_state.claim_relikvija(ch)
                    game_state.switch_player()
                game_state.check_game_over()
            else:
                game_state.game_over = True
                game_state.winner = "W"
            continue

        cursor_set = False
        if game_state.current_player == "W" and not game_state.game_over and not relic_open:
            mouse_pos = pygame.mouse.get_pos()
            mouse_row, mouse_col = mouse_to_rc(mouse_pos)
            if mouse_col <= 7:
                hovered_index = game_state.board.row_col_to_index(mouse_row, mouse_col)
                if hovered_index is not None:
                    movable = {m[1] for m in game_state.get_valid_moves()}
                    if hovered_index in movable:
                        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
                        cursor_set = True
        if not cursor_set:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                run = False

            if event.type == pygame.MOUSEBUTTONDOWN:
                pos = pygame.mouse.get_pos()

                if game_state.game_over:
                    if REPLAY_RECT.collidepoint(pos):
                        run_replay_mode(WIN, game_state)
                    continue
                if relic_open:
                    if GORNJA_RECT.collidepoint(pos):
                        game_state.claim_relikvija("front")
                        game_state.switch_player()
                        relic_open = False
                    elif DONJA_RECT.collidepoint(pos):
                        game_state.claim_relikvija("back")
                        game_state.switch_player()
                        relic_open = False
                    continue

                if UNDO.collidepoint(pos):
                    if not game_state.undo_stack.is_empty():
                        game_state.undo()
                        while game_state.current_player == "B" and not game_state.undo_stack.is_empty():
                            game_state.undo()
                        selected, sel_moves = None, []
                        game_state.game_over = False
                        game_state.winner = None
                    continue

                if REDO.collidepoint(pos):
                    if not game_state.redo_stack.is_empty():
                        game_state.redo()
                        if game_state.current_player == "B" and not game_state.redo_stack.is_empty():
                            game_state.redo()
                        selected, sel_moves = None, []
                    continue

                row, col = mouse_to_rc(pos)
                if col > 7:
                    continue
                clicked_index = game_state.board.row_col_to_index(row, col)

                executed = False
                for move in sel_moves:
                    if end_idx(move) == clicked_index:
                        game_state.execute_player_move(move)
                        executed = True
                        if game_state.board.is_brazda(clicked_index) and game_state.current_player == "W":
                            g_karta = game_state.carev_drum.get_first()
                            d_karta = game_state.carev_drum.get_last()
                            if g_karta and d_karta:
                                relic_open = True
                        break

                if executed:
                    selected, sel_moves = None, []
                    game_state.check_game_over()
                    continue

                if clicked_index is not None:
                    piece = game_state.board.state[clicked_index]
                    if piece and game_state.board.get_piece_color(piece) == "W":
                        selected = clicked_index
                        sel_moves = [m for m in game_state.get_valid_moves() if m[1] == clicked_index]
                    else:
                        selected, sel_moves = None, []

        draw_board(WIN, game_state)
        draw_pieces(WIN, game_state, selected, sel_moves)
        if game_state.game_over:
            draw_game_over(WIN, game_state.winner)
        elif relic_open:
            draw_relic_screen(WIN, g_karta, d_karta)
        draw_info(WIN, game_state)

        pygame.display.update()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()