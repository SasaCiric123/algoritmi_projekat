class Board:
    def __init__(self):
        self.state = [None] * 32 #W_J beli junak, B_J crni junak, W_K beli kraljevic, B_K crni kraljevic, M_K Marko Kraljevic
        self.initialize_pieces()

    @staticmethod
    def row_col_to_index(row, col): #prevodi 2D koordinate u index
        if not (0 <= row < 8 and 0 <= col < 8):
            return None

        if (row + col) % 2 == 0: #crna polja su neparan broj kada se sabere
            return None

        return (row * 4 ) + (col // 2)

    @staticmethod
    def index_to_row_col(index):
        if not ( 0 <= index < 32):
            return None
        row = index // 4
        if row % 2 == 0:
            col = (index % 4) * 2 + 1
        else:
            col = (index % 4) * 2
        return row, col

    def initialize_pieces(self):
        for i in range(12):
            self.state[i] = "B_J"
        for i in range(12,20):
            self.state[i] = None
        for i in range(20,32):
            self.state[i] = "W_J"

    def is_brazda(self, index):
        return index == 12 or index == 19

    def copy_board(self):
        new_board = Board()
        new_board.state = list(self.state)
        return new_board

    def get_piece_color(self, piece):
        if piece in ["W_K", "W_J", "W_M"]:
            return "W"
        if piece in ["B_K", "B_J", "B_M"]:
            return "B"
        return None

    def is_kraljevic(self,piece):
        return piece is not None and ("_K" in piece or "_M" in piece)

    def get_all_quiet_moves(self, player_color, sarac_available=False):
        moves = []
        for index in range (32):
            piece = self.state[index]
            if piece and self.get_piece_color(piece) == player_color:
                moves.extend(self.get_piece_quiet_moves(index, sarac_available=sarac_available))
        return moves

    def get_piece_quiet_moves(self, index, sarac_available=False):
        piece = self.state[index]
        if not piece:
            return []
        moves = []
        row, col = self.index_to_row_col(index)
        my_color = self.get_piece_color(piece)
        is_marko= piece in ["W_M", "B_M"]
        has_sarac = is_marko or sarac_available

        if piece == "W_J":
            directions = [(-1,-1), (-1,1)] #gore levo i gore desno
        elif piece == "B_J":
            directions = [(1,-1), (1,1)]  #dole levo i dole desno
        else:
            directions = [(-1,-1), (-1,1), (1,-1), (1,1)]

        if piece in ["B_J", "W_J"]:
            for dr, dc in directions:
                new_row, new_col = row + dr, col + dc
                new_index = self.row_col_to_index(new_row, new_col)
                if new_index is not None and self.state[new_index] is None:
                    moves.append((index, new_index))
        else:
            for dr, dc in directions:
                step = 1
                while True:
                    new_row = row + dr * step
                    new_col = col + dc * step
                    new_index = self.row_col_to_index(new_row, new_col)
                    if new_index is None:
                        break

                    if self.state[new_index] is None:
                        moves.append((index, new_index))
                        step += 1
                    elif has_sarac and self.get_piece_color(self.state[new_index]) == my_color:
                        jump_row = row + dr * (step + 1)
                        jump_col = col + dc * (step + 1)
                        jump_index = self.row_col_to_index(jump_row, jump_col)
                        if jump_index is not None and self.state[jump_index] is None:
                            moves.append((index, jump_index, 'sarac'))
                        break
                    else:
                        break
        return moves

    def get_all_capture_moves(self, player_color, topuz_owner=None, oklop_targets=None):
        capture_moves = []
        for index in range (32):
            piece = self.state[index]
            if piece and self.get_piece_color(piece) == player_color:
                capture_moves.extend(self.get_piece_capture_moves(index, topuz_owner=topuz_owner, oklop_targets=oklop_targets))
        return capture_moves

    def get_piece_capture_moves(self, index, topuz_owner=None, oklop_targets=None):
        piece = self.state[index]
        if not piece:
            return []
        moves = []
        row, col = self.index_to_row_col(index)
        my_color = self.get_piece_color(piece)

        if oklop_targets is None:
            oklop_targets = set()
        has_topuz = (topuz_owner == index)

        if piece == "W_J":
            directions = [(-1,-1), (-1,1)]
        elif piece == "B_J":
            directions = [(1,-1), (1,1)]
        else:
            directions = [(-1,-1), (-1,1), (1,-1), (1,1)]

        if piece in ["W_J", "B_J"]:
            for dr, dc in directions:
                victim_row, victim_col = row + dr, col + dc
                victim_index = self.row_col_to_index(victim_row, victim_col)

                end_row, end_col = row + dr * 2, col + dc * 2
                end_index = self.row_col_to_index(end_row, end_col)
                if victim_index is None:
                    continue
                if victim_index is not None:
                    victim_piece = self.state[victim_index]
                    if victim_piece and self.get_piece_color(victim_piece) != my_color and victim_index not in oklop_targets:
                        if victim_index not in oklop_targets:
                            if has_topuz:
                                moves.append((index, victim_index, victim_index, 'topuz'))
                            else:
                                if end_index is not None and self.state[end_index] is None:
                                    moves.append((index, victim_index, end_index))
        else:
            for dr, dc in directions:
                step = 1
                victim_index = None

                while True:
                    next_row, next_col = row + dr * step, col + dc * step
                    next_index = self.row_col_to_index(next_row, next_col)
                    if next_index is None:
                        break

                    current_piece = self.state[next_index]

                    if current_piece is None:################
                        if victim_index is not None:
                            if has_topuz:
                                moves.append((index, victim_index, victim_index, 'topuz'))
                            else:
                                moves.append((index, victim_index, next_index))
                                break
                        step +=1
                    elif self.get_piece_color(current_piece) == my_color:
                        break
                    else:
                        if victim_index is not None:
                            break
                        if next_index not in oklop_targets:
                            victim_index = next_index
                        else:
                            break
                        step +=1
        return moves

    def make_move(self, start_index, end_index, victim_index= None):
        piece = self.state[start_index]###############
        self.state[start_index] = None

        if victim_index is not None:#proverava se zbog topuza
            self.state[victim_index] = None
        self.state[end_index] = piece
        promoted = self.check_promotion(end_index)
        return promoted

    def check_promotion(self, index):
        piece = self.state[index]
        if not piece:
            return False

        row, col = self.index_to_row_col(index)

        if piece == "W_J" and row == 0:
            self.state[index] = "W_K"
            return True

        if piece == "B_J" and row == 7:
            self.state[index] = "B_K"
            return True

        return False

    def promote_to_kraljevic(self, index): #za relikviju
        piece = self.state[index]
        if not piece:
            return False
        color = self.get_piece_color(piece)
        if color == "W":
            self.state[index] = "W_K"
        elif color == "B":
            self.state[index] = "B_K"
        return True

    def promote_to_marko(self, index):
        piece = self.state[index]
        if not piece:
            return False
        color = self.get_piece_color(piece)
        if color == "W":
            self.state[index] = "W_M"
        elif color == "B":
            self.state[index] = "B_M"
        return True

    def get_nearest_enemy(self, index, my_color):
        row, col = self.index_to_row_col(index)
        best = None
        best_dist = float('inf')
        best_real_dist = float('inf')
        for i in range(32):
            piece = self.state[i]
            if piece and self.get_piece_color(piece) != my_color:
                r,c = self.index_to_row_col(i)
                dist = max(abs(r-row),abs(c-col))
                real_dist = (r - row) ** 2 + (c - col) ** 2
                if dist < best_dist or (dist == best_dist and real_dist < best_real_dist):
                    best_real_dist = real_dist
                    best_dist = dist
                    best = i
        return best
