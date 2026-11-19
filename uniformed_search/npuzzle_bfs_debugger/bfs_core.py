"""Core BFS engine and generalized n-puzzle domain with step-by-step debug tracing."""

from __future__ import annotations

import random
from typing import Any, Callable

Board = tuple[tuple[int, ...], ...]
Move = str
ALLOWED_SIZES = (2, 3, 4)
MOVE_ORDER: tuple[Move, ...] = ("Lên", "Xuống", "Trái", "Phải")
MOVE_DELTAS: dict[Move, tuple[int, int]] = {
    "Lên": (-1, 0),
    "Xuống": (1, 0),
    "Trái": (0, -1),
    "Phải": (0, 1),
}


class Node:
    """Search tree node following the lecture slide structure."""

    def __init__(
        self,
        state: Board,
        parent: Node | None = None,
        action: Move | None = None,
        depth: int = 0,
        node_id: int = 0,
    ) -> None:
        self.state = state
        self.parent = parent
        self.action = action
        self.depth = depth
        self.node_id = node_id


class Problem:
    """Problem formulation bundling start state, goal condition, actions, and transition model."""

    def __init__(
        self,
        start_state: Board,
        target_state: Board | Callable[[Board], bool],
        get_moves: Callable[[Board], list[Move]],
        apply_move: Callable[[Board, Move], Board],
    ) -> None:
        self.start_state = start_state
        self.target_state = target_state
        self.get_moves = get_moves
        self.apply_move = apply_move


def is_goal(puzzle: Problem, cur_state: Board) -> bool:
    """Return True if cur_state satisfies the problem's goal condition."""
    if callable(puzzle.target_state):
        return bool(puzzle.target_state(cur_state))
    return cur_state == puzzle.target_state


def Queue() -> list[Node]:
    """Create an empty FIFO queue."""
    return []


def enqueue(wait_list: list[Node], item: Node) -> None:
    """Append an item to the tail of the FIFO queue."""
    wait_list.append(item)


def is_empty(wait_list: list[Node]) -> bool:
    """Check whether the FIFO queue is empty."""
    return len(wait_list) == 0


def dequeue(wait_list: list[Node]) -> Node | None:
    """Pop and return the front item of the FIFO queue, or None if empty."""
    if is_empty(wait_list):
        return None
    first_item = wait_list[0]
    del wait_list[0]
    return first_item


def child_node(puzzle: Problem, prev_node: Node, move: Move, node_id: int = 0) -> Node:
    """Generate a child Node by applying move to prev_node.state."""
    next_state = puzzle.apply_move(prev_node.state, move)
    return Node(
        state=next_state,
        parent=prev_node,
        action=move,
        depth=prev_node.depth + 1,
        node_id=node_id,
    )


def solution(goal_node: Node) -> list[Board]:
    """Trace states from root to goal_node."""
    trace: list[Board] = []
    curr: Node | None = goal_node
    while curr is not None:
        trace.append(curr.state)
        curr = curr.parent
    trace.reverse()
    return trace


def solution_node_ids(goal_node: Node) -> list[int]:
    """Trace node IDs from root to goal_node."""
    ids: list[int] = []
    curr: Node | None = goal_node
    while curr is not None:
        ids.append(curr.node_id)
        curr = curr.parent
    ids.reverse()
    return ids


def BFS(puzzle: Problem) -> list[Board] | None:
    """Standard Graph-Search BFS matching the lecture slide pseudocode."""
    root = Node(puzzle.start_state)
    if is_goal(puzzle, root.state):
        return solution(root)

    wait_queue = Queue()
    enqueue(wait_queue, root)
    seen_states: set[Board] = set()

    while not is_empty(wait_queue):
        cur_node = dequeue(wait_queue)
        assert cur_node is not None
        seen_states.add(cur_node.state)

        for move in puzzle.get_moves(cur_node.state):
            next_node = child_node(puzzle, cur_node, move)
            in_queue = any(queued.state == next_node.state for queued in wait_queue)
            if next_node.state not in seen_states and not in_queue:
                if is_goal(puzzle, next_node.state):
                    return solution(next_node)
                enqueue(wait_queue, next_node)
    return None


