"""Lõi thuật toán: chạy được trên mọi bài toán, không biết gì về giao diện hay HTTP.

  models      Node, Problem, Domain và các hằng số
  primitives  Queue / Stack, child_node, solution
  algorithms  BFS, DFS, UCS, UCS_fast, DLS, IDS (bản chạy thuần, bám mã giả trên slide)
  recursive   DLS và IDS đệ quy có ghi vết (ngăn xếp lời gọi thay cho frontier)
  program     mã giả của từng thuật toán dưới dạng cây lệnh; tắt dòng, đổi chỗ dòng
  engine      trình thực thi cây lệnh, mỗi dòng mã giả chạy một bước và được ghi lại
  recorder    ghi nút và từng bước, gói kết quả JSON
  pseudocode  các dòng mã giả để hiển thị
  tracing     search_trace: điểm vào duy nhất để chạy một thuật toán có ghi vết

Muốn thêm một thuật toán mới: viết bản chạy thuần ở algorithms.py, dựng cây lệnh ở program.py, viết hàm xử lý
cho từng dòng mới ở engine.py (h_<tag> cho dòng thường, c_<tag> cho dòng if) và đăng ký tên trong ALGORITHMS
(models.py). tests/test_golden_traces.py sẽ báo ngay nếu thuật toán cũ bị đổi kết quả.
"""

from .algorithms import BFS, DFS, DLS, IDS, UCS, UCS_fast
from .primitives import (
    Queue,
    Stack,
    child_node,
    dequeue,
    enqueue,
    is_empty,
    pop,
    push,
    solution,
    solution_node_ids,
)
from .pseudocode import get_source_lines
from .tracing import search_trace
from .models import (
    ALGORITHMS,
    CUTOFF,
    DEFAULT_DEPTH_LIMIT,
    MAX_DEPTH_LIMIT,
    MAX_TRACE_ELEMENTS,
    RECURSIVE_ALGORITHMS,
    UCS_ALGORITHMS,
    Domain,
    Move,
    Node,
    Problem,
    is_goal,
    unit_cost,
)

__all__ = [
    "ALGORITHMS", "MAX_TRACE_ELEMENTS", "UCS_ALGORITHMS", "RECURSIVE_ALGORITHMS",
    "CUTOFF", "DEFAULT_DEPTH_LIMIT", "MAX_DEPTH_LIMIT",
    "BFS", "DFS", "DLS", "IDS", "UCS", "UCS_fast",
    "Domain", "Move", "Node", "Problem",
    "Queue", "Stack", "child_node", "dequeue", "enqueue", "is_empty", "is_goal",
    "pop", "push", "solution", "solution_node_ids", "unit_cost",
    "get_source_lines", "search_trace",
]
