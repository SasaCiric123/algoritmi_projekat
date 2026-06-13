import random

class ZobristHash:
    def __init__(self):
        self.pieces = ["W_J", "W_K", "W_M", "B_J", "B_K", "B_M"]
        self.num_squares = 32
        self.table = {}
        for square in range(self.num_squares):
            self.table[square] = {}
            for piece in self.pieces:
                self.table[square][piece] = random.getrandbits(64)

        self.black_turns_hash = random.getrandbits(64)

    def compute_initial_hash(self, board_state, current_player):
        current_hash = 0
        for square in range(self.num_squares):
            piece = board_state[square]
            if piece is not None:
                current_hash ^= self.table[square][piece]

        if current_player == "B":
            current_hash ^= self.black_turns_hash

        return current_hash

    def update_hash_move(self, current_hash, move_tuple, board_before_move, current_player, moving_piece):
        new_hash = current_hash
        move_type = move_tuple[0]
        start_idx = move_tuple[1]

        if moving_piece is None:
            return current_hash

        if move_type == "quiet":
            end_idx = move_tuple[2]
            new_hash ^= self.table[start_idx][moving_piece]
            new_hash ^= self.table[end_idx][moving_piece]

        elif move_type == "capture":
            victim_idx = move_tuple[2]
            end_idx = move_tuple[3]
            victim_piece = board_before_move.state[victim_idx]

            new_hash ^= self.table[start_idx][moving_piece]
            if victim_piece is not None:
                new_hash ^= self.table[victim_idx][victim_piece]
            new_hash ^= self.table[end_idx][moving_piece]

        new_hash ^= self.black_turns_hash

        return new_hash

class TranspositionTable:
    def __init__(self):
            self.table = {}

    def lookup(self, board_hash, depth):
            if board_hash in self.table:
                entry = self.table[board_hash]
                if entry['depth'] >= depth:
                    if entry['value'] is not None:
                        return entry['value']
            return None

    def store(self, board_hash, value, depth):
            if board_hash in self.table:
                if depth < self.table[board_hash]['depth']:
                    return

            self.table[board_hash] = {
                'value': value,
                'depth': depth
            }

    def clear(self):
            self.table.clear()