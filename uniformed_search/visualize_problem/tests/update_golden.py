"""Ghi lại dấu vân tay của mọi ca (chỉ chạy khi chủ ý đổi kết quả ghi vết): python tests/update_golden.py"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests import trace_cases

gold = {name: trace_cases.fingerprint(run()) for name, run in trace_cases.cases()}
(ROOT / "tests" / "golden_traces.json").write_text(json.dumps(dict(sorted(gold.items())), indent=0), encoding="utf-8")
print(f"Đã ghi {len(gold)} dấu vân tay.")