def make_goal_board(size: int) -> Board:
    """Build standard goal board for a size x size n-puzzle (1..n, 0 at bottom-right)."""
    if size not in ALLOWED_SIZES:
        raise ValueError(f"Kích thước bảng phải thuộc {ALLOWED_SIZES}, nhận được: {size}")
    nums = list(range(1, size * size)) + [0]
    return tuple(tuple(nums[r * size : (r + 1) * size]) for r in range(size))


def validate_board(raw_board: Any, expected_size: int | None = None) -> Board:
    """Validate and normalize an incoming 2D board into an immutable Board tuple.

    Raises:
        ValueError: If structure, dimensions, or tile values are invalid.
    """
    if not isinstance(raw_board, (list, tuple)) or len(raw_board) == 0:
        raise ValueError("Bảng phải là danh sách 2 chiều không rỗng.")

    size = len(raw_board)
    if size not in ALLOWED_SIZES:
        raise ValueError(f"Chỉ hỗ trợ bảng kích thước {ALLOWED_SIZES}, nhận được {size}x{size}.")
    if expected_size is not None and size != expected_size:
        raise ValueError(f"Kích thước bảng ({size}x{size}) không khớp size={expected_size}.")

    rows: list[tuple[int, ...]] = []
    seen_tiles: list[int] = []
    for row_idx, row in enumerate(raw_board):
        if not isinstance(row, (list, tuple)) or len(row) != size:
            raise ValueError(f"Hàng {row_idx} phải có đúng {size} phần tử.")
        parsed_row: list[int] = []
        for val in row:
            if isinstance(val, bool) or not isinstance(val, int):
                raise ValueError(f"Giá trị ô phải là số nguyên, nhận được: {val!r}")
            parsed_row.append(val)
            seen_tiles.append(val)
        rows.append(tuple(parsed_row))

    expected_tiles = set(range(size * size))
    if set(seen_tiles) != expected_tiles or len(seen_tiles) != size * size:
        raise ValueError(
            f"Bảng {size}x{size} phải chứa đủ và duy nhất các số từ 0 đến {size * size - 1}."
        )

    return tuple(rows)


def find_blank(board: Board) -> tuple[int, int]:
    """Return (row, col) coordinates of the blank tile (0)."""
    size = len(board)
    for r in range(size):
        for c in range(size):
            if board[r][c] == 0:
                return r, c
    raise ValueError("Không tìm thấy ô trống (0) trên bảng.")


def actions_npuzzle(board: Board) -> list[Move]:
    """Return valid blank-tile moves for any k x k n-puzzle board."""
    size = len(board)
    blank_r, blank_c = find_blank(board)
    valid_moves: list[Move] = []
    if blank_r > 0:
        valid_moves.append("Lên")
    if blank_r < size - 1:
        valid_moves.append("Xuống")
    if blank_c > 0:
        valid_moves.append("Trái")
    if blank_c < size - 1:
        valid_moves.append("Phải")
    return valid_moves


def result_npuzzle(board: Board, move: Move) -> Board:
    """Return the new Board after sliding the blank tile in the given direction."""
    if move not in MOVE_DELTAS:
        raise ValueError(f"Hướng di chuyển không hợp lệ: {move!r}")
    size = len(board)
    blank_r, blank_c = find_blank(board)
    dr, dc = MOVE_DELTAS[move]
    new_r, new_c = blank_r + dr, blank_c + dc
    if not (0 <= new_r < size and 0 <= new_c < size):
        raise ValueError(f"Nước đi {move!r} từ {(blank_r, blank_c)} vượt ra ngoài biên bảng {size}x{size}.")

    grid = [list(row) for row in board]
    grid[blank_r][blank_c] = grid[new_r][new_c]
    grid[new_r][new_c] = 0
    return tuple(tuple(row) for row in grid)


def count_inversions(board: Board) -> int:
    """Count permutation inversions of non-zero tiles in row-major order."""
    flat = [val for row in board for val in row if val != 0]
    inversions = 0
    for i in range(len(flat)):
        for j in range(i + 1, len(flat)):
            if flat[i] > flat[j]:
                inversions += 1
    return inversions


