"""Bảo vệ kiến trúc module: lõi không biết bài toán, bài toán không biết web; build và server đúng chỗ."""

from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "searchviz"
sys.path.insert(0, str(ROOT / "tools"))

import build_site  # noqa: E402
from searchviz.web.server import resolve_static  # noqa: E402


def imported_layers(layer: str) -> set[str]:
    """Các tầng (core / problems / web) mà module trong ``layer`` import tới."""
    found: set[str] = set()
    for path in (PACKAGE / layer).rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if node.level == 2:  # from ..core import ...
                    found.add(module.split(".")[0])
                elif node.level == 0 and module.startswith("searchviz."):
                    found.add(module.split(".")[1])
    return found


class LayeringTests(unittest.TestCase):
    def test_core_does_not_depend_on_problems_or_web(self) -> None:
        self.assertFalse(imported_layers("core") & {"problems", "web"})

    def test_problems_do_not_depend_on_web(self) -> None:
        self.assertNotIn("web", imported_layers("problems"))


class StaticServingTests(unittest.TestCase):
    def test_serves_every_ui_file_at_top_level(self) -> None:
        for name in ("index.html", "styles.css", "app.js", "theme.js"):
            self.assertIsNotNone(resolve_static("/" + name), name)
        self.assertEqual(resolve_static("/")[0].name, "index.html")

    def test_rejects_traversal_and_unknown_files(self) -> None:
        for path in ("/../README.md", "/..\\README.md", "/searchviz/core/types.py", "/nope.js", "/.env"):
            self.assertIsNone(resolve_static(path), path)


class BuildSiteTests(unittest.TestCase):
    def test_browser_bundle_contains_package_but_not_the_http_server(self) -> None:
        files = build_site.python_files()
        self.assertIn("searchviz/core/tracing.py", files)
        self.assertIn("searchviz/problems/vacuum.py", files)
        self.assertIn("searchviz/web/api.py", files)
        self.assertNotIn("searchviz/web/server.py", files)
        self.assertFalse([f for f in files if "__pycache__" in f])


if __name__ == "__main__":
    unittest.main()
