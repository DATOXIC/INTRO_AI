"""Phần chung cho mọi bài toán: tùy chọn chạy và các hàm đọc tham số từ yêu cầu JSON."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SolveOptions:
    """Tùy chọn chạy thuật toán, giống nhau cho mọi bài toán."""

    algorithm: str = "bfs"
    graph_search: bool = True
    early_goal_test: bool = True
    max_nodes: int = 300
    force_run: bool = False
    edits: Any = None
    depth_limit: int = 3


def parse_bool(value: Any, name: str, default: bool) -> bool:
    if value is None:
        return default
    if not isinstance(value, bool):
        raise ValueError(f"Tham số '{name}' phải là kiểu boolean.")
    return value


def parse_int(value: Any, name: str, default: int, min_val: int, max_val: int) -> int:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"Tham số '{name}' phải là số nguyên.")
    if not (min_val <= value <= max_val):
        raise ValueError(f"Tham số '{name}' phải nằm trong khoảng [{min_val}, {max_val}].")
    return value
