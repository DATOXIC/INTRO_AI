from collections import deque
import heapq

class Node:
    def __init__(self, 
    state,
    parent = None ,
    action = None,
    cost = 0):
        self.state = state
        self.parent = parent
        self.action = action
        self.cost = cost

    def __lt__(self, other):
        return self.cost < other.cost

    def get_path(self):

        path = []
        cur_node = self
        while cur_node:
            path.append((cur_node.state,cur_node.action))
            cur_node = cur_node.parent

        return path[::-1]

class Problem:
    def __init__(self, start_state, target_state, get_moves, apply_move, step_cost = None):
        self.start_state = start_state
        self.target_state = target_state
        self.get_moves = get_moves
        self.apply_move = apply_move
        self.step_cost = step_cost

def is_goal(problem, cur_state):
    if callable(problem.target_state):
        return problem.target_state(cur_state)

    return cur_state == problem.target_state

def BFS(problem: Problem):
    initial_node = Node(problem.start_state)

    # FIFO
    frontier = deque()
    frontier.append(initial_node)
    explored = {initial_node.state}

    while frontier:
        cur_node = frontier.popleft()

        if is_goal(problem,cur_node.state):
            return cur_node.get_path()

        for action in problem.get_moves(cur_node.state):
            next_state = problem.apply_move(cur_node.state, action)

            if next_state not in explored:
                explored.add(next_state)
                child = Node(state = next_state, parent=cur_node, action = action)
                frontier.append(child)

    return None

def UCS(problem: Problem):
    initial_node = Node(problem.start_state)

    frontier = []
    heapq.heappush(frontier, initial_node)
    explored = {initial_node.state : 0}

    while frontier:
        cur_node = heapq.heappop(frontier)

        if explored[cur_node.state] < cur_node.cost:
            continue

        if is_goal(problem, cur_node.state):
            return cur_node.get_path()

        for action in problem.get_moves(cur_node.state):
            next_state = problem.apply_move(cur_node.state, action)

            new_cost = cur_node.cost + problem.step_cost(cur_node.state, action)

            if next_state not in explored or explored[next_state] > new_cost:
                child = Node(next_state, cur_node, action = action, cost = new_cost)

                explored[next_state] = new_cost
                heapq.heappush(frontier, child)

    return None

def find_blank(cur_board):
    for row_idx in range(3):
        for col_idx in range(3):
            if cur_board[row_idx][col_idx] == 0:
                return row_idx, col_idx

def actions_8puzzle(cur_board):
    blank_r, blank_c = find_blank(cur_board)
    valid_moves = []

    if blank_r > 0: valid_moves.append("Lên")
    if blank_r < 2: valid_moves.append("Xuống")
    if blank_c > 0: valid_moves.append("Trái")
    if blank_c < 2: valid_moves.append("Phải")

    return valid_moves

def result_8puzzle(cur_board, move):
    blank_r, blank_c = find_blank(cur_board)

    new_r, new_c = blank_r, blank_c
    if move == "Lên":
        new_r -= 1
    elif move == "Xuống":
        new_r += 1
    elif move == "Trái":
        new_c -= 1
    elif move == "Phải":
        new_c += 1

    grid = [list(cur_board[0]), list(cur_board[1]), list(cur_board[2])]
    grid[blank_r][blank_c] = grid[new_r][new_c]
    grid[new_r][new_c] = 0

    return (tuple(grid[0]), tuple(grid[1]), tuple(grid[2]))

def cost_8puzzle(cur_board, move):
    if move in ("Lên", "Xuống"):
        return 1
    return 2

if __name__ == "__main__":

    start_board = ((1, 2, 3), (4, 0, 6), (7, 5, 8))
    target_board = ((1, 2, 3), (4, 5, 6), (7, 8, 0))

    puzzle_bfs = Problem(start_board, target_board, actions_8puzzle, result_8puzzle)

    puzzle_ucs = Problem(start_board, target_board, actions_8puzzle, result_8puzzle, cost_8puzzle)

    print("BFS:", BFS(puzzle_bfs))
    print("UCS:", UCS(puzzle_ucs))