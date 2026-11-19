"""Local HTTP server for the n-Puzzle BFS Interactive Debugger."""

from __future__ import annotations

import argparse
import json
import sys
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from bfs_core import (
    ALLOWED_SIZES,
    BFS_trace,
    analyze_solvability,
    get_bfs_source_lines,
    get_presets,
    make_goal_board,
    shuffle_solvable,
    validate_board,
)

STATIC_DIR = Path(__file__).resolve().parent / "static"
MAX_BODY_BYTES = 65_536

STATIC_ROUTES: dict[str, tuple[str, str]] = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "application/javascript; charset=utf-8"),
}


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


class DebuggerRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler serving static UI assets and JSON BFS APIs."""

    server_version = "NPuzzleBFSDebugger/1.0"

    def log_message(self, format: str, *args: Any) -> None:
        """Keep terminal logs concise."""
        sys.stderr.write(f"[HTTP] {self.address_string()} - {format % args}\n")

    def _send_bytes(self, status: HTTPStatus, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send_bytes(status, "application/json; charset=utf-8", data)

    def _read_json_body(self) -> dict[str, Any]:
        raw_len = self.headers.get("Content-Length")
        if raw_len is None:
            raise ValueError("Thiếu header Content-Length.")
        try:
            length = int(raw_len)
        except ValueError as exc:
            raise ValueError("Header Content-Length không hợp lệ.") from exc
        if length < 0 or length > MAX_BODY_BYTES:
            raise ValueError(f"Kích thước payload phải nằm trong khoảng [0, {MAX_BODY_BYTES}] bytes.")
        raw_bytes = self.rfile.read(length)
        if not raw_bytes:
            return {}
        try:
            parsed = json.loads(raw_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Payload JSON không hợp lệ.") from exc
        if not isinstance(parsed, dict):
            raise ValueError("Payload JSON phải là một object.")
        return parsed

    def do_GET(self) -> None:
        path = urlparse(self.path).path

        if path in STATIC_ROUTES:
            filename, content_type = STATIC_ROUTES[path]
            file_path = STATIC_DIR / filename
            if not file_path.is_file():
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"Không tìm thấy tệp giao diện {filename}."})
                return
            self._send_bytes(HTTPStatus.OK, content_type, file_path.read_bytes())
            return

        if path == "/api/presets":
            self._send_json(
                HTTPStatus.OK,
                {
                    "allowed_sizes": list(ALLOWED_SIZES),
                    "presets": get_presets(),
                    "default_source_lines": get_bfs_source_lines(True, True),
                },
            )
            return

        if path == "/api/health":
            self._send_json(HTTPStatus.OK, {"status": "ok"})
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"error": f"Đường dẫn không tồn tại: {path}"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path

        try:
            payload = self._read_json_body()
        except ValueError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if path == "/api/solve":
            self._handle_solve(payload)
            return

        if path == "/api/shuffle":
            self._handle_shuffle(payload)
            return

        if path == "/api/check":
            self._handle_check(payload)
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"error": f"Endpoint không tồn tại: {path}"})

    def _handle_solve(self, payload: dict[str, Any]) -> None:
        try:
            raw_start = payload.get("start_board")
            if raw_start is None:
                raise ValueError("Thiếu trường 'start_board'.")
            size = _parse_int(payload.get("size"), "size", len(raw_start) if isinstance(raw_start, list) else 3, 2, 4)
            start_board = validate_board(raw_start, expected_size=size)

            raw_target = payload.get("target_board")
            target_board = (
                validate_board(raw_target, expected_size=size)
                if raw_target is not None
                else make_goal_board(size)
            )
            graph_search = _parse_bool(payload.get("graph_search"), "graph_search", True)
            early_goal_test = _parse_bool(payload.get("early_goal_test"), "early_goal_test", True)
            max_nodes = _parse_int(payload.get("max_nodes"), "max_nodes", 300, 1, 3000)
            force_run = _parse_bool(payload.get("force_run"), "force_run", False)

            solvability = analyze_solvability(start_board, target_board)
            if not solvability["solvable"] and not force_run:
                self._send_json(
                    HTTPStatus.OK,
                    {
                        "status": "unsolvable_blocked",
                        "size": size,
                        "start_board": [list(r) for r in start_board],
                        "target_board": [list(r) for r in target_board],
                        "config": {
                            "graph_search": graph_search,
                            "early_goal_test": early_goal_test,
                            "max_nodes": max_nodes,
                        },
                        "solvability": solvability,
                        "source_lines": get_bfs_source_lines(graph_search, early_goal_test),
                        "nodes": [],
                        "steps": [],
                        "solution_ids": None,
                        "summary": None,
                    },
                )
                return

            result = BFS_trace(
                start_board,
                target_board,
                graph_search=graph_search,
                early_goal_test=early_goal_test,
                max_nodes=max_nodes,
            )
            self._send_json(HTTPStatus.OK, result)
        except ValueError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

    def _handle_shuffle(self, payload: dict[str, Any]) -> None:
        try:
            size = _parse_int(payload.get("size"), "size", 3, 2, 4)
            if size not in ALLOWED_SIZES:
                raise ValueError(f"Kích thước phải thuộc {ALLOWED_SIZES}.")
            steps = _parse_int(payload.get("steps"), "steps", 5, 0, 50)
            raw_seed = payload.get("seed")
            seed = _parse_int(raw_seed, "seed", 0, -2_147_483_648, 2_147_483_647) if raw_seed is not None else None

            raw_target = payload.get("target_board")
            target_board = (
                validate_board(raw_target, expected_size=size)
                if raw_target is not None
                else make_goal_board(size)
            )
            shuffled = shuffle_solvable(target_board, steps=steps, seed=seed)
            solvability = analyze_solvability(shuffled, target_board)
            self._send_json(
                HTTPStatus.OK,
                {
                    "size": size,
                    "start_board": [list(r) for r in shuffled],
                    "target_board": [list(r) for r in target_board],
                    "solvability": solvability,
                },
            )
        except ValueError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

    def _handle_check(self, payload: dict[str, Any]) -> None:
        try:
            raw_start = payload.get("start_board")
            if raw_start is None:
                raise ValueError("Thiếu trường 'start_board'.")
            start_board = validate_board(raw_start)
            size = len(start_board)
            raw_target = payload.get("target_board")
            target_board = (
                validate_board(raw_target, expected_size=size)
                if raw_target is not None
                else make_goal_board(size)
            )
            self._send_json(
                HTTPStatus.OK,
                {
                    "valid": True,
                    "size": size,
                    "solvability": analyze_solvability(start_board, target_board),
                },
            )
        except ValueError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"valid": False, "error": str(exc)})


def create_server(host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    """Create a ThreadingHTTPServer bound to host:port."""
    ThreadingHTTPServer.allow_reuse_address = True
    server = ThreadingHTTPServer((host, port), DebuggerRequestHandler)
    server.daemon_threads = True
    return server


def main() -> None:
    parser = argparse.ArgumentParser(description="Chạy ứng dụng n-Puzzle BFS Interactive Debugger.")
    parser.add_argument("--host", default="127.0.0.1", help="Địa chỉ lắng nghe (mặc định: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8765, help="Cổng HTTP (mặc định: 8765)")
    parser.add_argument("--no-browser", action="store_true", help="Không tự động mở trình duyệt")
    args = parser.parse_args()

    try:
        server = create_server(args.host, args.port)
    except OSError:
        server = create_server(args.host, 0)

    actual_port = server.server_address[1]
    url = f"http://{args.host}:{actual_port}/"
    print(f"n-Puzzle BFS Debugger đang chạy tại: {url}")
    print("Nhấn Ctrl+C để dừng server.")

    if not args.no_browser:
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nĐã dừng server.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
