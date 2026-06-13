import copy
import random
from random import choice
from zobrist import TranspositionTable


class AIPlayer:
    def __init__(self, color = "B",max_depth = 4):
        self.color = color
        self.max_depth = max_depth
        self.tt = TranspositionTable()

    def evaluate_board(self, game_state):
        score = 0
        board = game_state.board
        for index in range(32):
            piece = board.state[index]
            if not piece:
                continue

            piece_value = 0
            is_kraljevic = False
            if "_J" in piece:
                piece_value = 10
            elif "_K" in piece:
                piece_value = 30
                is_kraljevic = True
            elif "_M" in piece:
                piece_value = 150
                is_kraljevic = True

            row, col = board.index_to_row_col(index)
            if piece == "B_J":
                piece_value += row * 1.5
            elif piece == "W_J":
                piece_value += (7-row) * 1.5

            if not is_kraljevic:
                if col ==0 or col == 7 or row == 0 or row == 7:
                    piece_value += 3
            else:
                if 2 <= col <= 5 and 2 <= row <= 5:
                    piece_value += 4

            if board.get_piece_color(piece) == "B":
                score += piece_value
            else:
                score -= piece_value

        if game_state.inventory["B"]["topuz"]: score += 12
        if game_state.inventory["B"]["sarac"]: score += 15
        if game_state.oklop_trajanje["B"]>0: score += 15
        if game_state.vino_trajanje["B"]>0: score -= 20

        if game_state.inventory["W"]["topuz"]: score -= 12
        if game_state.inventory["W"]["sarac"]: score -= 15
        if game_state.oklop_trajanje["W"]>0: score -= 15
        if game_state.vino_trajanje["W"]>0: score += 20
        return score

    def simulate_relic_choice(self, game_state):
        brazda_fig = game_state.brazda_figura_index

        if brazda_fig is None or not game_state.board.is_brazda(brazda_fig):
            return
        front = game_state.carev_drum.get_first()
        back = game_state.carev_drum.get_last()
        priority = {"blago": 5, "oklop": 4, "topuz": 3, "sarac": 2, "vino": 1}
        if priority.get(front, 0) >= priority.get(back, 0):
            choice = "front"
        else:
            choice = "back"
        game_state.claim_relikvija(choice)

    def get_best_move(self, game_state):
        valid_moves = game_state.get_valid_moves()
        if not valid_moves:
            return None

        best_move = []
        best_value = float('-inf') #trazim maksimum pa krecem od - beskonacno
        alpha = float('-inf')
        beta = float('inf')

        for move in valid_moves:
            simulated_state = copy.deepcopy(game_state)
            simulated_state.execute_player_move(move)
            end_idx = self.get_end_index(move)
            if simulated_state.board.is_brazda(end_idx):
                self.simulate_relic_choice(simulated_state)

            move_value = self.minmax(simulated_state, self.max_depth - 1, alpha, beta, False)
            if move_value > best_value:
                best_value = move_value
                best_move = [move]
            elif move_value == best_value:
                best_move.append(move)
            alpha = max(alpha, best_value)

        return random.choice(best_move)

    def get_end_index(self, move):
        if move[0] == "quiet":
            return move[2]
        else:
            return move[3]

    def minmax(self, game_state, depth, alpha, beta, is_max):
        cached_value = self.tt.lookup(game_state.current_hash, depth)
        if cached_value is not None:
            return cached_value
        if depth == 0 or game_state.check_game_over(): #prekida se ako smo stigli do kraja dubine ili ako je igra zavrsena
            return self.evaluate_board(game_state)

        valid_moves = game_state.get_valid_moves()
        if not valid_moves:
            return self.evaluate_board(game_state)
        if is_max:
            max_eval = float("-inf")
            for move in valid_moves:
                simulated_state = copy.deepcopy(game_state)
                simulated_state.execute_player_move(move)
                end_idx = self.get_end_index(move)
                if simulated_state.board.is_brazda(end_idx):
                    self.simulate_relic_choice(simulated_state)
                evaluation = self.minmax(simulated_state, depth - 1, alpha, beta, False)
                max_eval = max(max_eval, evaluation)
                alpha = max(alpha, evaluation)
                if beta <= alpha:
                    break
            self.tt.store(game_state.current_hash, max_eval, depth)
            return max_eval

        else:
            min_eval = float("inf")
            for move in valid_moves:
                simulated_state = copy.deepcopy(game_state)
                simulated_state.execute_player_move(move)
                end_idx = self.get_end_index(move)
                if simulated_state.board.is_brazda(end_idx):
                    self.simulate_relic_choice(simulated_state)
                evaluation = self.minmax(simulated_state, depth - 1, alpha, beta, True)
                min_eval = min(min_eval, evaluation)
                beta = min(beta, evaluation)
                if beta <= alpha:
                    break
            self.tt.store(game_state.current_hash, min_eval, depth)
            return min_eval

