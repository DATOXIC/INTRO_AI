"""Generic uninformed-search engine (BFS / DFS / UCS) with step-by-step debug tracing.

The engine knows nothing about a specific puzzle: a *problem domain* is described by a
``Domain`` (start state, goal test, actions, transition model and JSON serialisation), so the
same pseudocode, trace format and UI work for n-Puzzle, Vacuum Robot and any future problem.
"""

from __future__ import annotations

import bisect
import heapq
from dataclasses import dataclass, field
from itertools import count
from typing import Any, Callable

Move = str
# "ucs"      : đúng mã giả trên slide (có REPLACE nút trong frontier).
# "ucs_fast" : bản tối ưu (best_cost + bỏ qua nút cũ khi pop), kết quả giống "ucs" nhưng không phải tìm trong frontier.
ALGORITHMS = ("bfs", "dfs", "ucs", "ucs_fast")
UCS_ALGORITHMS = ("ucs", "ucs_fast")

# Mỗi bước trong trace chứa danh sách frontier/explored, nên tổng kích thước tỉ lệ ~ steps × |lists|.
# Giới hạn tổng số phần tử để phản hồi JSON không phình ra hàng trăm MB (đặc biệt với DFS / Tree Search).
MAX_TRACE_ELEMENTS = 3_000_000


class Node:
    """Search tree node following the lecture slide structure."""

    def __init__(
        self,
        state: Any,
        parent: Node | None = None,
        action: Move | None = None,
        depth: int = 0,
        node_id: int = 0,
        path_cost: int = 0,
    ) -> None:
        self.state = state
        self.parent = parent
        self.action = action
        self.depth = depth
        self.node_id = node_id
        self.path_cost = path_cost  # g(n): tổng chi phí từ nút gốc tới nút này


class Problem:
    """Problem formulation bundling start state, goal condition, actions, and transition model."""

    def __init__(
        self,
        start_state: Any,
        target_state: Any | Callable[[Any], bool],
        get_moves: Callable[[Any], list[Move]],
        apply_move: Callable[[Any, Move], Any],
        step_cost: Callable[[Any, Move], int] | None = None,
    ) -> None:
        self.start_state = start_state
        self.target_state = target_state
        self.get_moves = get_moves
        self.apply_move = apply_move
        self.step_cost = step_cost or unit_cost


def unit_cost(state: Any, move: Move) -> int:
    """Chi phí mặc định: mọi hành động đều tốn 1."""
    return 1


def is_goal(puzzle: Problem, cur_state: Any) -> bool:
    """Return True if cur_state satisfies the problem's goal condition."""
    if callable(puzzle.target_state):
        return bool(puzzle.target_state(cur_state))
    return cur_state == puzzle.target_state


# ── Frontier data structures ────────────────────────────────────────────────

def Queue() -> list[Node]:
    """Create an empty FIFO queue."""
    return []


def enqueue(wait_list: list[Node], item: Node) -> None:
    """Append an item to the tail of the FIFO queue."""
    wait_list.append(item)


def is_empty(wait_list: list[Node]) -> bool:
    """Check whether a frontier (queue or stack) is empty."""
    return len(wait_list) == 0


def dequeue(wait_list: list[Node]) -> Node | None:
    """Pop and return the front item of the FIFO queue, or None if empty."""
    if is_empty(wait_list):
        return None
    first_item = wait_list[0]
    del wait_list[0]
    return first_item


def Stack() -> list[Node]:
    """Create an empty LIFO stack."""
    return []


def push(stack: list[Node], item: Node) -> None:
    """Push an item on top of the stack."""
    stack.append(item)


def pop(stack: list[Node]) -> Node | None:
    """Pop and return the top item of the stack, or None if empty."""
    if is_empty(stack):
        return None
    return stack.pop()


def child_node(puzzle: Problem, prev_node: Node, move: Move, node_id: int = 0) -> Node:
    """Generate a child Node by applying move to prev_node.state."""
    next_state = puzzle.apply_move(prev_node.state, move)
    return Node(
        state=next_state,
        parent=prev_node,
        action=move,
        depth=prev_node.depth + 1,
        node_id=node_id,
        path_cost=prev_node.path_cost + puzzle.step_cost(prev_node.state, move),
    )


def solution(goal_node: Node) -> list[Any]:
    """Trace states from root to goal_node."""
    trace: list[Any] = []
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


# ── Plain (un-instrumented) algorithms, matching the lecture pseudocode ─────

def BFS(puzzle: Problem) -> list[Any] | None:
    """Standard Graph-Search BFS matching the lecture slide pseudocode."""
    root = Node(puzzle.start_state)
    if is_goal(puzzle, root.state):
        return solution(root)

    wait_queue = Queue()
    enqueue(wait_queue, root)
    seen_states: set[Any] = set()

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


def DFS(puzzle: Problem) -> list[Any] | None:
    """Graph-Search DFS: same skeleton as BFS but the frontier is a LIFO stack."""
    root = Node(puzzle.start_state)
    if is_goal(puzzle, root.state):
        return solution(root)

    frontier = Stack()
    push(frontier, root)
    explored: set[Any] = set()

    while not is_empty(frontier):
        cur_node = pop(frontier)
        assert cur_node is not None
        explored.add(cur_node.state)

        for move in puzzle.get_moves(cur_node.state):
            child = child_node(puzzle, cur_node, move)
            in_frontier = any(queued.state == child.state for queued in frontier)
            if child.state not in explored and not in_frontier:
                if is_goal(puzzle, child.state):
                    return solution(child)
                push(frontier, child)
    return None


def UCS(puzzle: Problem) -> list[Any] | None:
    """UCS đúng mã giả trên slide: frontier ưu tiên theo path_cost; gặp đường rẻ hơn thì REPLACE."""
    arrival = count()
    root = Node(puzzle.start_state)
    frontier: list[tuple[int, int, Node]] = []
    heapq.heappush(frontier, (root.path_cost, next(arrival), root))
    explored: set[Any] = set()

    while frontier:
        cur_node = heapq.heappop(frontier)[2]
        if is_goal(puzzle, cur_node.state):
            return solution(cur_node)
        explored.add(cur_node.state)

        for move in puzzle.get_moves(cur_node.state):
            child = child_node(puzzle, cur_node, move)
            pos = next((i for i, e in enumerate(frontier) if e[2].state == child.state), -1)
            if child.state not in explored and pos == -1:
                heapq.heappush(frontier, (child.path_cost, next(arrival), child))
            elif pos != -1 and frontier[pos][2].path_cost > child.path_cost:
                frontier[pos] = (child.path_cost, next(arrival), child)  # REPLACE
                heapq.heapify(frontier)
    return None


