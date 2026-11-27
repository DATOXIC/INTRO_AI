"""Các thuật toán chạy thuần (không ghi vết), bám sát mã giả trên slide: BFS, DFS, UCS, UCS tối ưu."""

from __future__ import annotations

import heapq
from itertools import count
from typing import Any

from .primitives import (
    Queue,
    Stack,
    child_node,
    dequeue,
    enqueue,
    is_empty,
    pop,
    push,
    solution,
)
from .models import CUTOFF, Node, Problem, is_goal


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
                frontier[pos] = (child.path_cost, next(arrival), child)
                heapq.heapify(frontier)
    return None


def _is_cycle(node: Node) -> bool:
    ancestor = node.parent
    while ancestor is not None:
        if ancestor.state == node.state:
            return True
        ancestor = ancestor.parent
    return False


def _recursive_dls(puzzle: Problem, node: Node, limit: int, check_cycle: bool) -> Node | str | None:
    if is_goal(puzzle, node.state):
        return node
    if limit == 0:
        return CUTOFF

    cutoff_occurred = False
    for move in puzzle.get_moves(node.state):
        child = child_node(puzzle, node, move)
        if check_cycle and _is_cycle(child):
            continue
        result = _recursive_dls(puzzle, child, limit - 1, check_cycle)
        if result == CUTOFF:
            cutoff_occurred = True
        elif result is not None:
            return result
    return CUTOFF if cutoff_occurred else None


def DLS(puzzle: Problem, limit: int, check_cycle: bool = True) -> list[Any] | str | None:
    """DLS đệ quy đúng mã giả (AIMA): trả về danh sách trạng thái lời giải, ``CUTOFF`` hoặc ``None`` (failure)."""
    result = _recursive_dls(puzzle, Node(puzzle.start_state), limit, check_cycle)
    return solution(result) if isinstance(result, Node) else result


def IDS(puzzle: Problem, max_depth: int | None = None, check_cycle: bool = True) -> list[Any] | str | None:
    """IDS: lặp DLS với giới hạn 0, 1, 2, ... đến khi kết quả khác ``CUTOFF`` (hoặc quá ``max_depth`` thì ``CUTOFF``)."""
    for depth in count():
        if max_depth is not None and depth > max_depth:
            return CUTOFF
        result = DLS(puzzle, depth, check_cycle)
        if result != CUTOFF:
            return result
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
