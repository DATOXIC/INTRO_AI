"""Kiểu dữ liệu nền của bộ máy tìm kiếm: Node, Problem, Domain và các hằng số dùng chung.

Bộ máy không biết gì về một bài toán cụ thể. Mỗi bài toán (n-Puzzle, Vacuum, ...) tự mô tả
mình bằng một ``Domain`` (trạng thái đầu, đích, hành động, chuyển trạng thái, cách xuất JSON),
nên cùng một mã giả, một định dạng trace và một giao diện dùng được cho mọi bài.
"""

from __future__ import annotations

from dataclasses import dataclass, field
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