def UCS_fast(puzzle: Problem) -> list[Any] | None:
    """UCS tối ưu: best_cost thay cho việc tìm trong frontier, nút cũ bị bỏ qua khi được pop."""
    arrival = count()
    root = Node(puzzle.start_state)
    frontier: list[tuple[int, int, Node]] = []
    heapq.heappush(frontier, (root.path_cost, next(arrival), root))
    best_cost: dict[Any, int] = {root.state: 0}
    explored: set[Any] = set()

    while frontier:
        cur_node = heapq.heappop(frontier)[2]
        if cur_node.state in explored:
            continue
        if is_goal(puzzle, cur_node.state):
            return solution(cur_node)
        explored.add(cur_node.state)

        for move in puzzle.get_moves(cur_node.state):
            child = child_node(puzzle, cur_node, move)
            if child.state in explored:
                continue
            if child.state not in best_cost or child.path_cost < best_cost[child.state]:
                best_cost[child.state] = child.path_cost
                heapq.heappush(frontier, (child.path_cost, next(arrival), child))
    return None


# ── Domain adapter used by the tracer ───────────────────────────────────────

@dataclass(frozen=True)
class Domain:
    """Everything the tracer needs to know about one concrete problem instance."""

    kind: str
    start_state: Any
    goal: Any  # a goal state, or a predicate state -> bool
    get_moves: Callable[[Any], list[Move]]
    apply_move: Callable[[Any, Move], Any]
    state_to_json: Callable[[Any], Any]
    # (state, parent_state or None, action or None) -> extra per-node fields for the UI
    node_extras: Callable[[Any, Any, Move | None], dict[str, Any]]
    solvability: dict[str, Any]
    goal_description: str
    result_fields: dict[str, Any]
    # Chi phí một hành động (mặc định 1). move_costs chỉ để giao diện hiển thị bảng giá.
    step_cost: Callable[[Any, Move], int] = unit_cost
    move_costs: dict[str, int] = field(default_factory=dict)


def get_source_lines(
    algorithm: str = "bfs",
    graph_search: bool = True,
    early_goal_test: bool = True,
) -> list[dict[str, Any]]:
    """Return structured pseudocode lines with semantic tags matching the active options."""
    if algorithm in UCS_ALGORITHMS:
        return _number_lines(_ucs_lines(algorithm))
    is_dfs = algorithm == "dfs"
    name = "DFS" if is_dfs else "BFS"
    make_frontier = "Stack(); push(frontier, root)" if is_dfs else "Queue(); enqueue(frontier, root)"
    take = "pop(frontier)" if is_dfs else "dequeue(frontier)"
    put = "push(frontier, child)" if is_dfs else "enqueue(frontier, child)"

    lines: list[tuple[str, str]] = [
        ("def", f"def {name}(problem):"),
        ("init_root", "    root = Node(problem.start_state)"),
    ]
    if early_goal_test:
        lines.append(("check_root_goal", "    if is_goal(root): return solution(root)"))
    lines.append(("init_queue", f"    frontier = {make_frontier}"))
    if graph_search:
        lines.append(("init_explored", "    explored = set()"))
    lines.append(("while_loop", "    while not is_empty(frontier):"))
    lines.append(("dequeue", f"        cur_node = {take}"))
    if not early_goal_test:
        lines.append(("check_late_goal", "        if is_goal(cur_node): return solution(cur_node)"))
    if graph_search:
        lines.append(("add_explored", "        explored.add(cur_node.state)"))
    lines.append(("for_move", "        for move in actions(cur_node):"))
    lines.append(("make_child", "            child = child_node(cur_node, move)"))
    if graph_search:
        lines.append(("check_duplicate", "            if child not in explored and child not in frontier:"))
        indent = "                "
    else:
        indent = "            "
    if early_goal_test:
        lines.append(("check_early_goal", f"{indent}if is_goal(child): return solution(child)"))
    lines.append(("enqueue_child", f"{indent}{put}"))
    lines.append(("return_none", "    return None"))

    return _number_lines(lines)


