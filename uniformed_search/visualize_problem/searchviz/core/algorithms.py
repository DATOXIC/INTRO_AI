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
from .types import Node, Problem, is_goal


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
