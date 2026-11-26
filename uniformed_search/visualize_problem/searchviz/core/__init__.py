"""Lõi thuật toán: chạy được trên mọi bài toán, không biết gì về giao diện hay HTTP.

  types       Node, Problem, Domain và các hằng số
  primitives  Queue / Stack, child_node, solution
  algorithms  BFS, DFS, UCS, UCS_fast (bản chạy thuần, bám mã giả trên slide)
  pseudocode  mã giả hiển thị, mỗi dòng có tag
  tracing     search_trace: ghi vết từng dòng mã giả thành JSON cho giao diện

Muốn thêm một thuật toán mới: viết bản chạy thuần ở algorithms.py, thêm mã giả ở pseudocode.py,
thêm nhánh ghi vết ở tracing.py và đăng ký tên trong ALGORITHMS (types.py).
"""

from .algorithms import BFS, DFS, UCS, UCS_fast
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
from .types import (
    ALGORITHMS,
    MAX_TRACE_ELEMENTS,
    UCS_ALGORITHMS,
    Domain,
    Move,
    Node,
    Problem,
    is_goal,
    unit_cost,
)

__all__ = [
    "ALGORITHMS", "MAX_TRACE_ELEMENTS", "UCS_ALGORITHMS",
    "BFS", "DFS", "UCS", "UCS_fast",
    "Domain", "Move", "Node", "Problem",
    "Queue", "Stack", "child_node", "dequeue", "enqueue", "is_empty", "is_goal",
    "pop", "push", "solution", "solution_node_ids", "unit_cost",
    "get_source_lines", "search_trace",
]
