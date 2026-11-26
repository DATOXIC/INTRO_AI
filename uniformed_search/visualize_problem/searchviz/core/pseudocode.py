"""Mã giả hiển thị trong giao diện: từng dòng có một ``tag`` để trình ghi vết tô sáng đúng dòng."""

from __future__ import annotations

from typing import Any

from .types import UCS_ALGORITHMS


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
