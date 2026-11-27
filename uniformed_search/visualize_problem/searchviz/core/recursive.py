"""DLS và IDS viết đệ quy đúng như giáo trình (AIMA), có ghi vết từng dòng mã giả.

Khác với BFS / DFS / UCS (vòng ``while`` + frontier), hai thuật toán này không có frontier: ngăn xếp lời gọi hàm
đóng vai trò đó. Vì vậy ở giao diện, ``frontier_ids`` của mỗi bước chính là ngăn xếp lời gọi (từ lời gọi gốc ở đáy
đến lời gọi đang chạy ở đỉnh), ``explored_ids`` là các lời gọi đã trả về xong, và ``frame_limits`` là giá trị
``limit`` còn lại của từng lời gọi.

``graph_search`` = True thêm dòng ``if is_cycle(child): continue`` (chỉ so với các tổ tiên trên đường đi hiện tại,
bản tối ưu); False là đúng mã giả: không kiểm tra gì cả.

Mỗi lần gọi ``recursive_dls`` trả về: nút đích (lời giải), ``CUTOFF`` hoặc ``None`` (failure).
Với IDS, mỗi vòng lặp tìm lại từ gốc nên cùng một nút (cùng đường đi từ gốc) dùng lại cùng một ``id``: cây hiển thị
là cây của vòng sâu nhất, còn ``generated`` / ``expanded`` đếm đủ số lần nút bị sinh / mở lại ở mọi vòng.
"""

from __future__ import annotations

from itertools import count
from typing import Any

from .models import CUTOFF, MAX_TRACE_ELEMENTS, Domain, Node, Problem, is_goal
from .primitives import child_node, solution_node_ids
from .recorder import Recorder, build_result


class _Halt(Exception):
    """Dừng toàn bộ đệ quy khi chạm giới hạn an toàn."""


def recursive_lines(algorithm: str, graph_search: bool) -> list[dict[str, Any]]:
    """Các dòng mã giả hiển thị (chỉ đọc: không tắt / đổi chỗ dòng được)."""
    spec: list[tuple[str, str, int]] = []
    if algorithm == "ids":
        spec += [
            ("def", "def IDS(problem):", 0),
            ("ids_loop", "for depth in count():   # 0, 1, 2, ...", 1),
            ("ids_call", "result = recursive_dls(Node(problem.start_state), problem, depth)", 2),
            ("ids_check", "if result is not cutoff: return result", 2),
        ]
    else:
        spec += [
            ("def", "def DLS(problem, limit):", 0),
            ("dls_call", "return recursive_dls(Node(problem.start_state), problem, limit)", 1),
        ]
    spec += [
        ("rec_def", "def recursive_dls(node, problem, limit):", 0),
        ("check_goal", "if is_goal(node): return solution(node)", 1),
        ("check_limit", "if limit == 0: return cutoff", 1),
        ("init_cutoff", "cutoff_occurred = False", 1),
        ("for_move", "for move in actions(node):", 1),
        ("make_child", "child = child_node(node, move)", 2),
    ]
    if graph_search:
        spec.append(("check_cycle", "if is_cycle(child): continue", 2))
    spec += [
        ("recurse", "result = recursive_dls(child, problem, limit - 1)", 2),
        ("check_cutoff", "if result is cutoff: cutoff_occurred = True", 2),
        ("check_found", "elif result is not failure: return result", 2),
        ("return_end", "return cutoff if cutoff_occurred else failure", 1),
    ]
    return [
        {
            "line": i,
            "tag": tag,
            "code": "  " * indent + code,
            "block": None,
            "unit": False,
            "locked": True,
            "disabled": False,
            "can_up": False,
            "can_down": False,
        }
        for i, (tag, code, indent) in enumerate(spec, start=1)
    ]


