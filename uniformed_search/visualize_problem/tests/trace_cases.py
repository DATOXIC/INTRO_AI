"""Bộ ca chạy cố định dùng để canh giữ kết quả ghi vết (xem test_golden_traces.py).

Mỗi ca cho ra một vết đầy đủ (mọi bước, mọi nút). Ta lưu dấu vân tay (sha256) của vết đã được xác nhận là đúng;
nếu một thay đổi làm đổi dù chỉ một bước, một câu giải thích hay một chỉ số, test sẽ báo ca nào đổi.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Callable

from searchviz.core import search_trace
from searchviz.problems import get_presets
from searchviz.problems.npuzzle import (
    make_goal_board,
    make_npuzzle_domain,
    shuffle_solvable,
    validate_board,
)
from searchviz.problems.vacuum import make_vacuum_domain, validate_vacuum_state

BFS_DFS_OPTIONS = [(True, True), (True, False), (False, True), (False, False)]


def _npuzzle_boards() -> list[tuple[str, Any, Any]]:
    boards = []
    for preset in get_presets():
        if preset["problem"] != "npuzzle":
            continue
        start = validate_board(preset["start_board"])
        target = validate_board(preset["target_board"])
        boards.append((preset["id"], start, target))
    goal3 = make_goal_board(3)
    for seed, steps in ((1, 6), (2, 8), (3, 9)):
        boards.append((f"shuffle3_{seed}", shuffle_solvable(goal3, steps=steps, seed=seed), goal3))
    goal2 = make_goal_board(2)
    boards.append(("shuffle2_4", shuffle_solvable(goal2, steps=4, seed=4), goal2))
    return boards


def cases() -> list[tuple[str, Callable[[], dict[str, Any]]]]:
    """Danh sách (tên ca, hàm chạy) theo thứ tự cố định."""
    out: list[tuple[str, Callable[[], dict[str, Any]]]] = []

    def add(name: str, make_domain: Callable[[], Any], **kw: Any) -> None:
        out.append((name, lambda: search_trace(make_domain(), **kw)))

    for pid, start, target in _npuzzle_boards():
        def make(s=start, t=target):
            return make_npuzzle_domain(s, t)

        for graph, early in BFS_DFS_OPTIONS:
            for algo in ("bfs", "dfs"):
                add(f"{pid}/{algo}/g{int(graph)}e{int(early)}", make,
                    algorithm=algo, graph_search=graph, early_goal_test=early, max_nodes=90)
        for algo in ("ucs", "ucs_fast"):
            add(f"{pid}/{algo}", make, algorithm=algo, max_nodes=90)

    for preset in get_presets():
        if preset["problem"] != "vacuum":
            continue
        state = validate_vacuum_state(preset["start_state"])

        def make_v(s=state):
            return make_vacuum_domain(s)

        for graph, early in BFS_DFS_OPTIONS:
            for algo in ("bfs", "dfs"):
                add(f"{preset['id']}/{algo}/g{int(graph)}e{int(early)}", make_v,
                    algorithm=algo, graph_search=graph, early_goal_test=early, max_nodes=90)
        for algo in ("ucs", "ucs_fast"):
            add(f"{preset['id']}/{algo}", make_v, algorithm=algo, max_nodes=90)
    return out


def fingerprint(trace: dict[str, Any]) -> str:
    """sha256 của những phần mà giao diện đọc; các trường bổ sung về sau (không đổi ý nghĩa) không làm đổi dấu vân tay."""
    core = {
        "status": trace["status"],
        "algorithm": trace["algorithm"],
        "config": trace["config"],
        "source": [(l["line"], l["tag"], l["code"]) for l in trace["source_lines"]],
        "nodes": trace["nodes"],
        "steps": trace["steps"],
        "solution_ids": trace["solution_ids"],
        "summary": trace["summary"],
    }
    blob = json.dumps(core, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()
