"""Local HTTP server for the Search Interactive Debugger (BFS / DFS on n-Puzzle and Vacuum Robot)."""

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

from .api import handle

UI_DIR = Path(__file__).resolve().parents[2] / "ui"
MAX_BODY_BYTES = 65_536

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
}


def resolve_static(path: str) -> tuple[Path, str] | None:
    """Đổi đường dẫn URL thành (file trong ui/, content-type); chỉ phục vụ file nằm thẳng trong ui/."""
    name = "index.html" if path == "/" else path.lstrip("/")
    if not name or "/" in name or "\\" in name or name.startswith("."):
        return None
    content_type = CONTENT_TYPES.get(Path(name).suffix.lower())
    file_path = UI_DIR / name
    if content_type is None or not file_path.is_file():
        return None
    return file_path, content_type


class DebuggerRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler serving static UI assets and JSON BFS APIs."""

    server_version = "SearchDebugger/2.0"

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

        static = resolve_static(path)
        if static is not None:
            file_path, content_type = static
            self._send_bytes(HTTPStatus.OK, content_type, file_path.read_bytes())
            return

        if path.startswith("/api/"):
            status, body = handle("GET", path)
            self._send_json(HTTPStatus(status), body)
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"error": f"Đường dẫn không tồn tại: {path}"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path

        try:
            payload = self._read_json_body()
        except ValueError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        status, body = handle("POST", path, payload)
        self._send_json(HTTPStatus(status), body)


def create_server(host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    """Create a ThreadingHTTPServer bound to host:port."""
    ThreadingHTTPServer.allow_reuse_address = True
    server = ThreadingHTTPServer((host, port), DebuggerRequestHandler)
    server.daemon_threads = True
    return server


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Chạy ứng dụng Search Interactive Debugger (BFS/DFS).")
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
    print(f"Search Debugger đang chạy tại: {url}")
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