def analyze_solvability(start_board: Board, target_board: Board) -> dict[str, Any]:
    """Check whether start_board can reach target_board and explain the parity math."""
    size = len(start_board)
    start_inv = count_inversions(start_board)
    target_inv = count_inversions(target_board)
    start_blank_r, _ = find_blank(start_board)
    target_blank_r, _ = find_blank(target_board)

    if size % 2 == 1:
        start_parity = start_inv % 2
        target_parity = target_inv % 2
        solvable = start_parity == target_parity
        formula = "Bảng kích thước lẻ (k lẻ): Giải được ⇔ số nghịch thế (inversions) cùng tính chẵn/lẻ với Đích."
        detail = (
            f"Start có {start_inv} nghịch thế ({'chẵn' if start_parity == 0 else 'lẻ'}), "
            f"Goal có {target_inv} nghịch thế ({'chẵn' if target_parity == 0 else 'lẻ'}) "
            f"→ {'CÙNG tính chẵn/lẻ (GIẢI ĐƯỢC)' if solvable else 'KHÁC tính chẵn/lẻ (VÔ NGHIỆM)'}."
        )
    else:
        start_parity = (start_inv + start_blank_r) % 2
        target_parity = (target_inv + target_blank_r) % 2
        solvable = start_parity == target_parity
        formula = (
            "Bảng kích thước chẵn (k chẵn): Giải được ⇔ (số nghịch thế + chỉ số hàng của ô 0) "
            "cùng tính chẵn/lẻ với Đích."
        )
        detail = (
            f"Start: ({start_inv} + hàng {start_blank_r}) mod 2 = {start_parity}, "
            f"Goal: ({target_inv} + hàng {target_blank_r}) mod 2 = {target_parity} "
            f"→ {'BẰNG NHAU (GIẢI ĐƯỢC)' if solvable else 'KHÁC NHAU (VÔ NGHIỆM)'}."
        )

    return {
        "solvable": solvable,
        "size": size,
        "start_inversions": start_inv,
        "target_inversions": target_inv,
        "start_blank_row": start_blank_r,
        "target_blank_row": target_blank_r,
        "start_parity": start_parity,
        "target_parity": target_parity,
        "formula": formula,
        "explanation": detail,
    }


def is_solvable(start_board: Board, target_board: Board) -> bool:
    """Return True if start_board is reachable from target_board."""
    return bool(analyze_solvability(start_board, target_board)["solvable"])


def manhattan_distance(board: Board, target_board: Board) -> int:
    """Compute Manhattan distance heuristic h1 (sum of L1 distances of tiles 1..n)."""
    size = len(board)
    goal_pos: dict[int, tuple[int, int]] = {}
    for r in range(size):
        for c in range(size):
            val = target_board[r][c]
            if val != 0:
                goal_pos[val] = (r, c)

    total = 0
    for r in range(size):
        for c in range(size):
            val = board[r][c]
            if val != 0:
                gr, gc = goal_pos[val]
                total += abs(r - gr) + abs(c - gc)
    return total


def misplaced_tiles(board: Board, target_board: Board) -> int:
    """Count non-zero tiles not in their target position (Hamming heuristic)."""
    size = len(board)
    count = 0
    for r in range(size):
        for c in range(size):
            val = board[r][c]
            if val != 0 and val != target_board[r][c]:
                count += 1
    return count


def shuffle_solvable(
    target_board: Board,
    steps: int,
    seed: int | None = None,
) -> Board:
    """Generate a guaranteed-solvable board by applying random valid moves from target_board.

    Avoids immediately undoing the previous move so the resulting board is non-trivial.
    """
    if steps < 0 or steps > 50:
        raise ValueError("Số bước xáo trộn phải nằm trong khoảng [0, 50].")
    rng = random.Random(seed)
    opposite: dict[Move, Move] = {
        "Lên": "Xuống",
        "Xuống": "Lên",
        "Trái": "Phải",
        "Phải": "Trái",
    }

    cur = target_board
    last_move: Move | None = None
    visited_walk: set[Board] = {cur}
    for _ in range(steps):
        moves = actions_npuzzle(cur)
        if last_move is not None and len(moves) > 1:
            filtered = [m for m in moves if m != opposite[last_move]]
            if filtered:
                moves = filtered
        fresh = [m for m in moves if result_npuzzle(cur, m) not in visited_walk]
        chosen = rng.choice(fresh if fresh else moves)
        cur = result_npuzzle(cur, chosen)
        visited_walk.add(cur)
        last_move = chosen
    return cur


