"""Lớp API thuần Python, không phụ thuộc HTTP.

Dùng chung cho hai cách chạy:
  - server.py  : máy chủ cục bộ (python server.py)
  - pyodide_worker.js : chạy ngay trong trình duyệt (GitHub Pages, không cần máy chủ)

Hàm duy nhất cần gọi là `handle(method, path, payload)` -> (status, dict).
"""

from __future__ import annotations

from typing import Any

from bfs_core import (
    ALGORITHMS,
    ALLOWED_SIZES,
    analyze_solvability,
    get_presets,
    get_source_lines,
    make_goal_board,
    make_npuzzle_domain,
    search_trace,
    shuffle_solvable,
    validate_board,
)
from vacuum_world import make_vacuum_domain, validate_vacuum_state

PROBLEMS = ("npuzzle", "vacuum")


def _parse_bool(value: Any, name: str, default: bool) -> bool:
    if value is None:
        return default
    if not isinstance(value, bool):
        raise ValueError(f"Tham số '{name}' phải là kiểu boolean.")
    return value


def _parse_int(value: Any, name: str, default: int, min_val: int, max_val: int) -> int:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"Tham số '{name}' phải là số nguyên.")
    if not (min_val <= value <= max_val):
        raise ValueError(f"Tham số '{name}' phải nằm trong khoảng [{min_val}, {max_val}].")
    return value


def _presets() -> dict[str, Any]:
    return {
        "allowed_sizes": list(ALLOWED_SIZES),
        "problems": list(PROBLEMS),
        "algorithms": list(ALGORITHMS),
        "presets": get_presets(),
        "default_source_lines": get_source_lines("bfs", True, True),
    }


def _solve(payload: dict[str, Any]) -> dict[str, Any]:
    problem_kind = payload.get("problem", "npuzzle")
    if problem_kind not in PROBLEMS:
        raise ValueError(f"Tham số 'problem' phải thuộc {PROBLEMS}.")
    algorithm = payload.get("algorithm", "bfs")
    if algorithm not in ALGORITHMS:
        raise ValueError(f"Tham số 'algorithm' phải thuộc {ALGORITHMS}.")
    graph_search = _parse_bool(payload.get("graph_search"), "graph_search", True)
    early_goal_test = _parse_bool(payload.get("early_goal_test"), "early_goal_test", True)
    max_nodes = _parse_int(payload.get("max_nodes"), "max_nodes", 300, 1, 3000)
    force_run = _parse_bool(payload.get("force_run"), "force_run", False)

    if problem_kind == "vacuum":
        domain = make_vacuum_domain(validate_vacuum_state(payload.get("start_state")))
        return search_trace(
            domain,
            algorithm=algorithm,
            graph_search=graph_search,
            early_goal_test=early_goal_test,
            max_nodes=max_nodes,
        )

    raw_start = payload.get("start_board")
    if raw_start is None:
        raise ValueError("Thiếu trường 'start_board'.")
    size = _parse_int(payload.get("size"), "size", len(raw_start) if isinstance(raw_start, list) else 3, 2, 4)
    start_board = validate_board(raw_start, expected_size=size)

    raw_target = payload.get("target_board")
    target_board = (
        validate_board(raw_target, expected_size=size) if raw_target is not None else make_goal_board(size)
    )

    solvability = analyze_solvability(start_board, target_board)
    if not solvability["solvable"] and not force_run:
        return {
            "status": "unsolvable_blocked",
            "problem": "npuzzle",
            "algorithm": algorithm,
            "size": size,
            "start_board": [list(r) for r in start_board],
            "target_board": [list(r) for r in target_board],
            "config": {
                "graph_search": graph_search,
                "early_goal_test": early_goal_test,
                "max_nodes": max_nodes,
            },
            "solvability": solvability,
            "source_lines": get_source_lines(algorithm, graph_search, early_goal_test),
            "nodes": [],
            "steps": [],
            "solution_ids": None,
            "summary": None,
        }

    return search_trace(
        make_npuzzle_domain(start_board, target_board),
        algorithm=algorithm,
        graph_search=graph_search,
        early_goal_test=early_goal_test,
        max_nodes=max_nodes,
    )


def _shuffle(payload: dict[str, Any]) -> dict[str, Any]:
    size = _parse_int(payload.get("size"), "size", 3, 2, 4)
    if size not in ALLOWED_SIZES:
        raise ValueError(f"Kích thước phải thuộc {ALLOWED_SIZES}.")
    steps = _parse_int(payload.get("steps"), "steps", 5, 0, 50)
    raw_seed = payload.get("seed")
    seed = _parse_int(raw_seed, "seed", 0, -2_147_483_648, 2_147_483_647) if raw_seed is not None else None

    raw_target = payload.get("target_board")
    target_board = (
        validate_board(raw_target, expected_size=size) if raw_target is not None else make_goal_board(size)
    )
    shuffled = shuffle_solvable(target_board, steps=steps, seed=seed)
    return {
        "size": size,
        "start_board": [list(r) for r in shuffled],
        "target_board": [list(r) for r in target_board],
        "solvability": analyze_solvability(shuffled, target_board),
    }


def _check(payload: dict[str, Any]) -> dict[str, Any]:
    raw_start = payload.get("start_board")
    if raw_start is None:
        raise ValueError("Thiếu trường 'start_board'.")
    start_board = validate_board(raw_start)
    size = len(start_board)
    raw_target = payload.get("target_board")
    target_board = (
        validate_board(raw_target, expected_size=size) if raw_target is not None else make_goal_board(size)
    )
    return {
        "valid": True,
        "size": size,
        "solvability": analyze_solvability(start_board, target_board),
    }


_GET = {
    "/api/presets": lambda _payload: _presets(),
    "/api/health": lambda _payload: {"status": "ok"},
}
_POST = {
    "/api/solve": _solve,
    "/api/shuffle": _shuffle,
    "/api/check": _check,
}


def handle(method: str, path: str, payload: dict[str, Any] | None = None) -> tuple[int, dict[str, Any]]:
    """Xử lý một lời gọi API; trả về (mã HTTP, nội dung JSON)."""
    routes = _GET if method.upper() == "GET" else _POST
    route = routes.get(path)
    if route is None:
        label = "Đường dẫn" if method.upper() == "GET" else "Endpoint"
        return 404, {"error": f"{label} không tồn tại: {path}"}
    try:
        return 200, route(payload or {})
    except ValueError as exc:
        if path == "/api/check":
            return 400, {"valid": False, "error": str(exc)}
        return 400, {"error": str(exc)}
