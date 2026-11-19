from heapq import heappop
import heapq

class Node:
    def __init__(self, state, parent=None, action=None, path_cost=0):
        self.state = state          # Trạng thái hiện tại
        self.parent = parent        # Nút cha
        self.action = action        # Hành động tạo ra nút này
        self.path_cost = path_cost  # Tổng chi phí từ gốc đến đây

    def get_path(self):
        """Hàm lần ngược từ đích về gốc để in ra lộ trình"""
        path = []
        curr = self
        while curr:
            # Tại mỗi bước action tiếp theo là gì và state hiện tại là gì
            path.append((curr.action, curr.state))
            curr = curr.parent

        return path[::-1] # Đảo ngược lại từ Gốc -> Đích'


    def __lt__(self, other):
        return self.path_cost < other.path_cost

    
def ucs(initial_state, is_goal_func, get_successors_func):
    root = Node(state=initial_state)

    frontier = []
    heapq.heappush(frontier,root)

    best_cost = {initial_state: 0}

    while frontier:
        cur_node = heapq.heappop(frontier)

        if cur_node.path_cost > best_cost[cur_node.state]:
            continue

        if is_goal_func(cur_node.state):
            return cur_node.get_path()

        for action, cost, next_state in get_successors_func(cur_node.state):
            new_path_cost = cur_node.path_cost + cost
            if next_state not in best_cost or best_cost[next_state]>new_path_cost:
                child_node = Node(
                    state=next_state,
                    parent=cur_node,
                    action = action,
                    path_cost = new_path_cost
                )

                best_cost[next_state] = new_path_cost
                heapq.heappush(frontier,child_node)

    return None