def get_bfs_source_lines(graph_search: bool = True, early_goal_test: bool = True) -> list[dict[str, Any]]:
    """Return structured Python BFS lines with semantic tags matching the active options."""
    lines: list[tuple[str, str]] = [
        ("def", "def BFS(problem):"),
        ("init_root", "    root = Node(problem.start_state)"),
    ]
    if early_goal_test:
        lines.append(("check_root_goal", "    if is_goal(problem, root.state): return solution(root)"))
    lines.append(("init_queue", "    frontier = Queue(); enqueue(frontier, root)"))
    if graph_search:
        lines.append(("init_explored", "    explored = set()"))
    lines.append(("while_loop", "    while not is_empty(frontier):"))
    lines.append(("dequeue", "        cur_node = dequeue(frontier)"))
    if not early_goal_test:
        lines.append(("check_late_goal", "        if is_goal(problem, cur_node.state): return solution(cur_node)"))
    if graph_search:
        lines.append(("add_explored", "        explored.add(cur_node.state)"))
    lines.append(("for_move", "        for move in problem.get_moves(cur_node.state):"))
    lines.append(("make_child", "            child = child_node(problem, cur_node, move)"))
    if graph_search:
        lines.append(("check_duplicate", "            if child.state not in explored and child.state not in frontier:"))
        indent = "                "
    else:
        indent = "            "
    if early_goal_test:
        lines.append(("check_early_goal", f"{indent}if is_goal(problem, child.state): return solution(child)"))
    lines.append(("enqueue_child", f"{indent}enqueue(frontier, child)"))
    lines.append(("return_none", "    return None"))

    return [
        {"line": idx + 1, "tag": tag, "code": code}
        for idx, (tag, code) in enumerate(lines)
    ]


def get_presets() -> list[dict[str, Any]]:
    """Return curated n-puzzle learning presets across 2x2, 3x3, and 4x4 sizes."""
    return [
        {
            "id": "p3_easy",
            "name": "3-Puzzle (2×2) — 3 bước",
            "size": 2,
            "description": "Bảng nhỏ nhất (2×2), cực kỳ dễ quan sát toàn bộ cây tìm kiếm và cơ chế lọc trùng.",
            "start_board": [[0, 2], [1, 3]],
            "target_board": [[1, 2], [3, 0]],
        },
        {
            "id": "p8_slide",
            "name": "8-Puzzle (3×3) — Mẫu slide (2 bước)",
            "size": 3,
            "description": "Đúng bài mẫu trong notebook buổi 5, lời giải tối ưu 2 bước.",
            "start_board": [[1, 2, 3], [4, 0, 6], [7, 5, 8]],
            "target_board": [[1, 2, 3], [4, 5, 6], [7, 8, 0]],
        },
        {
            "id": "p8_branch",
            "name": "8-Puzzle (3×3) — Phân nhánh rõ (5 bước)",
            "size": 3,
            "description": "Cách đích 5 bước: thấy rõ sóng BFS mở rộng tầng 0→5, nhiều nhánh trùng bị cắt ở frontier & explored.",
            "start_board": [[1, 2, 3], [5, 0, 6], [4, 7, 8]],
            "target_board": [[1, 2, 3], [4, 5, 6], [7, 8, 0]],
        },
        {
            "id": "p8_medium",
            "name": "8-Puzzle (3×3) — Trung bình (7 bước)",
            "size": 3,
            "description": "Cách đích 7 bước: minh họa sự tăng trưởng nhanh của kích thước frontier theo O(b^d).",
            "start_board": [[1, 3, 6], [4, 2, 0], [7, 5, 8]],
            "target_board": [[1, 2, 3], [4, 5, 6], [7, 8, 0]],
        },
        {
            "id": "p8_unsolvable",
            "name": "8-Puzzle (3×3) — Vô nghiệm (1 nghịch thế lẻ)",
            "size": 3,
            "description": "Hoán đổi ô 7 và 8: khác tính chẵn/lẻ số nghịch thế nên không bao giờ tới đích được.",
            "start_board": [[1, 2, 3], [4, 5, 6], [8, 7, 0]],
            "target_board": [[1, 2, 3], [4, 5, 6], [7, 8, 0]],
        },
        {
            "id": "p15_easy",
            "name": "15-Puzzle (4×4) — 4 bước",
            "size": 4,
            "description": "Mở rộng sang bảng 4×4 (15-puzzle) với 4 bước tối ưu, chứng minh thuật toán hoạt động tổng quát cho mọi n.",
            "start_board": [
                [1, 2, 3, 4],
                [5, 6, 7, 8],
                [9, 10, 0, 11],
                [13, 14, 15, 12],
            ],
            "target_board": [
                [1, 2, 3, 4],
                [5, 6, 7, 8],
                [9, 10, 11, 12],
                [13, 14, 15, 0],
            ],
        },
    ]


