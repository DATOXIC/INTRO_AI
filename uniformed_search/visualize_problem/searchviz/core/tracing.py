"""Ghi vết từng bước chạy của BFS / DFS / UCS thành dữ liệu JSON cho giao diện.

``search_trace(domain, ...)`` dựng chương trình của thuật toán (có thể kèm chỉnh sửa của người dùng: tắt dòng,
đổi chỗ dòng), chạy nó bằng ``engine.Engine`` trên một ``Domain`` bất kỳ rồi trả về toàn bộ nút + từng bước
(mỗi bước ứng với một dòng mã giả), kèm frontier/explored tại thời điểm đó.
"""

from __future__ import annotations

from typing import Any

from .engine import Engine
from .models import ALGORITHMS, UCS_ALGORITHMS, Domain
from .program import apply_edits, build_program, render_lines
from .recorder import build_result


def search_trace(
    domain: Domain,
    *,
    algorithm: str = "bfs",
    graph_search: bool = True,
    early_goal_test: bool = True,
    max_nodes: int = 300,
    edits: Any = None,
) -> dict[str, Any]:
    """Chạy thuật toán có ghi vết trên ``domain`` và trả về toàn bộ vết từng dòng mã giả.

    Args:
        domain: Bài toán (trạng thái đầu, hành động, đích, cách xuất JSON).
        algorithm: ``"bfs"`` (FIFO), ``"dfs"`` (LIFO) hoặc ``"ucs"`` / ``"ucs_fast"`` (hàng đợi ưu tiên).
        graph_search: True thì lọc trùng bằng explored/frontier, False là Tree Search.
        early_goal_test: True thì kiểm tra đích khi sinh nút con, False thì khi lấy ra khỏi frontier.
        max_nodes: Số nút mở rộng tối đa trước khi dừng an toàn.
        edits: Chỉnh sửa mã giả ``{"disabled": [tag], "order": {khối: [tag]}}`` (xem ``program.py``).
    """
    if algorithm not in ALGORITHMS:
        raise ValueError(f"Thuật toán phải thuộc {ALGORITHMS}, nhận được: {algorithm!r}")
    if not (1 <= max_nodes <= 3000):
        raise ValueError("max_nodes phải nằm trong khoảng [1, 3000].")
    if algorithm in UCS_ALGORITHMS:
        # UCS luôn là Graph Search và kiểm tra đích khi pop (đúng slide), bất kể hai tùy chọn kia.
        graph_search, early_goal_test = True, False

    program, disabled, applied = apply_edits(build_program(algorithm, graph_search, early_goal_test), edits)
    source_lines = render_lines(program, disabled)
    engine = Engine(domain, program, source_lines, disabled, max_nodes=max_nodes)
    engine.run()

    extra: dict[str, Any] = {}
    if applied["disabled"] or applied["order"]:
        extra["program"] = applied
    if engine.error:
        extra["error"] = engine.error
    return build_result(
        domain=domain,
        algorithm=algorithm,
        status=engine.status,
        graph_search=graph_search,
        early_goal_test=early_goal_test,
        max_nodes=max_nodes,
        source_lines=source_lines,
        nodes=engine.nodes,
        steps=engine.steps,
        solution_ids=engine.solution_ids,
        extra=extra,
    )
