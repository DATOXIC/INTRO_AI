"""Chương trình (mã giả) của từng thuật toán dưới dạng cây lệnh, để có thể bỏ lệnh hoặc đổi chỗ lệnh.

Mỗi dòng mã giả là một ``Stmt`` có ``tag`` cố định. Trình thực thi (engine.py) chạy cây lệnh này và ghi
lại từng bước, nên việc tắt một dòng hay đổi thứ tự các dòng cùng khối đều cho ra kết quả chạy thật.

Quy ước về chỉnh sửa (``edits``):
  disabled : danh sách tag bị tắt. Dòng thường bị bỏ qua; dòng ``if`` coi như điều kiện luôn đúng.
             Dòng cấu trúc (def, while_loop, for_move, return_none) không tắt được.
  order    : {tên khối: [tag, ...]} thứ tự mới của các lệnh con trong khối đó. Khối gốc tên là "root",
             các khối còn lại mang tag của dòng mở khối (while_loop, for_move, check_duplicate, ...).
Tag lạ bị bỏ qua và tag còn thiếu giữ vị trí cũ, nên chỉnh sửa còn lại từ thuật toán khác vẫn an toàn.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Dòng cấu trúc: không tắt được (bỏ chúng thì chương trình không còn là thuật toán nữa).
LOCKED_TAGS = frozenset({"def", "while_loop", "for_move", "return_none"})
# Dòng đứng yên: tiêu đề hàm luôn ở đầu, `return None` luôn ở cuối.
FIXED_TAGS = frozenset({"def", "return_none"})
ROOT_BLOCK = "root"


@dataclass
class Stmt:
    tag: str
    code: str  # không thụt lề; độ sâu do vị trí trong cây quyết định
    kind: str = "simple"  # simple | while | for | if | elif
    body: list["Stmt"] = field(default_factory=list)
    orelse: "Stmt | None" = None  # nhánh elif nối ngay sau một dòng if


@dataclass
class Program:
    algorithm: str
    name: str
    graph_search: bool
    early_goal_test: bool
    body: list[Stmt]


def _s(tag: str, code: str, kind: str = "simple", body: list[Stmt] | None = None, orelse: Stmt | None = None) -> Stmt:
    return Stmt(tag, code, kind, body or [], orelse)


def build_program(algorithm: str, graph_search: bool = True, early_goal_test: bool = True) -> Program:
    """Dựng chương trình mặc định (chưa chỉnh sửa) của một thuật toán."""
    if algorithm == "ucs":
        for_body = [
            _s("make_child", "child = child_node(cur_node, move)"),
            _s(
                "check_duplicate",
                "if child not in explored and child not in frontier:",
                "if",
                [_s("enqueue_child", "enqueue(frontier, child)")],
                orelse=_s(
                    "check_better",
                    "elif child in frontier with higher path_cost:",
                    "elif",
                    [_s("replace_child", "replace(frontier, child)")],
                ),
            ),
        ]
        loop = [
            _s("dequeue", "cur_node = dequeue(frontier)   # g nhỏ nhất"),
            _s("check_late_goal", "if is_goal(cur_node): return solution(cur_node)"),
            _s("add_explored", "explored.add(cur_node.state)"),
            _s("for_move", "for move in actions(cur_node):", "for", for_body),
        ]
        body = [
            _s("init_root", "root = Node(problem.start_state, path_cost=0)"),
            _s("init_queue", "frontier = PriorityQueue(); enqueue(frontier, root)"),
            _s("init_explored", "explored = set()"),
            _s("while_loop", "while not is_empty(frontier):", "while", loop),
            _s("return_none", "return None"),
        ]
        return Program(algorithm, "UCS", True, False, body)

    if algorithm == "ucs_fast":
        for_body = [
            _s("make_child", "child = child_node(cur_node, move)"),
            _s("check_explored_child", "if child.state in explored: continue"),
            _s(
                "check_best",
                "if child.state not in best_cost or child.path_cost < best_cost[child.state]:",
                "if",
                [
                    _s("update_best", "best_cost[child.state] = child.path_cost"),
                    _s("enqueue_child", "enqueue(frontier, child)"),
                ],
            ),
        ]
        loop = [
            _s("dequeue", "cur_node = dequeue(frontier)   # g nhỏ nhất"),
            _s("check_stale", "if cur_node.state in explored: continue"),
            _s("check_late_goal", "if is_goal(cur_node): return solution(cur_node)"),
            _s("add_explored", "explored.add(cur_node.state)"),
            _s("for_move", "for move in actions(cur_node):", "for", for_body),
        ]
        body = [
            _s("init_root", "root = Node(problem.start_state, path_cost=0)"),
            _s("init_queue", "frontier = PriorityQueue(); enqueue(frontier, root)"),
            _s("init_best", "best_cost = {root.state: 0}"),
            _s("init_explored", "explored = set()"),
            _s("while_loop", "while not is_empty(frontier):", "while", loop),
            _s("return_none", "return None"),
        ]
        return Program(algorithm, "UCS_nhanh", True, False, body)

    # BFS / DFS: cùng một bộ khung, khác cấu trúc frontier
    is_dfs = algorithm == "dfs"
    name = "DFS" if is_dfs else "BFS"
    make_frontier = "Stack(); push(frontier, root)" if is_dfs else "Queue(); enqueue(frontier, root)"
    take = "pop(frontier)" if is_dfs else "dequeue(frontier)"
    put = "push(frontier, child)" if is_dfs else "enqueue(frontier, child)"

    tail: list[Stmt] = []
    if early_goal_test:
        tail.append(_s("check_early_goal", "if is_goal(child): return solution(child)"))
    tail.append(_s("enqueue_child", put))

    for_body = [_s("make_child", "child = child_node(cur_node, move)")]
    if graph_search:
        for_body.append(_s("check_duplicate", "if child not in explored and child not in frontier:", "if", tail))
    else:
        for_body.extend(tail)

    loop = [_s("dequeue", f"cur_node = {take}")]
    if not early_goal_test:
        loop.append(_s("check_late_goal", "if is_goal(cur_node): return solution(cur_node)"))
    if graph_search:
        loop.append(_s("add_explored", "explored.add(cur_node.state)"))
    loop.append(_s("for_move", "for move in actions(cur_node):", "for", for_body))

    body = [_s("init_root", "root = Node(problem.start_state)")]
    if early_goal_test:
        body.append(_s("check_root_goal", "if is_goal(root): return solution(root)"))
    body.append(_s("init_queue", f"frontier = {make_frontier}"))
    if graph_search:
        body.append(_s("init_explored", "explored = set()"))
    body.append(_s("while_loop", "while not is_empty(frontier):", "while", loop))
    body.append(_s("return_none", "return None"))
    return Program(algorithm, name, graph_search, early_goal_test, body)


# ── Chỉnh sửa ───────────────────────────────────────────────────────────────

def _blocks(program: Program) -> dict[str, list[Stmt]]:
    """Mọi khối có thể đổi thứ tự: tên khối -> danh sách lệnh con (tham chiếu thật, sửa tại chỗ)."""
    found: dict[str, list[Stmt]] = {ROOT_BLOCK: program.body}

    def walk(stmts: list[Stmt]) -> None:
        for st in stmts:
            cur: Stmt | None = st
            while cur is not None:
                if cur.body:
                    found[cur.tag] = cur.body
                    walk(cur.body)
                cur = cur.orelse

    walk(program.body)
    return found


def normalize_edits(edits: Any) -> dict[str, Any]:
    """Kiểm tra hình dạng của ``edits`` (lỗi hình dạng -> ValueError), trả về dạng chuẩn."""
    if edits is None:
        return {"disabled": [], "order": {}}
    if not isinstance(edits, dict):
        raise ValueError("Tham số 'program' phải là một object {disabled, order}.")
    disabled = edits.get("disabled", [])
    order = edits.get("order", {})
    if not isinstance(disabled, list) or not all(isinstance(t, str) for t in disabled):
        raise ValueError("'program.disabled' phải là danh sách tag (chuỗi).")
    if not isinstance(order, dict) or not all(
        isinstance(k, str) and isinstance(v, list) and all(isinstance(t, str) for t in v) for k, v in order.items()
    ):
        raise ValueError("'program.order' phải có dạng {khối: [tag, ...]}.")
    if len(disabled) > 64 or len(order) > 64 or any(len(v) > 64 for v in order.values()):
        raise ValueError("'program' quá lớn.")
    return {"disabled": disabled, "order": order}


def apply_edits(program: Program, edits: Any) -> tuple[Program, frozenset[str], dict[str, Any]]:
    """Áp dụng chỉnh sửa lên chương trình. Trả về (chương trình mới, tập tag bị tắt, chỉnh sửa đã hiệu lực)."""
    clean = normalize_edits(edits)
    prog = _clone(program)
    blocks = _blocks(prog)
    all_tags = {tag for block in blocks.values() for st in block for tag in _chain_tags(st)}

    disabled = frozenset(t for t in clean["disabled"] if t in all_tags and t not in LOCKED_TAGS)

    applied_order: dict[str, list[str]] = {}
    for block_name, wanted in clean["order"].items():
        block = blocks.get(block_name)
        if block is None:
            continue
        movable = [st for st in block if st.tag not in FIXED_TAGS]
        by_tag = {st.tag: st for st in movable}
        picked: list[Stmt] = []
        for tag in wanted:
            st = by_tag.pop(tag, None)  # tag lạ hoặc lặp bị bỏ qua
            if st is not None:
                picked.append(st)
        picked.extend(st for st in movable if st.tag in by_tag)  # tag còn thiếu: giữ thứ tự cũ
        if [s.tag for s in picked] == [s.tag for s in movable]:
            continue
        fixed_tail = [st for st in block if st.tag in FIXED_TAGS]
        block[:] = picked + fixed_tail
        applied_order[block_name] = [s.tag for s in picked]

    applied = {"disabled": sorted(disabled), "order": applied_order}
    return prog, disabled, applied


def _chain_tags(st: Stmt) -> list[str]:
    tags = []
    cur: Stmt | None = st
    while cur is not None:
        tags.append(cur.tag)
        for child in cur.body:
            tags.extend(_chain_tags(child))
        cur = cur.orelse
    return tags


def _clone(program: Program) -> Program:
    def copy(st: Stmt) -> Stmt:
        return Stmt(st.tag, st.code, st.kind, [copy(c) for c in st.body], copy(st.orelse) if st.orelse else None)

    return Program(program.algorithm, program.name, program.graph_search, program.early_goal_test,
                   [copy(s) for s in program.body])


# ── Hiển thị ────────────────────────────────────────────────────────────────

def render_lines(program: Program, disabled: frozenset[str] = frozenset()) -> list[dict[str, Any]]:
    """Các dòng mã giả đánh số, kèm thông tin để giao diện hiện nút tắt / đổi chỗ."""
    lines: list[dict[str, Any]] = [
        {"line": 1, "tag": "def", "code": f"def {program.name}(problem):", "block": None,
         "unit": False, "locked": True, "disabled": False, "can_up": False, "can_down": False}
    ]

    def emit(stmts: list[Stmt], depth: int, block: str) -> None:
        movable = [s for s in stmts if s.tag not in FIXED_TAGS]
        position = {id(s): i for i, s in enumerate(movable)}
        for st in stmts:
            cur: Stmt | None = st
            is_head = True
            while cur is not None:
                idx = position.get(id(st), -1) if is_head else -1
                lines.append({
                    "line": len(lines) + 1,
                    "tag": cur.tag,
                    "code": "  " * depth + cur.code,
                    "block": block,
                    "unit": idx >= 0,
                    "locked": cur.tag in LOCKED_TAGS,
                    "disabled": cur.tag in disabled,
                    "can_up": idx > 0,
                    "can_down": 0 <= idx < len(movable) - 1,
                })
                if cur.body:
                    emit(cur.body, depth + 1, cur.tag)
                cur = cur.orelse
                is_head = False

    emit(program.body, 1, ROOT_BLOCK)
    return lines