def BFS_trace(
    start_board: Board,
    target_board: Board,
    *,
    graph_search: bool = True,
    early_goal_test: bool = True,
    max_nodes: int = 300,
) -> dict[str, Any]:
    """Run instrumented BFS on an n-puzzle and return complete micro/macro debug trace.

    Args:
        start_board: Validated starting k x k board.
        target_board: Validated goal k x k board of the same size.
        graph_search: If True, prune duplicates in explored and frontier; if False, run Tree Search.
        early_goal_test: If True, check goal on child generation; if False, check on dequeue.
        max_nodes: Maximum number of expanded nodes before stopping safely.

    Returns:
        Dictionary containing nodes, step-by-step events, source lines, solvability, and summary.
    """
    if len(start_board) != len(target_board):
        raise ValueError("start_board và target_board phải cùng kích thước.")
    if not (1 <= max_nodes <= 3000):
        raise ValueError("max_nodes phải nằm trong khoảng [1, 3000].")

    puzzle = Problem(start_board, target_board, actions_npuzzle, result_npuzzle)
    solvability = analyze_solvability(start_board, target_board)
    source_lines = get_bfs_source_lines(graph_search=graph_search, early_goal_test=early_goal_test)
    tag_to_line = {item["tag"]: item["line"] for item in source_lines}

    nodes: list[dict[str, Any]] = []
    steps: list[dict[str, Any]] = []
    next_id = 0
    macro_counter = 0

    metrics = {
        "expanded": 0,
        "generated": 0,
        "skipped_explored": 0,
        "skipped_frontier": 0,
        "max_frontier_size": 0,
        "current_depth": 0,
    }

    def register_node(
        node: Node,
        parent_board: Board | None,
        created_step: int,
        *,
        is_duplicate: bool = False,
        duplicate_of: int | None = None,
        duplicate_reason: str | None = None,
    ) -> dict[str, Any]:
        blank_to = list(find_blank(node.state))
        blank_from: list[int] | None = None
        moved_tile: int | None = None
        if parent_board is not None:
            pr, pc = find_blank(parent_board)
            blank_from = [pr, pc]
            moved_tile = node.state[pr][pc]

        rec = {
            "id": node.node_id,
            "state": [list(row) for row in node.state],
            "parent_id": node.parent.node_id if node.parent is not None else None,
            "action": node.action,
            "depth": node.depth,
            "manhattan": manhattan_distance(node.state, target_board),
            "misplaced": misplaced_tiles(node.state, target_board),
            "inversions": count_inversions(node.state),
            "moved_tile": moved_tile,
            "blank_from": blank_from,
            "blank_to": blank_to,
            "is_duplicate": is_duplicate,
            "duplicate_of": duplicate_of,
            "duplicate_reason": duplicate_reason,
            "created_step": created_step,
            "expanded_step": None,
        }
        nodes.append(rec)
        return rec

    wait_queue: list[Node] = Queue()
    explored_map: dict[Board, int] = {}
    explored_order: list[int] = []
    frontier_map: dict[Board, int] = {}

    def record_step(
        *,
        event_type: str,
        code_tag: str,
        message: str,
        is_macro: bool,
        cur_id: int | None,
        candidate_id: int | None = None,
        collision_id: int | None = None,
        solution_ids: list[int] | None = None,
        local_vars: dict[str, Any] | None = None,
    ) -> int:
        nonlocal macro_counter
        if is_macro:
            macro_counter += 1
        step_idx = len(steps)
        metrics["max_frontier_size"] = max(metrics["max_frontier_size"], len(wait_queue))
        snap_metrics = {
            **metrics,
            "frontier_size": len(wait_queue),
            "explored_size": len(explored_order),
        }
        steps.append(
            {
                "index": step_idx,
                "macro_index": macro_counter,
                "is_macro": is_macro,
                "event_type": event_type,
                "code_tag": code_tag,
                "line": tag_to_line.get(code_tag, 1),
                "cur_id": cur_id,
                "candidate_id": candidate_id,
                "collision_id": collision_id,
                "frontier_ids": [n.node_id for n in wait_queue],
                "explored_ids": list(explored_order),
                "solution_ids": solution_ids,
                "vars": local_vars or {},
                "message": message,
                "metrics": snap_metrics,
            }
        )
        return step_idx

    root = Node(puzzle.start_state, parent=None, action=None, depth=0, node_id=next_id)
    next_id += 1
    metrics["generated"] += 1
    register_node(root, parent_board=None, created_step=0)

    if early_goal_test and is_goal(puzzle, root.state):
        sol_ids = solution_node_ids(root)
        record_step(
            event_type="goal_init",
            code_tag="check_root_goal",
            message="Trạng thái xuất phát #0 đã chính là ĐÍCH (0 bước)!",
            is_macro=True,
            cur_id=root.node_id,
            solution_ids=sol_ids,
            local_vars={"root": "#0", "is_goal": True},
        )
        return _build_result(
            status="solved",
            size=len(start_board),
            start_board=start_board,
            target_board=target_board,
            graph_search=graph_search,
            early_goal_test=early_goal_test,
            max_nodes=max_nodes,
            solvability=solvability,
            source_lines=source_lines,
            nodes=nodes,
            steps=steps,
            solution_ids=sol_ids,
        )

    enqueue(wait_queue, root)
    frontier_map[root.state] = root.node_id
    record_step(
        event_type="init",
        code_tag="init_queue",
        message="Khởi tạo: tạo nút gốc #0 (depth=0) và đẩy vào đầu hàng đợi frontier.",
        is_macro=True,
        cur_id=root.node_id,
        local_vars={"root": "#0", "frontier_len": 1, "explored_len": 0},
    )

    final_status = "failure"
    final_solution_ids: list[int] | None = None

    while not is_empty(wait_queue):
        if metrics["expanded"] >= max_nodes:
            final_status = "limit_reached"
            record_step(
                event_type="limit_reached",
                code_tag="while_loop",
                message=(
                    f"Đã chạm giới hạn an toàn {max_nodes} nút mở rộng — dừng tìm kiếm để tránh treo máy "
                    f"({'Tree Search không lọc trùng lặp' if not graph_search else 'không gian trạng thái quá sâu'})."
                ),
                is_macro=True,
                cur_id=None,
                local_vars={"max_nodes": max_nodes, "frontier_len": len(wait_queue)},
            )
            break

        cur_node = dequeue(wait_queue)
        assert cur_node is not None
        if frontier_map.get(cur_node.state) == cur_node.node_id:
            del frontier_map[cur_node.state]

        metrics["expanded"] += 1
        metrics["current_depth"] = cur_node.depth
        dequeue_step = record_step(
            event_type="dequeue",
            code_tag="dequeue",
            message=(
                f"Dequeue nút #{cur_node.node_id} (depth={cur_node.depth}, "
                f"action={cur_node.action or 'ROOT'}) từ ĐẦU hàng đợi frontier."
            ),
            is_macro=True,
            cur_id=cur_node.node_id,
            local_vars={
                "cur_node": f"#{cur_node.node_id}",
                "depth": cur_node.depth,
                "frontier_len": len(wait_queue),
            },
        )
        nodes[cur_node.node_id]["expanded_step"] = dequeue_step

        if not early_goal_test and is_goal(puzzle, cur_node.state):
            final_status = "solved"
            final_solution_ids = solution_node_ids(cur_node)
            record_step(
                event_type="goal_late",
                code_tag="check_late_goal",
                message=(
                    f"Late Goal Test: nút #{cur_node.node_id} (depth={cur_node.depth}) chính là ĐÍCH! "
                    f"Truy vết ngược qua parent → lời giải {len(final_solution_ids) - 1} bước."
                ),
                is_macro=True,
                cur_id=cur_node.node_id,
                solution_ids=final_solution_ids,
                local_vars={"cur_node": f"#{cur_node.node_id}", "is_goal": True},
            )
            break

        if graph_search:
            if cur_node.state not in explored_map:
                explored_map[cur_node.state] = cur_node.node_id
                explored_order.append(cur_node.node_id)
            record_step(
                event_type="explore",
                code_tag="add_explored",
                message=f"Thêm trạng thái của nút #{cur_node.node_id} vào tập đã duyệt explored (tổng {len(explored_order)} trạng thái).",
                is_macro=False,
                cur_id=cur_node.node_id,
                local_vars={"cur_node": f"#{cur_node.node_id}", "explored_len": len(explored_order)},
            )

        for move in puzzle.get_moves(cur_node.state):
            cand_id = next_id
            next_id += 1
            cand = child_node(puzzle, cur_node, move, node_id=cand_id)
            metrics["generated"] += 1

            in_explored = graph_search and (cand.state in explored_map)
            in_frontier = graph_search and (cand.state in frontier_map)

            if in_explored:
                collision_id = explored_map[cand.state]
                metrics["skipped_explored"] += 1
                register_node(
                    cand,
                    parent_board=cur_node.state,
                    created_step=len(steps),
                    is_duplicate=True,
                    duplicate_of=collision_id,
                    duplicate_reason="explored",
                )
                record_step(
                    event_type="skip_explored",
                    code_tag="check_duplicate",
                    message=(
                        f"Thử '{move}' từ #{cur_node.node_id} → sinh #{cand_id}, NHƯNG BỎ QUA vì trạng thái này "
                        f"đã nằm trong EXPLORED (trùng với nút #{collision_id})."
                    ),
                    is_macro=False,
                    cur_id=cur_node.node_id,
                    candidate_id=cand_id,
                    collision_id=collision_id,
                    local_vars={
                        "cur_node": f"#{cur_node.node_id}",
                        "move": move,
                        "child": f"#{cand_id}",
                        "in_explored": True,
                        "in_frontier": False,
                        "collision": f"#{collision_id} (explored)",
                    },
                )
                continue

            if in_frontier:
                collision_id = frontier_map[cand.state]
                metrics["skipped_frontier"] += 1
                register_node(
                    cand,
                    parent_board=cur_node.state,
                    created_step=len(steps),
                    is_duplicate=True,
                    duplicate_of=collision_id,
                    duplicate_reason="frontier",
                )
                record_step(
                    event_type="skip_frontier",
                    code_tag="check_duplicate",
                    message=(
                        f"Thử '{move}' từ #{cur_node.node_id} → sinh #{cand_id}, NHƯNG BỎ QUA vì trạng thái này "
                        f"đang chờ trong FRONTIER (trùng với nút #{collision_id})."
                    ),
                    is_macro=False,
                    cur_id=cur_node.node_id,
                    candidate_id=cand_id,
                    collision_id=collision_id,
                    local_vars={
                        "cur_node": f"#{cur_node.node_id}",
                        "move": move,
                        "child": f"#{cand_id}",
                        "in_explored": False,
                        "in_frontier": True,
                        "collision": f"#{collision_id} (frontier)",
                    },
                )
                continue

            register_node(cand, parent_board=cur_node.state, created_step=len(steps))

            if early_goal_test and is_goal(puzzle, cand.state):
                final_status = "solved"
                final_solution_ids = solution_node_ids(cand)
                record_step(
                    event_type="goal_early",
                    code_tag="check_early_goal",
                    message=(
                        f"Thử '{move}' từ #{cur_node.node_id} → sinh #{cand_id} (depth={cand.depth}): "
                        f"ĐẠT ĐÍCH NGAY (Early Goal Test)! Đường ngắn nhất: {len(final_solution_ids) - 1} bước."
                    ),
                    is_macro=True,
                    cur_id=cur_node.node_id,
                    candidate_id=cand_id,
                    solution_ids=final_solution_ids,
                    local_vars={
                        "cur_node": f"#{cur_node.node_id}",
                        "move": move,
                        "child": f"#{cand_id}",
                        "is_goal": True,
                    },
                )
                break

            enqueue(wait_queue, cand)
            if cand.state not in frontier_map:
                frontier_map[cand.state] = cand.node_id
            record_step(
                event_type="enqueue",
                code_tag="enqueue_child",
                message=(
                    f"Thử '{move}' từ #{cur_node.node_id} → sinh trạng thái mới #{cand_id} (depth={cand.depth}) "
                    f"và ENQUEUE vào cuối frontier."
                ),
                is_macro=False,
                cur_id=cur_node.node_id,
                candidate_id=cand_id,
                local_vars={
                    "cur_node": f"#{cur_node.node_id}",
                    "move": move,
                    "child": f"#{cand_id}",
                    "in_explored": False,
                    "in_frontier": False,
                    "frontier_len": len(wait_queue),
                },
            )

        if final_status == "solved":
            break

    if final_status == "failure":
        record_step(
            event_type="failure",
            code_tag="return_none",
            message="Hàng đợi frontier đã rỗng mà không tìm thấy ĐÍCH — Bài toán VÔ NGHIỆM!",
            is_macro=True,
            cur_id=None,
            local_vars={"frontier_len": 0, "explored_len": len(explored_order)},
        )

    return _build_result(
        status=final_status,
        size=len(start_board),
        start_board=start_board,
        target_board=target_board,
        graph_search=graph_search,
        early_goal_test=early_goal_test,
        max_nodes=max_nodes,
        solvability=solvability,
        source_lines=source_lines,
        nodes=nodes,
        steps=steps,
        solution_ids=final_solution_ids,
    )