class RecursiveSearch:
    def __init__(
        self,
        domain: Domain,
        algorithm: str,
        graph_search: bool,
        depth_limit: int,
        max_nodes: int,
        source_lines: list[dict[str, Any]],
    ) -> None:
        self.domain = domain
        self.algorithm = algorithm
        self.graph_search = graph_search
        self.depth_limit = depth_limit
        self.max_nodes = max_nodes
        self.puzzle = Problem(domain.start_state, domain.goal, domain.get_moves, domain.apply_move, domain.step_cost)

        self.stack: list[tuple[int, int]] = []
        self.keys: dict[tuple[str, ...], int] = {}
        self.key_of: dict[int, tuple[str, ...]] = {}
        self.next_id = 0
        self.iterations = 0
        self.status = "failure"
        self.solution_ids: list[int] | None = None

        tag_to_line = {item["tag"]: item["line"] for item in source_lines}
        self.rec = Recorder(domain, tag_to_line, self.frame_ids)
        self.nodes = self.rec.nodes
        self.steps = self.rec.steps
        self.metrics = self.rec.metrics

    def frame_ids(self) -> list[int]:
        return [nid for nid, _ in self.stack]

    def record(self, event: str, tag: str, message: str, macro: bool, cur_id: int | None, **kw: Any) -> int:
        return self.rec.record_step(
            event_type=event, code_tag=tag, message=message, is_macro=macro, cur_id=cur_id,
            extra={"frame_limits": [limit for _, limit in self.stack]}, **kw,
        )

    def make_node(self, parent: Node | None, move: str | None) -> tuple[Node, bool]:
        key: tuple[str, ...] = () if parent is None else self.key_of[parent.node_id] + (str(move),)
        nid = self.keys.get(key)
        is_new = nid is None
        if nid is None:
            nid = self.next_id
            self.next_id += 1
            self.keys[key] = nid
            self.key_of[nid] = key
        if parent is None:
            node = Node(self.puzzle.start_state, None, None, 0, nid)
        else:
            assert move is not None
            node = child_node(self.puzzle, parent, move, node_id=nid)
        self.metrics["generated"] += 1
        if is_new:
            record = self.rec.register_node(
                node, parent_state=None if parent is None else parent.state, created_step=len(self.steps)
            )
            record["cutoff_step"] = None
        return node, is_new

    @staticmethod
    def find_cycle(child: Node) -> Node | None:
        anc = child.parent
        while anc is not None:
            if anc.state == child.state:
                return anc
            anc = anc.parent
        return None

    def enter(self, node: Node, limit: int, tag: str) -> int:
        m = self.metrics
        if m["expanded"] >= self.max_nodes or self.rec.budget_used > MAX_TRACE_ELEMENTS:
            self.status = "limit_reached"
            reason = (
                f"Chạm giới hạn an toàn {self.max_nodes} nút mở rộng → dừng tìm kiếm."
                if m["expanded"] >= self.max_nodes
                else "Dữ liệu từng bước đã quá lớn để hiển thị → dừng tìm kiếm."
            )
            self.record("limit_reached", tag, reason, True, None, local_vars={"max_nodes": self.max_nodes})
            raise _Halt
        nid = node.node_id
        self.stack.append((nid, limit))
        m["current_depth"] = node.depth
        if node.parent is None:
            msg = f"Gọi recursive_dls(gốc #{nid}, limit = {limit}): khung đầu tiên của ngăn xếp lời gọi."
        else:
            msg = (
                f"Gọi đệ quy recursive_dls(#{nid}, limit - 1 = {limit}): thêm khung mới lên ĐỈNH ngăn xếp "
                f"(đang sâu {len(self.stack)} lời gọi)."
            )
        return self.record(
            "dequeue", tag, msg, True, nid,
            local_vars={"node": f"#{nid}", "limit": limit, "tầng": node.depth, "ngăn xếp": len(self.stack)},
        )

    def leave(self, node: Node) -> None:
        self.stack.pop()
        self.rec.explored_order.append(node.node_id)

    def call(self, node: Node, limit: int, tag: str) -> Node | str | None:
        enter_step = self.enter(node, limit, tag)
        result = self.run_call(node, limit, enter_step)
        self.leave(node)
        return result

    def run_call(self, node: Node, limit: int, enter_step: int) -> Node | str | None:
        cur = node.node_id
        base = {"node": f"#{cur}", "limit": limit}

        if is_goal(self.puzzle, node.state):
            sol = solution_node_ids(node)
            self.status, self.solution_ids = "solved", sol
            step = self.record(
                "goal_late", "check_goal",
                f"#{cur} là ĐÍCH! return solution(node): lời giải {len(sol) - 1} bước.",
                True, cur, solution_ids=sol, local_vars={**base, "is_goal": True},
            )
            if self.nodes[cur]["resolved_step"] is None:
                self.nodes[cur]["resolved_step"] = step
            return node
        self.record(
            "check_late", "check_goal", f"#{cur} chưa phải đích → xét tiếp limit.", False, cur,
            local_vars={**base, "is_goal": False},
        )

        if limit == 0:
            self.nodes[cur]["cutoff_step"] = len(self.steps)
            self.record(
                "cutoff", "check_limit",
                f"limit = 0: hết lượt đi sâu mà #{cur} (tầng {node.depth}) chưa phải đích → return cutoff.",
                False, cur, local_vars={**base, "limit == 0": True},
            )
            return CUTOFF

        self.metrics["expanded"] += 1
        if self.nodes[cur]["expanded_step"] is None:
            self.nodes[cur]["expanded_step"] = enter_step
        self.record(
            "limit_ok", "check_limit",
            f"limit = {limit} > 0 → còn được đi sâu, mở rộng #{cur} (đi tiếp {limit} lớp nữa).",
            False, cur, local_vars={**base, "limit == 0": False},
        )
        self.record(
            "init_cutoff", "init_cutoff", "cutoff_occurred = False: chưa có nhánh con nào bị cắt.", False, cur,
            local_vars={**base, "cutoff_occurred": False},
        )

        cutoff_occurred = False
        moves = self.puzzle.get_moves(node.state)
        for idx, move in enumerate(moves, start=1):
            child, _ = self.make_node(node, move)
            cid = child.node_id
            self.record(
                "gen_child", "make_child",
                f"Thử nước '{move}' ({idx}/{len(moves)}) → sinh nút con #{cid} (tầng {child.depth}).",
                False, cur, candidate_id=cid,
                local_vars={"node": f"#{cur}", "move": move, "child": f"#{cid}", "lượt": f"{idx}/{len(moves)}"},
            )

            if self.graph_search:
                anc = self.find_cycle(child)
                if anc is not None:
                    self.metrics["skipped_explored"] += 1
                    rec = self.nodes[cid]
                    rec["is_duplicate"], rec["duplicate_of"], rec["duplicate_reason"] = True, anc.node_id, "cycle"
                    step = self.record(
                        "skip_cycle", "check_cycle",
                        f"#{cid} cùng trạng thái với tổ tiên #{anc.node_id} (cách {child.depth - anc.depth} bước) "
                        "→ is_cycle = True → bỏ qua (continue).",
                        False, cur, candidate_id=cid, collision_id=anc.node_id,
                        local_vars={"child": f"#{cid}", "is_cycle": True, "tổ tiên": f"#{anc.node_id}"},
                    )
                    if rec["resolved_step"] is None:
                        rec["resolved_step"] = step
                    continue
                self.record(
                    "check_pass", "check_cycle",
                    f"#{cid} không trùng tổ tiên nào trong {child.depth} nút trên đường đi → is_cycle = False.",
                    False, cur, candidate_id=cid, local_vars={"child": f"#{cid}", "is_cycle": False},
                )

            result = self.call(child, limit - 1, "recurse")

            if result is CUTOFF:
                cutoff_occurred = True
                self.record(
                    "got_cutoff", "check_cutoff",
                    f"Lời gọi con #{cid} trả về cutoff → cutoff_occurred = True, thử nước kế tiếp.",
                    False, cur, candidate_id=cid, local_vars={"result": "cutoff", "cutoff_occurred": True},
                )
            elif result is None:
                self.record(
                    "got_failure", "check_found",
                    f"Lời gọi con #{cid} trả về failure → cả hai điều kiện đều sai, thử nước kế tiếp.",
                    False, cur, candidate_id=cid,
                    local_vars={"result": "failure", "cutoff_occurred": cutoff_occurred},
                )
            else:
                self.record(
                    "unwind", "check_found",
                    f"Lời gọi con #{cid} trả về lời giải → return result: thoát khỏi #{cur}, chuyển lời giải lên trên.",
                    False, cur, candidate_id=cid, solution_ids=self.solution_ids, local_vars={"result": "lời giải"},
                )
                return result

        if cutoff_occurred:
            self.record(
                "return_end", "return_end",
                f"Hết các nước đi của #{cur} và có nhánh bị cắt → return cutoff.",
                False, cur, local_vars={**base, "cutoff_occurred": True},
            )
            return CUTOFF
        self.record(
            "return_end", "return_end",
            f"Hết các nước đi của #{cur} và không nhánh nào bị cắt → return failure (dưới nút này chắc chắn không có đích).",
            False, cur, local_vars={**base, "cutoff_occurred": False},
        )
        return None

    def run(self) -> None:
        try:
            if self.algorithm == "dls":
                self.run_dls()
            else:
                self.run_ids()
        except _Halt:
            pass

    def run_dls(self) -> None:
        root, _ = self.make_node(None, None)
        result = self.call(root, self.depth_limit, "dls_call")
        if result is CUTOFF:
            self.status = "cutoff"
            self.record(
                "cutoff_result", "dls_call",
                f"DLS trả về CUTOFF: có nhánh chạm giới hạn l = {self.depth_limit} mà chưa thấy đích. "
                "Chưa kết luận được vô nghiệm, hãy tăng giới hạn (hoặc dùng IDS).",
                True, None, local_vars={"result": "cutoff", "limit": self.depth_limit},
            )
        elif result is None:
            self.status = "failure"
            self.record(
                "failure", "dls_call",
                f"DLS trả về failure: đã duyệt hết cây trong giới hạn l = {self.depth_limit} mà không nhánh nào bị cắt "
                "→ chắc chắn không có lời giải.",
                True, None, local_vars={"result": "failure", "limit": self.depth_limit},
            )

    def run_ids(self) -> None:
        for depth in count():
            self.iterations = depth + 1
            self.rec.explored_order.clear()
            self.record(
                "ids_iter", "ids_loop",
                f"Vòng lặp thứ {depth + 1}: đặt giới hạn depth = {depth}, tìm lại từ gốc và đi sâu tối đa {depth} bước.",
                True, None, local_vars={"depth": depth},
            )
            root, _ = self.make_node(None, None)
            result = self.call(root, depth, "ids_call")
            if result is CUTOFF:
                self.record(
                    "ids_next", "ids_check",
                    f"result = cutoff (còn nhánh bị cắt ở giới hạn {depth}) → chưa kết luận, tăng depth lên {depth + 1}.",
                    False, None, local_vars={"result": "cutoff", "depth": depth},
                )
                continue
            if result is None:
                self.status = "failure"
                self.record(
                    "failure", "ids_check",
                    f"result = failure: ở giới hạn depth = {depth} đã duyệt hết cây mà không nhánh nào bị cắt "
                    "→ chắc chắn không có lời giải.",
                    True, None, local_vars={"result": "failure", "depth": depth},
                )
                return
            assert self.solution_ids is not None
            self.record(
                "ids_done", "ids_check",
                f"result là lời giải → IDS return result: lời giải {len(self.solution_ids) - 1} bước, "
                f"tìm ra ở vòng giới hạn depth = {depth}.",
                True, None, solution_ids=self.solution_ids,
                local_vars={"result": "lời giải", "depth": depth},
            )
            return


def recursive_trace(
    domain: Domain,
    *,
    algorithm: str,
    graph_search: bool,
    depth_limit: int,
    max_nodes: int,
) -> dict[str, Any]:
    source_lines = recursive_lines(algorithm, graph_search)
    search = RecursiveSearch(domain, algorithm, graph_search, depth_limit, max_nodes, source_lines)
    search.run()
    return build_result(
        domain=domain,
        algorithm=algorithm,
        status=search.status,
        graph_search=graph_search,
        early_goal_test=False,
        max_nodes=max_nodes,
        source_lines=source_lines,
        nodes=search.nodes,
        steps=search.steps,
        solution_ids=search.solution_ids,
        extra={
            "recursive": True,
            "depth_limit": depth_limit if algorithm == "dls" else None,
            "iterations": search.iterations if algorithm == "ids" else None,
        },
    )
