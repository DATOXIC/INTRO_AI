"""Các bài toán (problem) có thể chọn trong giao diện.

Mỗi bài toán là một module trong thư mục này và cung cấp:
  KIND                    tên dùng trong API ("npuzzle", "vacuum", ...)
  presets()               danh sách đề mẫu cho giao diện
  solve(payload, options) dựng Domain từ yêu cầu rồi gọi search_trace, trả về trace JSON

Muốn thêm bài toán mới: tạo module mới theo mẫu vacuum.py, rồi thêm nó vào PROBLEMS bên dưới.
Phần còn lại (thuật toán, ghi vết, giao diện) không cần sửa nếu bài mới tái dùng được các thành phần
hiển thị sẵn có.
"""

from __future__ import annotations

from typing import Any

from . import npuzzle, vacuum

# Thứ tự ở đây là thứ tự hiển thị của các đề mẫu.
PROBLEMS = {
    npuzzle.KIND: npuzzle,
    vacuum.KIND: vacuum,
}


def get_presets() -> list[dict[str, Any]]:
    """Tất cả đề mẫu của mọi bài toán, theo thứ tự đăng ký."""
    presets: list[dict[str, Any]] = []
    for module in PROBLEMS.values():
        presets.extend(module.presets())
    return presets


__all__ = ["PROBLEMS", "get_presets", "npuzzle", "vacuum"]
