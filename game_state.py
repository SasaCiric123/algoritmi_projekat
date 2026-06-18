from structures import Stack, HistoryTree, Deque
from board import Board
from zobrist import ZobristHash
import copy

LOG_TO_CONSOLE = False


class GameState:
    def __init__(self):
        self.board = Board()
        self.current_player = "W"
        self.inventory = {
            "W": {"topuz": set(), "sarac": set()},
            "B": {"topuz": set(), "sarac": set()}
        }
        self.oklop_trajanje = {"W":0, "B":0}
        self.vino_trajanje = {"W":0, "B":0}
        self.sarac_koriscen = {"W":False, "B":False}
        self.oklop_figura = {"W":None, "B":None}
        self.vino_figura = {"W":None, "B":None}

        self.undo_stack = Stack()
        self.history_tree = HistoryTree()
        self.game_over = False
        self.winner = None
        self.in_chain = None

        self.carev_drum = Deque()
        pocetne_relikvije = ["topuz", "sarac", "oklop", "vino", "blago"]
        for relikvija in pocetne_relikvije:
            self.carev_drum.add_last(relikvija)

        self.brazda_figura_index = None
        self.zobrist = ZobristHash()
        self.current_hash = self.zobrist.compute_initial_hash(self.board.state, self.current_player)
        self.halfmove_clock = 0

    def log(self, message):
        if LOG_TO_CONSOLE:
            print(message)

    def check_marko_promotion(self, player):#uslovi za marka
        inv = self.inventory[player]
        protivnik = "B" if player == "W" else "W"
        ima_topuz = len(inv.get("topuz", set())) > 0
        ima_sarac = len(inv.get("sarac", set())) > 0
        ima_vino = self.vino_trajanje[protivnik] > 0 and self.vino_figura[protivnik] is not None
        ima_kraljevic = False

        for i in range(32):
            pc = self.board.state[i]
            if pc and self.board.get_piece_color(pc) == player and "_K" in pc:
                ima_kraljevic = True
                break

        if ima_topuz and ima_sarac and ima_vino and ima_kraljevic:
            return True
        return False

    def try_marko_upgrade(self, player, idx = None): #ako nije navedeno koja figura se promovise onda prva kraljevska
        if not self.check_marko_promotion(player):
            return False
        if idx is None:
            for i in range(32):
                piece = self.board.state[i]
                if piece and self.board.get_piece_color(piece) == player and "_K" in piece:
                    idx = i;
                    break
        if idx is None:
            return False
        self.board.promote_to_marko(idx)
        self.inventory[player]["sarac"].add(idx)
        self.inventory[player]["topuz"].add(idx)
        self.halfmove_clock = 0
        return True

    def sync_marko_powers(self):
        for idx, piece in enumerate(self.board.state):
            if piece in ("W_M", "B_M"):
                player = self.board.get_piece_color(piece)
                self.inventory[player]["sarac"].add(idx)
                self.inventory[player]["topuz"].add(idx)

    def switch_player(self):
        self.in_chain = None
        trenutni = self.current_player
        protivnik = "B" if self.current_player == "W" else "W"
        self.sarac_koriscen[trenutni] = False

        if self.oklop_trajanje[protivnik] > 0:
            self.oklop_trajanje[protivnik] -= 1
            if self.oklop_trajanje[protivnik] == 0:
                self.oklop_figura[protivnik] = None
                self.log(f"Оклоп играча {protivnik} је зарђао!")

        if self.vino_trajanje[trenutni] > 0:
            self.vino_trajanje[trenutni] -= 1
            if self.vino_trajanje[trenutni] == 0:
                self.log(f"Играч {trenutni} се отрезнио, дејство вина је прошло!")

        self.current_player = protivnik
        self.cycle_carev_drum()

    def get_topuz_owner(self):
        if not self.inventory[self.current_player]["topuz"]:
            return None
        return "all"

    def get_valid_moves(self):
        valid_moves = []
        p = self.current_player
        self.sync_marko_powers()
        topuz_s = self.inventory[p]["topuz"]
        sarac_s = self.inventory[p]["sarac"]
        oklop_t = self.get_oklop_targets()

        if self.in_chain is not None:
            chain_piece = self.board.state[self.in_chain]
            if chain_piece and self.board.get_piece_color(chain_piece) == p:
                if self.vino_trajanje[p] > 0 and self.vino_figura[p] == self.in_chain:
                    return []

                has_topuz_chain = self.in_chain in topuz_s or chain_piece in ("W_M", "B_M")
                t_owner = self.in_chain if has_topuz_chain else None
                piece_captures = self.board.get_piece_capture_moves(self.in_chain,
                                                                    topuz_owner = t_owner,
                                                                    oklop_targets=oklop_t)
                for move in piece_captures:
                    valid_moves.append(self.format_capture(move))
                return valid_moves
            else:
                self.in_chain = None

        captures = []
        for index in range(32):
            piece = self.board.state[index]
            if piece and self.board.get_piece_color(piece) != p:
                continue
            if self.vino_frozen(self.board.get_piece_color(piece), index):
                continue
            has_topuz = index in topuz_s or piece in ("W_M", "B_M")
            t_owner = index if has_topuz else None
            captures.extend(self.board.get_piece_capture_moves(index,
                                                                   topuz_owner=t_owner,
                                                                   oklop_targets=oklop_t))
        if captures:
            for move in captures:
                valid_moves.append(self.format_capture(move))
            return valid_moves

        for index in range(32):
            piece = self.board.state[index]
            if not piece or self.board.get_piece_color(piece) != p:
                continue
            if self.vino_frozen(self.board.get_piece_color(piece), index):
                continue
            figura_sarac = (index in sarac_s or piece in ("W_M", "B_M"))
            sarac_available = figura_sarac and not self.sarac_koriscen[p]
            moves_for_piece = self.board.get_piece_quiet_moves(index, sarac_available=sarac_available)
            for move in moves_for_piece:
                start = move[0]
                end = move[1]
                flag = 'sarac' if (len(move) > 2 and move[2] == 'sarac') else None
                valid_moves.append(('quiet', start, end, flag))

        return valid_moves

    def format_capture(self, move):
        if len(move) == 3:
            return ('capture', move[0], move[1], move[2], None)
        elif len(move) == 4 and move[3] == "topuz":
            return ('capture', move[0], move[1], move[2], "topuz")
        return ('capture', move[0], move[1], move[2], None)

    def get_oklop_targets(self):
        targets = set()
        for color in ["B", "W"]:
            if self.oklop_trajanje[color] > 0 and self.oklop_figura[color] is not None:
                targets.add(self.oklop_figura[color])
        return targets

    def vino_frozen(self, player, index):
        if player not in ("W","B"):
            return False
        return (self.vino_trajanje[player] > 0 and self.vino_figura[player] == index)

    def execute_player_move(self, move_tuple, brazda_square = False):
        self.sync_marko_powers()
        move_type = move_tuple[0] #ili capture ili quiet
        start_idx = move_tuple[1]
        moving_piece = self.board.state[start_idx]
        if moving_piece and self.vino_frozen(self.current_player, start_idx):
            return False

        #cuvam kopiju ako bude bio undo
        if self.undo_stack is not None:
            board_copy = self.board.copy_board()
            state_snapshot = self.snapshot_state()
            self.undo_stack.push((board_copy, self.current_player, state_snapshot))
        protivnik = "B" if self.current_player == "W" else "W"
        if move_type == "quiet":
            self.halfmove_clock += 1
            end_idx = move_tuple[2]
            flag = move_tuple[3] if len(move_tuple) > 3 else None
            if flag == "sarac":
                self.sarac_koriscen[self.current_player] = True
            if start_idx in self.inventory[self.current_player]["topuz"]:
                self.inventory[self.current_player]["topuz"].discard(start_idx)
                self.inventory[self.current_player]["topuz"].add(end_idx)

            if start_idx in self.inventory[self.current_player]["sarac"]:
                self.inventory[self.current_player]["sarac"].discard(start_idx)
                self.inventory[self.current_player]["sarac"].add(end_idx)
            self.board.make_move(start_idx, end_idx)
            self.in_chain = None
            self.brazda_figura_index = end_idx
            if not self.board.is_brazda(end_idx):
                self.switch_player()

        elif move_type == "capture":
            self.halfmove_clock = 0
            victim_idx = move_tuple[2]
            end_idx = move_tuple[3]
            flag = move_tuple[4] if len(move_tuple) > 4 else None
            if flag == "topuz":
                self.board.make_move(start_idx, end_idx, victim_index=end_idx)
            else:
                self.board.make_move(start_idx, end_idx, victim_index=victim_idx)

            self.inventory[protivnik]["topuz"].discard(victim_idx)
            self.inventory[protivnik]["sarac"].discard(victim_idx)
            self.inventory[protivnik]["topuz"].discard(end_idx)
            self.inventory[protivnik]["sarac"].discard(end_idx)

            if start_idx in self.inventory[self.current_player]["topuz"]:
                self.inventory[self.current_player]["topuz"].discard(start_idx)
                self.inventory[self.current_player]["topuz"].add(end_idx)

            if start_idx in self.inventory[self.current_player]["sarac"]:
                self.inventory[self.current_player]["sarac"].discard(start_idx)
                self.inventory[self.current_player]["sarac"].add(end_idx)
            self.brazda_figura_index = end_idx
            if flag == "topuz":
                self.in_chain = None
                if not self.board.is_brazda(end_idx):
                    self.switch_player()
            else:
                next_capture = self.board.get_piece_capture_moves(end_idx,
                                                              topuz_owner=None,
                                                              oklop_targets=self.get_oklop_targets())
                if next_capture:
                    self.in_chain = end_idx
                else:
                    if not self.board.is_brazda(end_idx):
                        self.switch_player()

        if self.history_tree is not None:
            self.history_tree.add_move(move_tuple, copy.deepcopy(self))

        self.current_hash = self.zobrist.compute_initial_hash(self.board.state, self.current_player)

    def snapshot_state(self):#snapshot za moci
        self.sync_marko_powers()
        return{
            "inventory": copy.deepcopy(self.inventory),
            "oklop_trajanje": dict(self.oklop_trajanje),
            "vino_trajanje": dict(self.vino_trajanje),
            "oklop_figura": dict(self.oklop_figura),
            "vino_figura": dict(self.vino_figura),
            "sarac_koriscen": dict(self.sarac_koriscen),
            "in_chain": self.in_chain,
            "brazda_figura_index": self.brazda_figura_index,
            "carev_drum": self.carev_drum.to_list(),
            "halfmove_clock": self.halfmove_clock
        }

    def restore_snapshot(self, snapshot):
        self.inventory = copy.deepcopy(snapshot["inventory"])
        self.oklop_trajanje = dict(snapshot["oklop_trajanje"])
        self.vino_trajanje = dict(snapshot["vino_trajanje"])
        self.oklop_figura = dict(snapshot["oklop_figura"])
        self.vino_figura = dict(snapshot["vino_figura"])
        self.sarac_koriscen = dict(snapshot["sarac_koriscen"])
        self.in_chain = snapshot["in_chain"]
        self.brazda_figura_index = snapshot["brazda_figura_index"]
        self.halfmove_clock = snapshot.get("halfmove_clock", 0)

        from structures import Deque
        self.carev_drum = Deque()
        for stavka in snapshot["carev_drum"]:
            self.carev_drum.add_last(stavka)
        self.sync_marko_powers()

    def undo(self):
        if self.undo_stack.is_empty():
            self.log("Нема потеза за поништавање!")
            return False
        previous_board, previous_player, previous_snapshot = self.undo_stack.pop()
        self.board = previous_board
        self.current_player = previous_player
        self.restore_snapshot(previous_snapshot)
        self.sync_marko_powers()
        if self.history_tree is not None:
            self.history_tree.undo_move()
        self.log("Потез успешно поништен (Undo)!")
        return True

    def cycle_carev_drum(self):
        if not self.carev_drum.is_empty():
            poslednja = self.carev_drum.remove_last()
            self.carev_drum.add_first(poslednja)

    def get_brazda_options(self):
        if self.carev_drum.is_empty():
            return None, None

        front_option = self.carev_drum.get_first()
        back_option = self.carev_drum.get_last()
        return front_option, back_option

    def claim_relikvija(self, choice_direction):
        p = self.current_player
        figura_index = self.brazda_figura_index

        if choice_direction == "front":
            relikvija = self.carev_drum.get_first()
        else:
            relikvija = self.carev_drum.get_last()

        if relikvija == "topuz":
            if figura_index is not None:
                self.inventory[p]["topuz"].add(figura_index)
            self.log(f"Играч {p} је добио Топуз!")

        elif relikvija == "sarac":
            if figura_index is not None:
                self.inventory[p]["sarac"].add(figura_index)
                self.log(f"Играч {p} је добио Шарца!")

        elif relikvija == "oklop":
            if figura_index is not None:
                piece = self.board.state[figura_index]
                if piece and "_M" in piece:
                    self.oklop_trajanje[p] = 2
                else:
                    self.oklop_trajanje[p] = 1
                self.oklop_figura[p] = figura_index
                self.log(f"Играч {p}: Фигура на {figura_index} је обукла Оклоп (трајање: {self.oklop_trajanje[p]} пот.)!")

        elif relikvija == "vino":
            protivnik = "B" if p == "W" else "W"
            if figura_index is not None:
                my_color = self.board.get_piece_color(self.board.state[figura_index]) or p
                nearest = self.board.get_nearest_enemy(figura_index, my_color)
                if nearest is not None:
                    nearest_piece = self.board.state[nearest]
                    if nearest_piece and "_M" in nearest_piece:
                        self.log(f"Марко Краљевић је имун на Вино!")
                    else:
                        self.vino_trajanje[protivnik] = 2
                        self.vino_figura[protivnik] = nearest
                        self.log(f"Бачено рујно вино!")
                else:
                    self.log("Нема противника у близини!")

        elif relikvija == "blago":
            if figura_index is not None:
                piece = self.board.state[figura_index]
                if piece:
                    self.board.promote_to_kraljevic(figura_index)
                    self.halfmove_clock = 0
                    self.log(f"Три товара блага!")
                    self.try_marko_upgrade(p, figura_index)
        if relikvija != "blago":
            self.try_marko_upgrade(p, figura_index)

        if self.history_tree and self.history_tree.current_node:
            self.history_tree.current_node.game_state_snapshot = copy.deepcopy(self)

    def check_game_over(self):
        white_count = 0
        black_count = 0

        for index in range(32):
            piece = self.board.state[index]
            if piece:
                color = self.board.get_piece_color(piece)
                if  color == "W":
                    white_count += 1
                elif color == "B":
                    black_count += 1

        if white_count == 0:
            self.game_over = True
            self.winner = "B"
            return True
        if black_count == 0:
            self.game_over = True
            self.winner = "W"
            return True

        if self.halfmove_clock >= 40:
            self.game_over = True
            self.winner = None
            return True

        if not self.get_valid_moves():
            self.game_over = True
            self.winner = "B" if self.current_player == "W" else "W"
            return True

        return False

    def display_status(self):
        self.log("--- СТАТУС ИГРЕ ---")
        self.log(f"На потезу је: {'Бели (Јунаци)' if self.current_player == 'W' else 'Црни (АИ)'}")
        self.log(f"Инвентар Бели: {self.inventory['W']}")
        self.log(f"Инвентар Црни: {self.inventory['B']}")
        self.log("-------------------")


    def __getstate__(self):#stavljam da deep copy ne gleda history tree i undo
        state = self.__dict__.copy()
        state["history_tree"] = None
        state["undo_stack"] = None
        import copy
        state["inventory"] = copy.deepcopy(self.inventory)
        state["oklop_trajanje"] = dict(self.oklop_trajanje)
        state["vino_trajanje"] = dict(self.vino_trajanje)
        state["sarac_koriscen"] = dict(self.sarac_koriscen)
        state["oklop_figura"] = dict(self.oklop_figura)
        state["vino_figura"] = dict(self.vino_figura)
        state["current_hash"] = self.current_hash

        from structures import Deque
        novi_drum = Deque(capacity=self.carev_drum.capacity)
        for stavka in self.carev_drum.to_list():
            novi_drum.add_last(stavka)
        state["carev_drum"] = novi_drum
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.history_tree = None
        self.undo_stack= None