def _build_result(
    *,
    status: str,
    size: int,
    start_board: Board,
    target_board: Board,
    graph_search: bool,
    early_goal_test: bool,
    max_nodes: int,
    solvability: dict[str, Any],
    source_lines: list[dict[str, Any]],
    nodes: list[dict[str, Any]],
    steps: list[dict[str, Any]],
    solution_ids: list[int] | None,
) -> dict[str, Any]:
    last_metrics = steps[-1]["metrics"] if steps else {}
    expanded = last_metrics.get("expanded", 0)
    generated = last_metrics.get("generated", 0)
    avg_branching = round((generated - 1) / expanded, 2) if expanded > 0 else 0.0

    return {
        "status": status,
        "size": size,
        "start_board": [list(r) for r in start_board],
        "target_board": [list(r) for r in target_board],
        "config": {
            "graph_search": graph_search,
            "early_goal_test": early_goal_test,
            "max_nodes": max_nodes,
        },
        "solvability": solvability,
        "source_lines": source_lines,
        "nodes": nodes,
        "steps": steps,
        "solution_ids": solution_ids,
        "summary": {
            "total_steps": len(steps),
            "total_macros": steps[-1]["macro_index"] if steps else 0,
            "solution_length": (len(solution_ids) - 1) if solution_ids is not None else None,
            "nodes_expanded": expanded,
            "nodes_generated": generated,
            "skipped_explored": last_metrics.get("skipped_explored", 0),
            "skipped_frontier": last_metrics.get("skipped_frontier", 0),
            "max_frontier_size": last_metrics.get("max_frontier_size", 0),
            "avg_branching_factor": avg_branching,
        },
    }
