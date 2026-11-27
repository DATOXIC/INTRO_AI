"""Đóng gói trang tĩnh để đưa lên GitHub Pages.

    python tools/build_site.py            # tạo thư mục dist/
    python -m http.server -d dist         # xem thử cục bộ (không cần máy chủ Python)

dist/ chứa giao diện (ui/*) và mã Python của package searchviz (py/searchviz/**) để Pyodide
chạy trong trình duyệt. File .py mới trong searchviz/ được tự đưa vào, trừ web/server.py
(máy chủ HTTP chỉ dùng khi chạy cục bộ).
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "ui"
PACKAGE = ROOT / "searchviz"
DIST = ROOT / "dist"
EXCLUDE = {"web/server.py"}


def python_files() -> list[str]:
    """Đường dẫn (tính từ gốc dự án, dùng dấu /) của mọi file .py cần đưa vào trình duyệt."""
    files = []
    for path in sorted(PACKAGE.rglob("*.py")):
        rel = path.relative_to(PACKAGE).as_posix()
        if rel in EXCLUDE or "__pycache__" in path.parts:
            continue
        files.append(f"searchviz/{rel}")
    return files


def main() -> None:
    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(UI, DIST)

    py_dir = DIST / "py"
    files = python_files()
    for rel in files:
        target = py_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, target)
    (py_dir / "manifest.json").write_text(json.dumps({"files": files}, indent=2), encoding="utf-8")

    (DIST / ".nojekyll").write_text("", encoding="utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(f"Đã tạo {DIST} với {len(files)} file Python: {', '.join(files)}")


if __name__ == "__main__":
    main()
