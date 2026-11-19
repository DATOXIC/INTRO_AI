from collections import deque

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


    def __repr__(self):
        return f"Node(state={self.state}, action={self.action}, cost={self.path_cost})"


def breadth_first_search(initial_state, is_goal_func, get_successors_func):
    root = Node(state = initial_state)

    if is_goal_func(root.state):
        return root.get_path()

    seen_state = set() # Những trạng thái đã xét
    wait_queue = deque()
    wait_queue.append(root)

    while wait_queue:
        cur_node = wait_queue.popleft()
        
        # Đến State mới với Action là gì
        for action, next_state in get_successors_func(cur_node.state):
            
            if next_state not in seen_state:
                child_node = Node(
                    state = next_state,
                    parent = cur_node,
                    action = action,
                    path_cost = cur_node.path_cost + 1
                )
                
                if is_goal_func(child_node.state):
                    return child_node.get_path()

                wait_queue.append(child_node)
                seen_state.add(next_state)

    return None

