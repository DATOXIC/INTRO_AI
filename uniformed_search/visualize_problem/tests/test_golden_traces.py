"""Canh giữ kết quả ghi vết: mọi ca trong trace_cases.py phải cho đúng dấu vân tay đã lưu.

Dấu vân tay được lấy từ bộ ghi vết viết tay trước khi chuyển sang trình thực thi chương trình
(engine.py), nên test này chứng minh việc tái cấu trúc không đổi một bước nào.
Nếu bạn CHỦ Ý đổi câu chữ/định dạng, chạy lại ``python tests/update_golden.py`` rồi xem diff.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from tests import trace_cases

GOLDEN = json.loads((Path(__file__).parent / "golden_traces.json").read_text(encoding="utf-8"))


class GoldenTraceTests(unittest.TestCase):
    def test_case_list_matches_golden_file(self) -> None:
        self.assertEqual(sorted(name for name, _ in trace_cases.cases()), sorted(GOLDEN))

    def test_every_trace_is_unchanged(self) -> None:
        changed = []
        for name, run in trace_cases.cases():
            if trace_cases.fingerprint(run()) != GOLDEN[name]:
                changed.append(name)
        self.assertEqual(changed, [], f"{len(changed)} ca đã đổi kết quả, ví dụ: {changed[:5]}")


if __name__ == "__main__":
    unittest.main()
