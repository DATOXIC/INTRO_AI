"""Mã giả hiển thị trong giao diện, dựng từ cây lệnh trong ``program.py``.

Mỗi dòng có một ``tag`` để trình ghi vết tô sáng đúng dòng; các cờ ``block / unit / can_up / can_down /
disabled / locked`` cho giao diện biết dòng nào tắt được, đổi chỗ được.
"""

from __future__ import annotations

from typing import Any

from .models import UCS_ALGORITHMS
from .program import apply_edits, build_program, render_lines


def get_source_lines(
    algorithm: str = "bfs",
    graph_search: bool = True,
    early_goal_test: bool = True,
    edits: Any = None,
) -> list[dict[str, Any]]:
    """Các dòng mã giả có đánh số, khớp với tùy chọn đang chọn (và chỉnh sửa nếu có)."""
    if algorithm in UCS_ALGORITHMS:
        graph_search, early_goal_test = True, False
    program, disabled, _ = apply_edits(build_program(algorithm, graph_search, early_goal_test), edits)
    return render_lines(program, disabled)


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
