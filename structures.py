class Stack:
    def __init__(self):
        self.items = []

    def push(self, item):
        self.items.append(item)

    def pop(self):
        if not self.is_empty():
            return self.items.pop()
        else:
            return None

    def peek(self):
        if not self.is_empty():
            return self.items[-1]
        else:
            return None

    def is_empty(self):
        return len(self.items) == 0

    def size(self):
        return len(self.items)

    def clear(self):
        self.items = []
#za carev drum, zato je kapacitet 5
class Deque:
    def __init__(self, capacity = 5):
        self.items = []
        self.capacity = capacity

    def add_first(self, item):
        if len(self.items) >= self.capacity: #proveravam da li je dek pun, ako jeste oslobadjam mesto
            self.items.pop()
        self.items.insert(0, item)

    def add_last(self, item):
        if len(self.items) >= self.capacity:
            self.items.pop(0)
        self.items.append(item)

    def remove_first(self):
        if not self.is_empty():
            return self.items.pop(0)
        else:
            return None

    def remove_last(self):
        if not self.is_empty():
            return self.items.pop()
        else:
            return None

    def is_empty(self):
        return len(self.items) == 0

    def size(self):
        return len(self.items)

    def get_first(self):
       if not self.is_empty():
           return self.items[0]
       else:
           return None

    def get_last(self):
        if not self.is_empty():
            return self.items[-1]
        else:
            return None

    def to_list(self):
        return list(self.items)


class TreeNode:
    def __init__(self, move_data, game_state_snapshot = None):
        self.move_data = move_data #tekst sta se desava
        self.game_state_snapshot = game_state_snapshot #Stanje igre nakon poteza
        self.children = []
        self.parent = None

class HistoryTree:
    def __init__(self):
        self.root = TreeNode("Почетак партије", None)
        self.current_node = self.root #prati gde se nalazimo u partiji

    def add_move(self, move_data, game_state_snapshot): #dodaje potez u istoriju, cak iako se uradi Undo, samo ce dodati novo dete naroditelja
        for child in self.current_node.children:
            if child.move_data == move_data:
                self.current_node = child
                return child

        new_node = TreeNode(move_data, game_state_snapshot)
        new_node.parent = self.current_node
        self.current_node.children.append(new_node)
        self.current_node = new_node
        return new_node

    def undo_move(self):
        if self.current_node.parent is not None:
            self.current_node = self.current_node.parent
            return True
        return False

    def redo_move(self, child_index = 0):
        if len(self.current_node.children) == 0:
            return False

        if child_index is None:
            child_index = len(self.current_node.children) - 1

        if 0 <= child_index < len(self.current_node.children):
            self.current_node = self.current_node.children[child_index]
            return True
        return False