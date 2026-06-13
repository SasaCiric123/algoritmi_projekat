import copy
import contextlib
import io
import time

from zobrist import TranspositionTable


class SearchTimeout(Exception):
    pass


class AIPlayer:
    def __init__(self, color="B", max_depth=4, time_limit=3.0):
        self.color = color
        self.max_depth = max_depth
        self.time_limit = time_limit
        self.tt = TranspositionTable()
        self.last_completed_depth = 0

    def evaluate_board(self, game_state):
        if game_state.game_over:
            if game_state.winner == "B":
                return 100000
            if game_state.winner == "W":
                return -100000
            return 0

        score = 0
        board = game_state.board

        for index in range(32):
            piece = board.state[index]
            if not piece:
                continue

            piece_value = self.get_piece_value(piece)
            row, col = board.index_to_row_col(index)

            if piece == "B_J":
                piece_value += row * 2
                if row == 6:
                    piece_value += 12
            elif piece == "W_J":
                piece_value += (7 - row) * 2
                if row == 1:
                    piece_value += 12
            elif 2 <= row <= 5 and 2 <= col <= 5:
                piece_value += 6

            if board.get_piece_color(piece) == "B":
                score += piece_value
            else:
                score -= piece_value

        b_moves = self.get_moves_for(game_state, "B")
        w_moves = self.get_moves_for(game_state, "W")
        b_captures = [move for move in b_moves if move[0] == "capture"]
        w_captures = [move for move in w_moves if move[0] == "capture"]

        score += (len(b_moves) - len(w_moves)) * 2
        score += (len(b_captures) - len(w_captures)) * 15
        score += self.best_capture_value(game_state, b_captures) * 8
        score -= self.best_capture_value(game_state, w_captures) * 15

        if not w_moves:
            score += 500
        if not b_moves:
            score -= 500

        score += self.relic_score(game_state, "B")
        score -= self.relic_score(game_state, "W")
        return score

    def get_best_move(self, game_state, time_limit=None):
        valid_moves = game_state.get_valid_moves()
        if not valid_moves:
            return None

        valid_moves = self.remove_obvious_blunders(game_state, valid_moves)
        ordered_moves = self.order_moves(game_state, valid_moves, reverse=True)
        best_move = ordered_moves[0]

        limit = self.time_limit if time_limit is None else time_limit
        deadline = time.perf_counter() + limit
        self.last_completed_depth = 0
        self.tt.clear()

        for depth in range(1, self.max_depth + 1):
            try:
                depth_best_move = self.search_at_depth(game_state, ordered_moves, depth, deadline)
                if depth_best_move is not None:
                    best_move = depth_best_move
                    self.last_completed_depth = depth
            except SearchTimeout:
                break

        return best_move

    def search_at_depth(self, game_state, valid_moves, depth, deadline):
        best_move = None
        best_value = float("-inf")
        best_tiebreak = float("-inf")
        alpha = float("-inf")
        beta = float("inf")

        for move in valid_moves:
            self.check_timeout(deadline)
            simulated_state = self.simulate_move(game_state, move)
            move_value = self.minmax(simulated_state, depth - 1, alpha, beta, deadline)
            tiebreak = self.quick_move_score(game_state, move)

            if move_value > best_value or (move_value == best_value and tiebreak > best_tiebreak):
                best_value = move_value
                best_tiebreak = tiebreak
                best_move = move

            alpha = max(alpha, best_value)

        return best_move

    def minmax(self, game_state, depth, alpha, beta, deadline):
        self.check_timeout(deadline)

        cached_value = self.tt.lookup(self.position_key(game_state), depth)
        if cached_value is not None:
            return cached_value

        if game_state.check_game_over():
            if game_state.winner == "B":
                return 100000 + depth
            if game_state.winner == "W":
                return -100000 - depth
            return 0

        if depth == 0:
            return self.evaluate_board(game_state)

        valid_moves = game_state.get_valid_moves()
        if not valid_moves:
            return self.evaluate_board(game_state)

        is_max = game_state.current_player == self.color

        if is_max:
            best_value = float("-inf")
            cutoff = False
            for move in self.order_moves(game_state, valid_moves, reverse=True):
                simulated_state = self.simulate_move(game_state, move)
                value = self.minmax(simulated_state, depth - 1, alpha, beta, deadline)
                best_value = max(best_value, value)
                alpha = max(alpha, value)
                if beta <= alpha:
                    cutoff = True
                    break
        else:
            best_value = float("inf")
            cutoff = False
            for move in self.order_moves(game_state, valid_moves, reverse=False):
                simulated_state = self.simulate_move(game_state, move)
                value = self.minmax(simulated_state, depth - 1, alpha, beta, deadline)
                best_value = min(best_value, value)
                beta = min(beta, value)
                if beta <= alpha:
                    cutoff = True
                    break

        if not cutoff:
            self.tt.store(self.position_key(game_state), best_value, depth)
        return best_value

    def simulate_relic_choice(self, game_state):
        brazda_fig = game_state.brazda_figura_index
        if brazda_fig is None or not game_state.board.is_brazda(brazda_fig):
            return

        front = game_state.carev_drum.get_first()
        back = game_state.carev_drum.get_last()
        priority = {"blago": 5, "oklop": 4, "topuz": 3, "sarac": 2, "vino": 1}
        choice = "front" if priority.get(front, 0) >= priority.get(back, 0) else "back"

        with contextlib.redirect_stdout(io.StringIO()):
            game_state.claim_relikvija(choice)
        game_state.switch_player()

    def simulate_move(self, game_state, move):
        simulated_state = copy.deepcopy(game_state)
        simulated_state.execute_player_move(move)
        end_idx = self.get_end_index(move)
        if simulated_state.board.is_brazda(end_idx):
            self.simulate_relic_choice(simulated_state)
        return simulated_state

    def remove_obvious_blunders(self, game_state, moves):
        safe_moves = []

        for move in moves:
            moving_piece = game_state.board.state[move[1]]
            moved_value = self.get_piece_value(moving_piece)
            gained_value = 0
            if move[0] == "capture":
                gained_value = self.get_piece_value(game_state.board.state[move[2]])

            simulated_state = self.simulate_move(game_state, move)
            if simulated_state.current_player == game_state.current_player:
                safe_moves.append(move)
                continue

            enemy_captures = [m for m in simulated_state.get_valid_moves() if m[0] == "capture"]
            enemy_gain = self.best_capture_value(simulated_state, enemy_captures)
            if enemy_gain < moved_value or gained_value >= enemy_gain:
                safe_moves.append(move)

        return safe_moves or moves

    def order_moves(self, game_state, moves, reverse):
        return sorted(moves, key=lambda move: self.quick_move_score(game_state, move), reverse=reverse)

    def quick_move_score(self, game_state, move):
        board = game_state.board
        piece = board.state[move[1]]
        end_idx = self.get_end_index(move)
        end_row, end_col = board.index_to_row_col(end_idx)
        score = 0

        if move[0] == "capture":
            score += self.get_piece_value(board.state[move[2]]) * 3
            if len(move) > 4 and move[4] == "topuz":
                score += 8
        elif len(move) > 3 and move[3] == "sarac":
            score += 6

        if piece == "B_J" and end_row == 7:
            score += 80
        elif piece == "W_J" and end_row == 0:
            score += 80

        if 2 <= end_row <= 5 and 2 <= end_col <= 5:
            score += 4
        if board.is_brazda(end_idx):
            score += 12

        return score

    def get_moves_for(self, game_state, player):
        old_player = game_state.current_player
        old_chain = game_state.in_chain
        game_state.current_player = player
        game_state.in_chain = None
        moves = game_state.get_valid_moves()
        game_state.current_player = old_player
        game_state.in_chain = old_chain
        return moves

    def best_capture_value(self, game_state, capture_moves):
        best_value = 0
        for move in capture_moves:
            best_value = max(best_value, self.get_piece_value(game_state.board.state[move[2]]))
        return best_value

    def relic_score(self, game_state, player):
        score = 0
        if game_state.inventory[player]["topuz"]:
            score += 18
        if game_state.inventory[player]["sarac"]:
            score += 14
        if game_state.oklop_trajanje[player] > 0:
            score += 18
        if game_state.vino_trajanje[player] > 0:
            score -= 25
        return score

    def position_key(self, game_state):
        return (
            game_state.current_hash,
            game_state.current_player,
            game_state.in_chain,
            tuple(sorted(game_state.inventory["W"]["topuz"])),
            tuple(sorted(game_state.inventory["B"]["topuz"])),
            tuple(sorted(game_state.inventory["W"]["sarac"])),
            tuple(sorted(game_state.inventory["B"]["sarac"])),
            game_state.oklop_trajanje["W"],
            game_state.oklop_trajanje["B"],
            game_state.vino_trajanje["W"],
            game_state.vino_trajanje["B"],
            game_state.oklop_figura["W"],
            game_state.oklop_figura["B"],
            game_state.vino_figura["W"],
            game_state.vino_figura["B"],
            tuple(game_state.carev_drum.to_list()),
        )

    def get_piece_value(self, piece):
        if not piece:
            return 0
        if "_M" in piece:
            return 150
        if "_K" in piece:
            return 30
        return 10

    def get_end_index(self, move):
        return move[2] if move[0] == "quiet" else move[3]

    def check_timeout(self, deadline):
        if time.perf_counter() >= deadline:
            raise SearchTimeout()