def _number_lines(lines: list[tuple[str, str]]) -> list[dict[str, Any]]:
    """Halve the indentation (pseudocode reads better with 2-space levels) and number the lines."""

    def compact(code: str) -> str:
        body = code.lstrip(" ")
        return " " * ((len(code) - len(body)) // 2) + body

    return [
        {"line": idx + 1, "tag": tag, "code": compact(code)}
        for idx, (tag, code) in enumerate(lines)
    ]


def _ucs_lines(algorithm: str) -> list[tuple[str, str]]:
    """Pseudocode of UCS (slide version, with REPLACE) and of the optimised UCS (best_cost)."""
    if algorithm == "ucs":
        return [
            ("def", "def UCS(problem):"),
            ("init_root", "    root = Node(problem.start_state, path_cost=0)"),
            ("init_queue", "    frontier = PriorityQueue(); enqueue(frontier, root)"),
            ("init_explored", "    explored = set()"),
            ("while_loop", "    while not is_empty(frontier):"),
            ("dequeue", "        cur_node = dequeue(frontier)   # g nhỏ nhất"),
            ("check_late_goal", "        if is_goal(cur_node): return solution(cur_node)"),
            ("add_explored", "        explored.add(cur_node.state)"),
            ("for_move", "        for move in actions(cur_node):"),
            ("make_child", "            child = child_node(cur_node, move)"),
            ("check_duplicate", "            if child not in explored and child not in frontier:"),
            ("enqueue_child", "                enqueue(frontier, child)"),
            ("check_better", "            elif child in frontier with higher path_cost:"),
            ("replace_child", "                replace(frontier, child)"),
            ("return_none", "    return None"),
        ]
    return [
        ("def", "def UCS_nhanh(problem):"),
        ("init_root", "    root = Node(problem.start_state, path_cost=0)"),
        ("init_queue", "    frontier = PriorityQueue(); enqueue(frontier, root)"),
        ("init_best", "    best_cost = {root.state: 0}"),
        ("init_explored", "    explored = set()"),
        ("while_loop", "    while not is_empty(frontier):"),
        ("dequeue", "        cur_node = dequeue(frontier)   # g nhỏ nhất"),
        ("check_stale", "        if cur_node.state in explored: continue"),
        ("check_late_goal", "        if is_goal(cur_node): return solution(cur_node)"),
        ("add_explored", "        explored.add(cur_node.state)"),
        ("for_move", "        for move in actions(cur_node):"),
        ("make_child", "            child = child_node(cur_node, move)"),
        ("check_explored_child", "            if child.state in explored: continue"),
        ("check_best", "            if child.state not in best_cost or child.path_cost < best_cost[child.state]:"),
        ("update_best", "                best_cost[child.state] = child.path_cost"),
        ("enqueue_child", "                enqueue(frontier, child)"),
        ("return_none", "    return None"),
    ]


def _vocabulary(algorithm: str) -> dict[str, str]:
    """Wording that differs between a FIFO queue (BFS) and a LIFO stack (DFS)."""
    if algorithm == "dfs":
        return {
            "container": "ngăn xếp",
            "out_where": "ĐỈNH ngăn xếp",
            "in_verb": "Push",
            "in_where": "lên ĐỈNH ngăn xếp",
        }
    if algorithm in UCS_ALGORITHMS:
        return {
            "container": "hàng đợi ưu tiên",
            "out_where": "ĐẦU hàng đợi ưu tiên (g nhỏ nhất)",
            "in_verb": "Thêm",
            "in_where": "vào hàng đợi ưu tiên (đúng vị trí theo g)",
        }
    return {
        "container": "hàng đợi",
        "out_where": "ĐẦU hàng đợi",
        "in_verb": "Thêm",
        "in_where": "vào CUỐI hàng đợi",
    }


class _Recorder:
    """Ghi lại từng nút và từng bước của một lần chạy (dùng chung cho BFS/DFS và UCS)."""

    def __init__(
        self,
        domain: Domain,
        tag_to_line: dict[str, int],
        frontier_ids: Callable[[], list[int]],
    ) -> None:
        self.domain = domain
        self.tag_to_line = tag_to_line
        self.frontier_ids = frontier_ids
        self.nodes: list[dict[str, Any]] = []
        self.steps: list[dict[str, Any]] = []
        self.explored_order: list[int] = []
        self.macro_counter = 0
        self.budget_used = 0
        self.metrics: dict[str, int] = {
            "expanded": 0,
            "generated": 0,
            "skipped_explored": 0,
            "skipped_frontier": 0,
            "skipped_stale": 0,
            "replaced": 0,
            "max_frontier_size": 0,
            "current_depth": 0,
        }

    def register_node(
        self,
        node: Node,
        parent_state: Any,
        created_step: int,
        *,
        is_duplicate: bool = False,
        duplicate_of: int | None = None,
        duplicate_reason: str | None = None,
    ) -> dict[str, Any]:
        domain = self.domain
        parent_cost = node.parent.path_cost if node.parent is not None else 0
        rec = {
            "id": node.node_id,
            "state": domain.state_to_json(node.state),
            "parent_id": node.parent.node_id if node.parent is not None else None,
            "action": node.action,
            "depth": node.depth,
            "path_cost": node.path_cost,
            "step_cost": node.path_cost - parent_cost,
            "actions": list(domain.get_moves(node.state)),
            **domain.node_extras(node.state, parent_state, node.action),
            "is_duplicate": is_duplicate,
            "duplicate_of": duplicate_of,
            "duplicate_reason": duplicate_reason,
            "created_step": created_step,
            # Bước mà số phận của nút được quyết định (bị cắt hoặc được đưa vào frontier). Giao diện
            # dùng mốc này để không "tiết lộ trước" việc nút con bị trùng khi mới vừa sinh ra.
            "resolved_step": None,
            "expanded_step": None,
            # UCS: nút này thay (replaces) hoặc bị thay (superseded_by) một nút khác cùng trạng thái.
            "replaces": None,
            "superseded_by": None,
            "superseded_step": None,
            # UCS tối ưu: nút cũ bị bỏ qua khi pop.
            "discarded_step": None,
        }
        self.nodes.append(rec)
        return rec

    def record_step(
        self,
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
        if is_macro:
            self.macro_counter += 1
        step_idx = len(self.steps)
        frontier_ids = self.frontier_ids()
        self.metrics["max_frontier_size"] = max(self.metrics["max_frontier_size"], len(frontier_ids))
        self.budget_used += len(frontier_ids) + len(self.explored_order) + 1
        self.steps.append(
            {
                "index": step_idx,
                "macro_index": self.macro_counter,
                "is_macro": is_macro,
                "event_type": event_type,
                "code_tag": code_tag,
                "line": self.tag_to_line.get(code_tag, 1),
                "cur_id": cur_id,
                "candidate_id": candidate_id,
                "collision_id": collision_id,
                "frontier_ids": frontier_ids,
                "explored_ids": list(self.explored_order),
                "solution_ids": solution_ids,
                "vars": local_vars or {},
                "message": message,
                "metrics": {
                    **self.metrics,
                    "frontier_size": len(frontier_ids),
                    "explored_size": len(self.explored_order),
                },
            }
        )
        return step_idx


def search_trace(
    domain: Domain,
    *,
    algorithm: str = "bfs",
    graph_search: bool = True,
    early_goal_test: bool = True,
    max_nodes: int = 300,
) -> dict[str, Any]:
    """Run an instrumented BFS/DFS on ``domain`` and return a complete line-by-line debug trace.

    Every executed pseudocode line becomes one step, so the UI can animate exactly what the
    code does: create root, pop, mark explored, generate child, check duplicate / goal, push.

    Args:
        domain: Problem adapter (start state, actions, goal, serialisation).
        algorithm: ``"bfs"`` (FIFO), ``"dfs"`` (LIFO) or ``"ucs"`` / ``"ucs_fast"`` (priority queue).
        graph_search: If True, prune duplicates in explored and frontier; if False, run Tree Search.
        early_goal_test: If True, check goal on child generation; if False, check on pop.
        max_nodes: Maximum number of expanded nodes before stopping safely.

    Returns:
        Dictionary with nodes, steps, source lines, solvability and summary.
    """
    if algorithm not in ALGORITHMS:
        raise ValueError(f"Thuật toán phải thuộc {ALGORITHMS}, nhận được: {algorithm!r}")
    if not (1 <= max_nodes <= 3000):
        raise ValueError("max_nodes phải nằm trong khoảng [1, 3000].")
    if algorithm in UCS_ALGORITHMS:
        # UCS luôn là Graph Search và kiểm tra đích khi pop (đúng slide), bất kể hai tùy chọn kia.
        return _search_trace_ucs(domain, fast=algorithm == "ucs_fast", max_nodes=max_nodes)

    is_dfs = algorithm == "dfs"
    words = _vocabulary(algorithm)
    puzzle = Problem(domain.start_state, domain.goal, domain.get_moves, domain.apply_move, domain.step_cost)
    source_lines = get_source_lines(algorithm, graph_search, early_goal_test)
    tag_to_line = {item["tag"]: item["line"] for item in source_lines}

    next_id = 0
    frontier: list[Node] = Stack() if is_dfs else Queue()
    rec = _Recorder(domain, tag_to_line, lambda: [n.node_id for n in frontier])
    nodes, steps, metrics = rec.nodes, rec.steps, rec.metrics
    explored_order = rec.explored_order
    register_node, record_step = rec.register_node, rec.record_step
    explored_map: dict[Any, int] = {}
    frontier_map: dict[Any, int] = {}

    def take_frontier() -> Node | None:
        return pop(frontier) if is_dfs else dequeue(frontier)

    def put_frontier(node: Node) -> None:
        if is_dfs:
            push(frontier, node)
        else:
            enqueue(frontier, node)

    def finish(status: str, solution_ids: list[int] | None) -> dict[str, Any]:
        return _build_result(
            domain=domain,
            algorithm=algorithm,
            status=status,
            graph_search=graph_search,
            early_goal_test=early_goal_test,
            max_nodes=max_nodes,
            source_lines=source_lines,
            nodes=nodes,
            steps=steps,
            solution_ids=solution_ids,
        )

    # ── Dòng: root = Node(problem.start_state) ──
    root = Node(puzzle.start_state, parent=None, action=None, depth=0, node_id=next_id)
    next_id += 1
    metrics["generated"] += 1
    register_node(root, parent_state=None, created_step=0)
    record_step(
        event_type="init_root",
        code_tag="init_root",
        message="Tạo nút gốc #0 từ trạng thái xuất phát.",
        is_macro=True,
        cur_id=root.node_id,
        local_vars={"root": "#0", "depth": 0},
    )

    # ── Dòng: if is_goal(root): return solution(root) ──
    if early_goal_test and is_goal(puzzle, root.state):
        sol_ids = solution_node_ids(root)
        record_step(
            event_type="goal_init",
            code_tag="check_root_goal",
            message="Nút gốc #0 đã là ĐÍCH (0 bước)!",
            is_macro=True,
            cur_id=root.node_id,
            solution_ids=sol_ids,
            local_vars={"root": "#0", "is_goal": True},
        )
        return finish("solved", sol_ids)

    if early_goal_test:
        record_step(
            event_type="check_root",
            code_tag="check_root_goal",
            message="Gốc chưa phải đích → tiếp tục.",
            is_macro=False,
            cur_id=root.node_id,
            local_vars={"root": "#0", "is_goal": False},
        )

    # ── Dòng: frontier = Queue()/Stack(); enqueue/push(frontier, root) ──
    put_frontier(root)
    frontier_map[root.state] = root.node_id
    init_step = record_step(
        event_type="init",
        code_tag="init_queue",
        message=f"Tạo {words['container']} frontier và đưa nút gốc #0 vào.",
        is_macro=True,
        cur_id=root.node_id,
        candidate_id=root.node_id,
        local_vars={"root": "#0", "frontier_len": 1},
    )
    nodes[root.node_id]["resolved_step"] = init_step

    # ── Dòng: explored = set() ──
    if graph_search:
        record_step(
            event_type="init_explored",
            code_tag="init_explored",
            message="Tạo tập explored rỗng.",
            is_macro=False,
            cur_id=None,
            local_vars={"frontier_len": 1, "explored_len": 0},
        )

    final_status = "failure"
    final_solution_ids: list[int] | None = None

    while not is_empty(frontier):
        if metrics["expanded"] >= max_nodes or rec.budget_used > MAX_TRACE_ELEMENTS:
            final_status = "limit_reached"
            reason = (
                f"Chạm giới hạn an toàn {max_nodes} nút mở rộng → dừng tìm kiếm."
                if metrics["expanded"] >= max_nodes
                else "Dữ liệu từng bước đã quá lớn để hiển thị → dừng tìm kiếm."
            )
            record_step(
                event_type="limit_reached",
                code_tag="while_loop",
                message=reason,
                is_macro=True,
                cur_id=None,
                local_vars={"max_nodes": max_nodes, "frontier_len": len(frontier)},
            )
            break

        # ── Dòng: cur_node = dequeue(frontier) / pop(frontier) ──
        cur_node = take_frontier()
        assert cur_node is not None
        if frontier_map.get(cur_node.state) == cur_node.node_id:
            del frontier_map[cur_node.state]

        metrics["expanded"] += 1
        metrics["current_depth"] = cur_node.depth
        dequeue_step = record_step(
            event_type="dequeue",
            code_tag="dequeue",
            message=f"Pop nút #{cur_node.node_id} (tầng {cur_node.depth}) khỏi {words['out_where']} → thành cur_node.",
            is_macro=True,
            cur_id=cur_node.node_id,
            local_vars={
                "cur_node": f"#{cur_node.node_id}",
                "depth": cur_node.depth,
                "frontier_len": len(frontier),
            },
        )
        nodes[cur_node.node_id]["expanded_step"] = dequeue_step

        # ── Dòng: if is_goal(cur_node): return solution(cur_node)   (Late Goal) ──
        if not early_goal_test and is_goal(puzzle, cur_node.state):
            final_status = "solved"
            final_solution_ids = solution_node_ids(cur_node)
            record_step(
                event_type="goal_late",
                code_tag="check_late_goal",
                message=f"#{cur_node.node_id} là ĐÍCH! Lời giải {len(final_solution_ids) - 1} bước.",
                is_macro=True,
                cur_id=cur_node.node_id,
                solution_ids=final_solution_ids,
                local_vars={"cur_node": f"#{cur_node.node_id}", "is_goal": True},
            )
            break

        if not early_goal_test:
            record_step(
                event_type="check_late",
                code_tag="check_late_goal",
                message=f"#{cur_node.node_id} chưa phải đích → tiếp tục.",
                is_macro=False,
                cur_id=cur_node.node_id,
                local_vars={"cur_node": f"#{cur_node.node_id}", "is_goal": False},
            )

        # ── Dòng: explored.add(cur_node.state) ──
        if graph_search:
            if cur_node.state not in explored_map:
                explored_map[cur_node.state] = cur_node.node_id
                explored_order.append(cur_node.node_id)
            record_step(
                event_type="explore",
                code_tag="add_explored",
                message=f"Ghi #{cur_node.node_id} vào explored (tổng {len(explored_order)}).",
                is_macro=False,
                cur_id=cur_node.node_id,
                local_vars={"cur_node": f"#{cur_node.node_id}", "explored_len": len(explored_order)},
            )

        # ── Dòng: for move in actions(cur_node) ──
        moves = puzzle.get_moves(cur_node.state)
        for move_idx, move in enumerate(moves, start=1):
            cand_id = next_id
            next_id += 1
            cand = child_node(puzzle, cur_node, move, node_id=cand_id)
            metrics["generated"] += 1

            in_explored = graph_search and (cand.state in explored_map)
            in_frontier = graph_search and (not in_explored) and (cand.state in frontier_map)
            collision_id: int | None = None
            if in_explored:
                collision_id = explored_map[cand.state]
            elif in_frontier:
                collision_id = frontier_map[cand.state]

            register_node(
                cand,
                parent_state=cur_node.state,
                created_step=len(steps),
                is_duplicate=collision_id is not None,
                duplicate_of=collision_id,
                duplicate_reason="explored" if in_explored else ("frontier" if in_frontier else None),
            )

            # ── Dòng: child = child_node(cur_node, move) ──
            record_step(
                event_type="gen_child",
                code_tag="make_child",
                message=f"Thử nước '{move}' ({move_idx}/{len(moves)}) → sinh nút con #{cand_id} (tầng {cand.depth}).",
                is_macro=False,
                cur_id=cur_node.node_id,
                candidate_id=cand_id,
                local_vars={
                    "cur_node": f"#{cur_node.node_id}",
                    "move": move,
                    "child": f"#{cand_id}",
                    "lượt": f"{move_idx}/{len(moves)}",
                },
            )

            # ── Dòng: if child not in explored and child not in frontier ──
            if in_explored or in_frontier:
                where = "explored" if in_explored else "frontier"
                metrics["skipped_explored" if in_explored else "skipped_frontier"] += 1
                skip_step = record_step(
                    event_type="skip_explored" if in_explored else "skip_frontier",
                    code_tag="check_duplicate",
                    message=(
                        f"#{cand_id} trùng #{collision_id} "
                        f"{'đã có trong explored' if in_explored else 'đang chờ trong frontier'} → bỏ qua."
                    ),
                    is_macro=False,
                    cur_id=cur_node.node_id,
                    candidate_id=cand_id,
                    collision_id=collision_id,
                    local_vars={
                        "child": f"#{cand_id}",
                        "in_explored": in_explored,
                        "in_frontier": in_frontier,
                        "collision": f"#{collision_id} ({where})",
                    },
                )
                nodes[cand_id]["resolved_step"] = skip_step
                continue

            if graph_search:
                record_step(
                    event_type="check_pass",
                    code_tag="check_duplicate",
                    message=f"#{cand_id} chưa có trong explored và frontier → là trạng thái mới.",
                    is_macro=False,
                    cur_id=cur_node.node_id,
                    candidate_id=cand_id,
                    local_vars={"child": f"#{cand_id}", "in_explored": False, "in_frontier": False},
                )

            # ── Dòng: if is_goal(child): return solution(child)   (Early Goal) ──
            if early_goal_test:
                if is_goal(puzzle, cand.state):
                    final_status = "solved"
                    final_solution_ids = solution_node_ids(cand)
                    goal_step = record_step(
                        event_type="goal_early",
                        code_tag="check_early_goal",
                        message=f"#{cand_id} là ĐÍCH! Lời giải {len(final_solution_ids) - 1} bước.",
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
                    nodes[cand_id]["resolved_step"] = goal_step
                    break
                record_step(
                    event_type="check_goal",
                    code_tag="check_early_goal",
                    message=f"#{cand_id} chưa phải đích.",
                    is_macro=False,
                    cur_id=cur_node.node_id,
                    candidate_id=cand_id,
                    local_vars={"child": f"#{cand_id}", "is_goal": False},
                )

            # ── Dòng: enqueue(frontier, child) / push(frontier, child) ──
            put_frontier(cand)
            if cand.state not in frontier_map:
                frontier_map[cand.state] = cand.node_id
            enqueue_step = record_step(
                event_type="enqueue",
                code_tag="enqueue_child",
                message=f"{words['in_verb']} #{cand_id} {words['in_where']}.",
                is_macro=False,
                cur_id=cur_node.node_id,
                candidate_id=cand_id,
                local_vars={
                    "cur_node": f"#{cur_node.node_id}",
                    "move": move,
                    "child": f"#{cand_id}",
                    "frontier_len": len(frontier),
                },
            )
            nodes[cand_id]["resolved_step"] = enqueue_step

        if final_status == "solved":
            break

    if final_status == "failure":
        record_step(
            event_type="failure",
            code_tag="return_none",
            message=f"Frontier rỗng mà chưa thấy đích → không có lời giải.",
            is_macro=True,
            cur_id=None,
            local_vars={"frontier_len": 0, "explored_len": len(explored_order)},
        )

    return finish(final_status, final_solution_ids)


def _search_trace_ucs(domain: Domain, *, fast: bool, max_nodes: int) -> dict[str, Any]:
    """Instrumented UCS. ``fast=False`` follows the lecture slide (REPLACE in frontier);
    ``fast=True`` is the optimised variant (best_cost + stale nodes skipped on pop)."""
    algorithm = "ucs_fast" if fast else "ucs"
    puzzle = Problem(domain.start_state, domain.goal, domain.get_moves, domain.apply_move, domain.step_cost)
    source_lines = get_source_lines(algorithm, True, False)
    tag_to_line = {item["tag"]: item["line"] for item in source_lines}

    # frontier luôn được sắp theo (path_cost, thứ tự vào): phần tử đầu là nút sẽ được pop.
    frontier: list[tuple[int, int, Node]] = []
    arrival = count()
    rec = _Recorder(domain, tag_to_line, lambda: [entry[2].node_id for entry in frontier])
    nodes, steps, metrics = rec.nodes, rec.steps, rec.metrics
    register_node, record_step = rec.register_node, rec.record_step
    explored_map: dict[Any, int] = {}
    in_frontier: dict[Any, tuple[int, int, Node]] = {}  # bản slide: trạng thái -> nút duy nhất trong frontier
    best_cost: dict[Any, int] = {}  # bản tối ưu: g nhỏ nhất đã thấy của mỗi trạng thái
    best_node: dict[Any, int] = {}
    next_id = 0

    def put(node: Node) -> tuple[int, int, Node]:
        entry = (node.path_cost, next(arrival), node)
        bisect.insort(frontier, entry)
        return entry

    def finish(status: str, solution_ids: list[int] | None) -> dict[str, Any]:
        return _build_result(
            domain=domain,
            algorithm=algorithm,
            status=status,
            graph_search=True,
            early_goal_test=False,
            max_nodes=max_nodes,
            source_lines=source_lines,
            nodes=nodes,
            steps=steps,
            solution_ids=solution_ids,
        )

    # ── root = Node(problem.start_state, path_cost=0) ──
    root = Node(puzzle.start_state, node_id=next_id)
    next_id += 1
    metrics["generated"] += 1
    register_node(root, None, 0)
    record_step(
        event_type="init_root",
        code_tag="init_root",
        message="Tạo nút gốc #0 với chi phí g = 0.",
        is_macro=True,
        cur_id=0,
        local_vars={"root": "#0", "g": 0},
    )

    # ── frontier = PriorityQueue(); enqueue(frontier, root) ──
    entry = put(root)
    if not fast:
        in_frontier[root.state] = entry
    init_step = record_step(
        event_type="init",
        code_tag="init_queue",
        message="Tạo hàng đợi ưu tiên frontier (xếp theo g) và đưa nút gốc #0 vào.",
        is_macro=True,
        cur_id=0,
        candidate_id=0,
        local_vars={"root": "#0", "frontier_len": 1},
    )
    nodes[0]["resolved_step"] = init_step

    # ── best_cost = {root.state: 0}   (chỉ bản tối ưu) ──
    if fast:
        best_cost[root.state] = 0
        best_node[root.state] = 0
        record_step(
            event_type="init_best",
            code_tag="init_best",
            message="Tạo best_cost: ghi nhớ g nhỏ nhất đã tìm thấy cho mỗi trạng thái (mới có gốc: g = 0).",
            is_macro=False,
            cur_id=None,
            local_vars={"best_cost": 1},
        )

    # ── explored = set() ──
    record_step(
        event_type="init_explored",
        code_tag="init_explored",
        message="Tạo tập explored rỗng.",
        is_macro=False,
        cur_id=None,
        local_vars={"frontier_len": 1, "explored_len": 0},
    )

    final_status = "failure"
    final_solution_ids: list[int] | None = None

    while frontier:
        if metrics["expanded"] >= max_nodes or rec.budget_used > MAX_TRACE_ELEMENTS:
            final_status = "limit_reached"
            reason = (
                f"Chạm giới hạn an toàn {max_nodes} nút mở rộng → dừng tìm kiếm."
                if metrics["expanded"] >= max_nodes
                else "Dữ liệu từng bước đã quá lớn để hiển thị → dừng tìm kiếm."
            )
            record_step(
                event_type="limit_reached",
                code_tag="while_loop",
                message=reason,
                is_macro=True,
                cur_id=None,
                local_vars={"max_nodes": max_nodes, "frontier_len": len(frontier)},
            )
            break

        # ── cur_node = dequeue(frontier)   (g nhỏ nhất) ──
        cur = frontier.pop(0)[2]
        if not fast:
            in_frontier.pop(cur.state, None)
            metrics["expanded"] += 1
            metrics["current_depth"] = cur.depth
        dequeue_step = record_step(
            event_type="dequeue",
            code_tag="dequeue",
            message=f"Pop nút #{cur.node_id} (g = {cur.path_cost}) — nút có g nhỏ nhất trong frontier → thành cur_node.",
            is_macro=True,
            cur_id=cur.node_id,
            local_vars={"cur_node": f"#{cur.node_id}", "g": cur.path_cost, "frontier_len": len(frontier)},
        )

        # ── if cur_node.state in explored: continue   (chỉ bản tối ưu) ──
        if fast:
            if cur.state in explored_map:
                metrics["skipped_stale"] += 1
                stale_step = record_step(
                    event_type="skip_stale",
                    code_tag="check_stale",
                    message=(
                        f"#{cur.node_id} là nút CŨ: trạng thái này đã được mở rộng với đường rẻ hơn "
                        f"(#{explored_map[cur.state]}) → bỏ qua (continue)."
                    ),
                    is_macro=True,
                    cur_id=cur.node_id,
                    collision_id=explored_map[cur.state],
                    local_vars={"cur_node": f"#{cur.node_id}", "g": cur.path_cost, "in_explored": True},
                )
                nodes[cur.node_id]["discarded_step"] = stale_step
                continue
            metrics["expanded"] += 1
            metrics["current_depth"] = cur.depth
            record_step(
                event_type="check_stale",
                code_tag="check_stale",
                message=f"#{cur.node_id} chưa nằm trong explored → không phải nút cũ, tiếp tục mở rộng.",
                is_macro=False,
                cur_id=cur.node_id,
                local_vars={"cur_node": f"#{cur.node_id}", "in_explored": False},
            )
        nodes[cur.node_id]["expanded_step"] = dequeue_step

        # ── if is_goal(cur_node): return solution(cur_node) ──
        if is_goal(puzzle, cur.state):
            final_status = "solved"
            final_solution_ids = solution_node_ids(cur)
            record_step(
                event_type="goal_late",
                code_tag="check_late_goal",
                message=(
                    f"#{cur.node_id} là ĐÍCH! Lời giải {len(final_solution_ids) - 1} bước, "
                    f"chi phí g = {cur.path_cost} (rẻ nhất)."
                ),
                is_macro=True,
                cur_id=cur.node_id,
                solution_ids=final_solution_ids,
                local_vars={"cur_node": f"#{cur.node_id}", "g": cur.path_cost, "is_goal": True},
            )
            break
        record_step(
            event_type="check_late",
            code_tag="check_late_goal",
            message=f"#{cur.node_id} chưa phải đích → tiếp tục.",
            is_macro=False,
            cur_id=cur.node_id,
            local_vars={"cur_node": f"#{cur.node_id}", "g": cur.path_cost, "is_goal": False},
        )

        # ── explored.add(cur_node.state) ──
        explored_map[cur.state] = cur.node_id
        rec.explored_order.append(cur.node_id)
        record_step(
            event_type="explore",
            code_tag="add_explored",
            message=f"Ghi #{cur.node_id} vào explored (tổng {len(rec.explored_order)}).",
            is_macro=False,
            cur_id=cur.node_id,
            local_vars={"cur_node": f"#{cur.node_id}", "explored_len": len(rec.explored_order)},
        )

        # ── for move in actions(cur_node) ──
        moves = puzzle.get_moves(cur.state)
        for move_idx, move in enumerate(moves, start=1):
            cand_id = next_id
            next_id += 1
            cand = child_node(puzzle, cur, move, node_id=cand_id)
            metrics["generated"] += 1
            step_cost = cand.path_cost - cur.path_cost
            in_explored = cand.state in explored_map
            old_entry = None if (fast or in_explored) else in_frontier.get(cand.state)
            register_node(
                cand,
                parent_state=cur.state,
                created_step=len(steps),
                is_duplicate=in_explored,
                duplicate_of=explored_map[cand.state] if in_explored else None,
                duplicate_reason="explored" if in_explored else None,
            )

            # ── child = child_node(cur_node, move) ──
            record_step(
                event_type="gen_child",
                code_tag="make_child",
                message=(
                    f"Thử nước '{move}' ({move_idx}/{len(moves)}, tốn {step_cost}) → sinh nút con #{cand_id} "
                    f"với g = {cur.path_cost} + {step_cost} = {cand.path_cost}."
                ),
                is_macro=False,
                cur_id=cur.node_id,
                candidate_id=cand_id,
                local_vars={
                    "cur_node": f"#{cur.node_id}",
                    "move": move,
                    "child": f"#{cand_id}",
                    "g(child)": f"{cur.path_cost}+{step_cost}={cand.path_cost}",
                },
            )

            if in_explored:
                metrics["skipped_explored"] += 1
                skip_step = record_step(
                    event_type="skip_explored",
                    code_tag="check_explored_child" if fast else "check_duplicate",
                    message=f"#{cand_id} trùng #{explored_map[cand.state]} đã có trong explored → bỏ qua.",
                    is_macro=False,
                    cur_id=cur.node_id,
                    candidate_id=cand_id,
                    collision_id=explored_map[cand.state],
                    local_vars={"child": f"#{cand_id}", "in_explored": True},
                )
                nodes[cand_id]["resolved_step"] = skip_step
                continue

            if fast:
                # ── if child.state in explored: continue   (không) ──
                record_step(
                    event_type="check_pass",
                    code_tag="check_explored_child",
                    message=f"#{cand_id} chưa có trong explored.",
                    is_macro=False,
                    cur_id=cur.node_id,
                    candidate_id=cand_id,
                    local_vars={"child": f"#{cand_id}", "in_explored": False},
                )
                prev = best_cost.get(cand.state)
                if prev is not None and cand.path_cost >= prev:
                    holder = best_node[cand.state]
                    nodes[cand_id]["is_duplicate"] = True
                    nodes[cand_id]["duplicate_of"] = holder
                    nodes[cand_id]["duplicate_reason"] = "frontier"
                    metrics["skipped_frontier"] += 1
                    worse_step = record_step(
                        event_type="not_better",
                        code_tag="check_best",
                        message=(
                            f"g = {cand.path_cost} không thấp hơn best_cost = {prev} "
                            f"(đã có #{holder}) → bỏ qua nút con."
                        ),
                        is_macro=False,
                        cur_id=cur.node_id,
                        candidate_id=cand_id,
                        collision_id=holder,
                        local_vars={"child": f"#{cand_id}", "g(child)": cand.path_cost, "best_cost": prev},
                    )
                    nodes[cand_id]["resolved_step"] = worse_step
                    continue
                record_step(
                    event_type="better",
                    code_tag="check_best",
                    message=(
                        "Trạng thái này chưa có trong best_cost → là đường đầu tiên tới nó."
                        if prev is None
                        else f"g = {cand.path_cost} < best_cost = {prev} → tìm được đường RẺ HƠN."
                    ),
                    is_macro=False,
                    cur_id=cur.node_id,
                    candidate_id=cand_id,
                    collision_id=best_node.get(cand.state),
                    local_vars={
                        "child": f"#{cand_id}",
                        "g(child)": cand.path_cost,
                        "best_cost": "chưa có" if prev is None else prev,
                    },
                )
                best_cost[cand.state] = cand.path_cost
                record_step(
                    event_type="update_best",
                    code_tag="update_best",
                    message=f"Ghi best_cost[trạng thái của #{cand_id}] = {cand.path_cost}.",
                    is_macro=False,
                    cur_id=cur.node_id,
                    candidate_id=cand_id,
                    local_vars={"child": f"#{cand_id}", "best_cost": cand.path_cost},
                )
                old_id = best_node.get(cand.state)
                best_node[cand.state] = cand_id
                put(cand)
                note = f" Nút #{old_id} trở thành nút CŨ (sẽ bị bỏ qua khi pop)." if old_id is not None else ""
                enqueue_step = record_step(
                    event_type="enqueue",
                    code_tag="enqueue_child",
                    message=f"Thêm #{cand_id} vào frontier đúng vị trí theo g = {cand.path_cost}.{note}",
                    is_macro=False,
                    cur_id=cur.node_id,
                    candidate_id=cand_id,
                    collision_id=old_id,
                    local_vars={"child": f"#{cand_id}", "g(child)": cand.path_cost, "frontier_len": len(frontier)},
                )
                nodes[cand_id]["resolved_step"] = enqueue_step
                if old_id is not None:
                    metrics["replaced"] += 1
                    nodes[old_id]["superseded_by"] = cand_id
                    nodes[old_id]["superseded_step"] = enqueue_step
                    nodes[cand_id]["replaces"] = old_id
                continue

            # ── Bản slide: if child not in explored and child not in frontier ──
            if old_entry is None:
                record_step(
                    event_type="check_pass",
                    code_tag="check_duplicate",
                    message=f"#{cand_id} chưa có trong explored và frontier → là trạng thái mới.",
                    is_macro=False,
                    cur_id=cur.node_id,
                    candidate_id=cand_id,
                    local_vars={"child": f"#{cand_id}", "in_explored": False, "in_frontier": False},
                )
                in_frontier[cand.state] = put(cand)
                enqueue_step = record_step(
                    event_type="enqueue",
                    code_tag="enqueue_child",
                    message=f"Thêm #{cand_id} vào frontier đúng vị trí theo g = {cand.path_cost}.",
                    is_macro=False,
                    cur_id=cur.node_id,
                    candidate_id=cand_id,
                    local_vars={"child": f"#{cand_id}", "g(child)": cand.path_cost, "frontier_len": len(frontier)},
                )
                nodes[cand_id]["resolved_step"] = enqueue_step
                continue

            old = old_entry[2]
            record_step(
                event_type="dup_frontier",
                code_tag="check_duplicate",
                message=(
                    f"#{cand_id} cùng trạng thái với #{old.node_id} đang chờ trong frontier (g = {old.path_cost}) "
                    "→ không vào nhánh if, xét tiếp nhánh elif: đường nào rẻ hơn?"
                ),
                is_macro=False,
                cur_id=cur.node_id,
                candidate_id=cand_id,
                collision_id=old.node_id,
                local_vars={"child": f"#{cand_id}", "in_frontier": True, "collision": f"#{old.node_id}"},
            )
            if cand.path_cost >= old.path_cost:
                nodes[cand_id]["is_duplicate"] = True
                nodes[cand_id]["duplicate_of"] = old.node_id
                nodes[cand_id]["duplicate_reason"] = "frontier"
                metrics["skipped_frontier"] += 1
                worse_step = record_step(
                    event_type="not_better",
                    code_tag="check_better",
                    message=(
                        f"g mới = {cand.path_cost} không thấp hơn g cũ = {old.path_cost} "
                        "→ giữ nút cũ, bỏ qua nút con."
                    ),
                    is_macro=False,
                    cur_id=cur.node_id,
                    candidate_id=cand_id,
                    collision_id=old.node_id,
                    local_vars={"g(child)": cand.path_cost, "g(cũ)": old.path_cost},
                )
                nodes[cand_id]["resolved_step"] = worse_step
                continue

            record_step(
                event_type="better",
                code_tag="check_better",
                message=f"g mới = {cand.path_cost} < g cũ = {old.path_cost} → tìm được đường RẺ HƠN, cần thay nút cũ.",
                is_macro=False,
                cur_id=cur.node_id,
                candidate_id=cand_id,
                collision_id=old.node_id,
                local_vars={"g(child)": cand.path_cost, "g(cũ)": old.path_cost},
            )
            frontier.remove(old_entry)
            in_frontier[cand.state] = put(cand)
            metrics["replaced"] += 1
            replace_step = record_step(
                event_type="replace",
                code_tag="replace_child",
                message=f"Thay #{old.node_id} (g = {old.path_cost}) bằng #{cand_id} (g = {cand.path_cost}) trong frontier.",
                is_macro=False,
                cur_id=cur.node_id,
                candidate_id=cand_id,
                collision_id=old.node_id,
                local_vars={"child": f"#{cand_id}", "g(child)": cand.path_cost, "frontier_len": len(frontier)},
            )
            nodes[old.node_id]["superseded_by"] = cand_id
            nodes[old.node_id]["superseded_step"] = replace_step
            nodes[cand_id]["replaces"] = old.node_id
            nodes[cand_id]["resolved_step"] = replace_step

        if final_status == "solved":
            break

    if final_status == "failure":
        record_step(
            event_type="failure",
            code_tag="return_none",
            message="Frontier rỗng mà chưa thấy đích → không có lời giải.",
            is_macro=True,
            cur_id=None,
            local_vars={"frontier_len": 0, "explored_len": len(rec.explored_order)},
        )

    return finish(final_status, final_solution_ids)


def _build_result(
    *,
    domain: Domain,
    algorithm: str,
    status: str,
    graph_search: bool,
    early_goal_test: bool,
    max_nodes: int,
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
        "problem": domain.kind,
        "algorithm": algorithm,
        "goal_description": domain.goal_description,
        "start_state": domain.state_to_json(domain.start_state),
        **domain.result_fields,
        "move_costs": domain.move_costs,
        "config": {
            "graph_search": graph_search,
            "early_goal_test": early_goal_test,
            "max_nodes": max_nodes,
        },
        "solvability": domain.solvability,
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
            "skipped_stale": last_metrics.get("skipped_stale", 0),
            "replaced": last_metrics.get("replaced", 0),
            "solution_cost": nodes[solution_ids[-1]]["path_cost"] if solution_ids else None,
            "max_frontier_size": last_metrics.get("max_frontier_size", 0),
            "avg_branching_factor": avg_branching,
        },
    }
