"""Đóng gói trang tĩnh để đưa lên GitHub Pages.

    python build_site.py            # tạo thư mục dist/
    python -m http.server -d dist   # xem thử cục bộ (không cần server.py)

dist/ chứa giao diện (static/*) và mã Python (py/*.py) để Pyodide chạy trong trình duyệt.
File .py mới (ví dụ ucs_world.py cho bài mới) được tự đưa vào, trừ server.py và test_*.py.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
STATIC = HERE / "static"
DIST = HERE / "dist"
EXCLUDE = {"server.py", "build_site.py"}


def main() -> None:
    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(STATIC, DIST)

    py_dir = DIST / "py"
    py_dir.mkdir()
    files = sorted(
        p.name
        for p in HERE.glob("*.py")
        if p.name not in EXCLUDE and not p.name.startswith("test_")
    )
    for name in files:
        shutil.copy2(HERE / name, py_dir / name)
    (py_dir / "manifest.json").write_text(json.dumps({"files": files}, indent=2), encoding="utf-8")

    # GitHub Pages mặc định chạy Jekyll; tắt đi để mọi file được phục vụ nguyên trạng.
    (DIST / ".nojekyll").write_text("", encoding="utf-8")
    print(f"Đã tạo {DIST} với {len(files)} file Python: {', '.join(files)}")


if __name__ == "__main__":
    main()
