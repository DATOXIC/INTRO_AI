

class Node:
    def __init__(self, state, parent=None, action=None, depth=0):
        self.state = state          # Trạng thái hiện tại
        self.parent = parent        # Nút cha
        self.action = action        # Hành động tạo ra nút này
        self.depth = depth  # Tổng chi phí từ gốc đến đây

    def get_path(self):
        """Hàm lần ngược từ đích về gốc để in ra lộ trình"""
        path = []
        curr = self
        while curr:
            # Tại mỗi bước action tiếp theo là gì và state hiện tại là gì
            path.append((curr.action, curr.state))
            curr = curr.parent

        return path[::-1] # Đảo ngược lại từ Gốc -> Đích'


def dls(initial_state, is_goal_func, get_successors_func, depth):
    root = Node(state= initial_state)
    
    frontier = []
    frontier.append(root)
    seen_state = {}

    seen_state[root.state] = 1

    while frontier:
        cur_node = frontier.pop()

        if is_goal_func(cur_node.state):
            return cur_node.get_path()

        if cur_node.depth >= depth:
            continue


        for action, next_state in get_successors_func(cur_node.state):
            child_depth = cur_node.depth + 1
            if next_state not in seen_state or child_depth < seen_state[next_state]:
                child_node = Node(
                    state= next_state,
                    action = action,
                    parent = cur_node,
                    depth= child_depth
                )

                frontier.append(child_node)
                seen_state[next_state] = child_depth


    return None

def iddfs(initial_state, is_goal_func, get_successors_func, max_limit=100):

    for limit in range(max_limit):
        result = dls(initial_state, is_goal_func, get_successors_func, limit)
        
        if result is not None:
            return result

    return None




def recursive_dls(cur_node, problem, limit, explored):
    # 1. Đạt đích -> trả về đường đi ngay
    if is_goal(problem, cur_node.state):
        return cur_node.get_path()

    # 2. Chạm trần giới hạn -> dừng nhánh này (cutoff)
    if cur_node.depth >= limit:
        return "cutoff"

    cutoff_occurred = False

    # 3. Thử từng nhánh con bằng cách gọi đệ quy
    for action in problem.get_moves(cur_node.state):
        next_state = problem.apply_move(cur_node.state, action)
        child_depth = cur_node.depth + 1

        if next_state not in explored or child_depth < explored[next_state]:
            explored[next_state] = child_depth
            child = Node(next_state, parent=cur_node, action=action, depth=child_depth)

            result = recursive_dls(child, problem, limit, explored)
            
            if result == "cutoff":
                cutoff_occurred = True
            elif result is not None:
                return result  # Tìm thấy đường đi -> thoát luôn

    return "cutoff" if cutoff_occurred else None