"""Lớp API thuần Python, không phụ thuộc HTTP.

Dùng chung cho hai cách chạy:
  - searchviz.web.server : máy chủ cục bộ (python run.py)
  - ui/pyodide_worker.js : chạy ngay trong trình duyệt (GitHub Pages, không cần máy chủ)

Hàm duy nhất cần gọi là `handle(method, path, payload)` -> (status, dict).
Lớp này chỉ đọc tham số chung rồi giao cho module bài toán trong ``searchviz.problems``.
"""

from __future__ import annotations

from typing import Any

from ..core import ALGORITHMS, get_source_lines
from ..problems import PROBLEMS, get_presets, npuzzle, vacuum
from ..problems.base import SolveOptions, parse_bool, parse_int


def _presets() -> dict[str, Any]:
    return {
        "allowed_sizes": list(npuzzle.ALLOWED_SIZES),
        "problems": list(PROBLEMS),
        "algorithms": list(ALGORITHMS),
        "vacuum_rooms": list(range(vacuum.MIN_ROOMS, vacuum.MAX_ROOMS + 1)),
        "presets": get_presets(),
        "default_source_lines": get_source_lines("bfs", True, True),
    }


def _solve(payload: dict[str, Any]) -> dict[str, Any]:
    problem_kind = payload.get("problem", npuzzle.KIND)
    if problem_kind not in PROBLEMS:
        raise ValueError(f"Tham số 'problem' phải thuộc {tuple(PROBLEMS)}.")
    algorithm = payload.get("algorithm", "bfs")
    if algorithm not in ALGORITHMS:
        raise ValueError(f"Tham số 'algorithm' phải thuộc {ALGORITHMS}.")
    options = SolveOptions(
        algorithm=algorithm,
        graph_search=parse_bool(payload.get("graph_search"), "graph_search", True),
        early_goal_test=parse_bool(payload.get("early_goal_test"), "early_goal_test", True),
        max_nodes=parse_int(payload.get("max_nodes"), "max_nodes", 300, 1, 3000),
        force_run=parse_bool(payload.get("force_run"), "force_run", False),
        edits=payload.get("program"),
    )
    return PROBLEMS[problem_kind].solve(payload, options)


_GET = {
    "/api/presets": lambda _payload: _presets(),
    "/api/health": lambda _payload: {"status": "ok"},
}
_POST = {
    "/api/solve": _solve,
    "/api/shuffle": npuzzle.shuffle,
    "/api/check": npuzzle.check,
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
