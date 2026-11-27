"""Cấu trúc dữ liệu cho frontier (hàng đợi, ngăn xếp) và các hàm dựng nút / truy vết lời giải."""

from __future__ import annotations

from typing import Any

from .models import Move, Node, Problem


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
