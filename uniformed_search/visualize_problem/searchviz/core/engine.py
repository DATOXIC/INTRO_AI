"""Trình thực thi chương trình tìm kiếm: chạy cây lệnh của ``program.py`` và ghi lại từng dòng đã chạy.

Mỗi tag (dòng mã giả) có một hàm xử lý ``h_<tag>``. Nhờ vậy cùng một bộ máy chạy được BFS, DFS, UCS và UCS tối ưu,
và chạy đúng cả khi người dùng tắt một dòng hay đổi chỗ các dòng: dòng nào dùng biến chưa được tạo sẽ cho ra
một lỗi chương trình dễ hiểu (ProgramError), còn vòng lặp vô hạn bị chặn bởi giới hạn an toàn.
"""

from __future__ import annotations

import bisect
from itertools import count
from typing import Any

from .models import MAX_TRACE_ELEMENTS, Domain, Node, Problem, is_goal
from .primitives import child_node, solution_node_ids
from .program import Program, Stmt
from .pseudocode import _vocabulary
from .recorder import Recorder

# Tín hiệu điều khiển luồng trả về từ mỗi lệnh
NEXT, CONT_FOR, CONT_WHILE, DONE = range(4)

# Biến -> dòng tạo ra nó, dùng để giải thích lỗi "dùng biến chưa tạo"
DEFINERS = {
    "frontier": "init_queue",
    "explored": "init_explored",
    "best_cost": "init_best",
    "root": "init_root",
    "cur_node": "dequeue",
    "child": "make_child",
}

FAMILY = {"bfs": "fifo", "dfs": "lifo", "ucs": "slide", "ucs_fast": "fast"}


class ProgramError(Exception):
    """Chương trình đã bị chỉnh sửa tới mức không chạy được (ví dụ dùng biến trước khi tạo)."""

    def __init__(self, tag: str, message: str) -> None:
        super().__init__(message)
        self.tag = tag
        self.message = message


class Engine:
    def __init__(
        self,
        domain: Domain,
        program: Program,
        source_lines: list[dict[str, Any]],
        disabled: frozenset[str],
        *,
        max_nodes: int,
    ) -> None:
        self.domain = domain
        self.program = program
        self.disabled = disabled
        self.max_nodes = max_nodes
        self.fam = FAMILY[program.algorithm]
        self.pq = self.fam in ("slide", "fast")
        self.words = _vocabulary(program.algorithm)
        self.puzzle = Problem(domain.start_state, domain.goal, domain.get_moves, domain.apply_move, domain.step_cost)

        self.source_lines = source_lines
        self.line_info = {item["tag"]: item for item in source_lines}
        tags = {item["tag"] for item in source_lines}
        # UCS tối ưu đếm "đã mở rộng" ở dòng check_stale (nút cũ không tính); không có dòng đó thì đếm ngay khi pop
        self.counts_in_dequeue = not (self.fam == "fast" and "check_stale" in tags and "check_stale" not in disabled)

        self.frontier: list[Any] | None = None  # Node (FIFO/LIFO) hoặc (g, thứ tự vào, Node) (hàng đợi ưu tiên)
        self.explored_map: dict[Any, int] | None = None
        self.frontier_map: dict[Any, int] = {}  # BFS/DFS: trạng thái -> nút đang chờ trong frontier
        self.in_frontier: dict[Any, tuple[int, int, Node]] = {}  # UCS slide: trạng thái -> mục trong frontier
        self.best_cost: dict[Any, int] | None = None
        self.best_node: dict[Any, int] = {}
        self.arrival = count()
        self.next_id = 0
        self.defined: set[str] = set()

        self.root: Node | None = None
        self.cur: Node | None = None
        self.cand: Node | None = None
        self.move = ""
        self.move_idx = 0
        self.moves: list[str] = []
        self.dup_entry: tuple[int, int, Node] | None = None
        self.dequeue_step = 0

        self.status = "failure"
        self.solution_ids: list[int] | None = None
        self.error: dict[str, Any] | None = None

        tag_to_line = {item["tag"]: item["line"] for item in source_lines}
        self.rec = Recorder(domain, tag_to_line, self.f_ids)
        self.nodes = self.rec.nodes
        self.steps = self.rec.steps
        self.metrics = self.rec.metrics

    # ── tiện ích ───────────────────────────────────────────────────────────
    def f_ids(self) -> list[int]:
        if self.frontier is None:
            return []
        if self.pq:
            return [entry[2].node_id for entry in self.frontier]
        return [n.node_id for n in self.frontier]

    def record(self, event: str, tag: str, message: str, macro: bool, cur_id: int | None, **kw: Any) -> int:
        return self.rec.record_step(
            event_type=event, code_tag=tag, message=message, is_macro=macro, cur_id=cur_id, **kw
        )

    def need(self, name: str, st: Stmt) -> None:
        """Báo lỗi dễ hiểu nếu dòng ``st`` dùng biến ``name`` mà biến đó chưa được tạo."""
        if name in self.defined:
            return
        here = self.line_info.get(st.tag, {"line": 0, "code": st.code}).copy()
        definer = DEFINERS[name]
        where = self.line_info.get(definer)
        if where is None:
            reason = "thuật toán này không có dòng nào tạo ra nó"
        elif definer in self.disabled:
            reason = f"dòng {where['line']} (`{where['code'].strip()}`) tạo ra nó đã bị TẮT"
        else:
            reason = f"dòng {where['line']} (`{where['code'].strip()}`) tạo ra nó chưa chạy trước dòng này"
        raise ProgramError(
            st.tag,
            f"Dòng {here['line']} (`{here['code'].strip()}`) cần `{name}` nhưng `{name}` chưa tồn tại: {reason}.",
        )

    def put(self, node: Node) -> tuple[int, int, Node]:
        entry = (node.path_cost, next(self.arrival), node)
        bisect.insort(self.frontier, entry)  # type: ignore[arg-type]
        return entry

    def mark_expanded(self, cur: Node) -> None:
        self.metrics["expanded"] += 1
        self.metrics["current_depth"] = cur.depth

    def mark_duplicate(self, cand_id: int, of: int | None, reason: str) -> None:
        rec = self.nodes[cand_id]
        rec["is_duplicate"] = True
        rec["duplicate_of"] = of
        rec["duplicate_reason"] = reason

    # ── điều khiển luồng ───────────────────────────────────────────────────
    def run(self) -> None:
        try:
            self.run_block(self.program.body)
        except ProgramError as exc:
            self.status = "program_error"
            line = self.line_info.get(exc.tag, {}).get("line", 1)
            self.error = {"tag": exc.tag, "line": line, "message": exc.message}
            self.record("program_error", exc.tag, exc.message, True, None)

    def run_block(self, stmts: list[Stmt]) -> int:
        for st in stmts:
            signal = self.exec_stmt(st)
            if signal != NEXT:
                return signal
        return NEXT

    def exec_stmt(self, st: Stmt) -> int:
        if st.kind == "while":
            return self.exec_while(st)
        if st.kind == "for":
            return self.exec_for(st)
        if st.kind == "if":
            return self.exec_if(st)
        if st.tag in self.disabled:
            return NEXT
        return getattr(self, f"h_{st.tag}")(st)

    def exec_if(self, st: Stmt) -> int:
        cur: Stmt | None = st
        while cur is not None:
            outcome = "taken" if cur.tag in self.disabled else getattr(self, f"c_{cur.tag}")(cur)
            if outcome == "taken":
                return self.run_block(cur.body)
            if outcome == "skip":
                return NEXT
            cur = cur.orelse  # "next": thử nhánh elif
        return NEXT

    def exec_while(self, st: Stmt) -> int:
        self.need("frontier", st)
        assert self.frontier is not None
        while self.frontier:
            m = self.metrics
            if m["expanded"] >= self.max_nodes or self.rec.budget_used > MAX_TRACE_ELEMENTS:
                self.status = "limit_reached"
                reason = (
                    f"Chạm giới hạn an toàn {self.max_nodes} nút mở rộng → dừng tìm kiếm."
                    if m["expanded"] >= self.max_nodes
                    else "Dữ liệu từng bước đã quá lớn để hiển thị → dừng tìm kiếm."
                )
                self.record(
                    "limit_reached", st.tag, reason, True, None,
                    local_vars={"max_nodes": self.max_nodes, "frontier_len": len(self.frontier)},
                )
                return DONE
            if self.run_block(st.body) == DONE:
                return DONE
        return NEXT

    def exec_for(self, st: Stmt) -> int:
        self.need("cur_node", st)
        assert self.cur is not None
        self.moves = self.puzzle.get_moves(self.cur.state)
        for idx, move in enumerate(self.moves, start=1):
            self.move, self.move_idx = move, idx
            signal = self.run_block(st.body)
            if signal in (DONE, CONT_WHILE):
                return signal
        return NEXT

    # ── dòng khởi tạo ──────────────────────────────────────────────────────
    def h_init_root(self, st: Stmt) -> int:
        nid = self.next_id
        self.next_id += 1
        root = Node(self.puzzle.start_state, parent=None, action=None, depth=0, node_id=nid)
        self.root = root
        self.defined.add("root")
        self.metrics["generated"] += 1
        self.rec.register_node(root, parent_state=None, created_step=len(self.steps))
        if self.pq:
            msg, lv = f"Tạo nút gốc #{nid} với chi phí g = 0.", {"root": f"#{nid}", "g": 0}
        else:
            msg, lv = f"Tạo nút gốc #{nid} từ trạng thái xuất phát.", {"root": f"#{nid}", "depth": 0}
        self.record("init_root", st.tag, msg, True, nid, local_vars=lv)
        return NEXT

    def h_check_root_goal(self, st: Stmt) -> int:
        self.need("root", st)
        root = self.root
        assert root is not None
        rid = root.node_id
        if is_goal(self.puzzle, root.state):
            sol = solution_node_ids(root)
            self.record(
                "goal_init", st.tag, f"Nút gốc #{rid} đã là ĐÍCH (0 bước)!", True, rid,
                solution_ids=sol, local_vars={"root": f"#{rid}", "is_goal": True},
            )
            self.status, self.solution_ids = "solved", sol
            return DONE
        self.record(
            "check_root", st.tag, "Gốc chưa phải đích → tiếp tục.", False, rid,
            local_vars={"root": f"#{rid}", "is_goal": False},
        )
        return NEXT

    def h_init_queue(self, st: Stmt) -> int:
        self.need("root", st)
        root = self.root
        assert root is not None
        self.frontier = []
        self.defined.add("frontier")
        if self.pq:
            entry = self.put(root)
            if self.fam == "slide":
                self.in_frontier[root.state] = entry
            msg = f"Tạo hàng đợi ưu tiên frontier (xếp theo g) và đưa nút gốc #{root.node_id} vào."
        else:
            self.frontier.append(root)
            self.frontier_map[root.state] = root.node_id
            msg = f"Tạo {self.words['container']} frontier và đưa nút gốc #{root.node_id} vào."
        step = self.record(
            "init", st.tag, msg, True, root.node_id, candidate_id=root.node_id,
            local_vars={"root": f"#{root.node_id}", "frontier_len": len(self.frontier)},
        )
        self.nodes[root.node_id]["resolved_step"] = step
        return NEXT

    def h_init_best(self, st: Stmt) -> int:
        self.need("root", st)
        root = self.root
        assert root is not None
        self.best_cost = {root.state: 0}
        self.best_node = {root.state: root.node_id}
        self.defined.add("best_cost")
        self.record(
            "init_best", st.tag,
            "Tạo best_cost: ghi nhớ g nhỏ nhất đã tìm thấy cho mỗi trạng thái (mới có gốc: g = 0).",
            False, None, local_vars={"best_cost": 1},
        )
        return NEXT

    def h_init_explored(self, st: Stmt) -> int:
        self.explored_map = {}
        self.defined.add("explored")
        self.record(
            "init_explored", st.tag, "Tạo tập explored rỗng.", False, None,
            local_vars={"frontier_len": len(self.frontier or []), "explored_len": 0},
        )
        return NEXT

    # ── thân vòng while ────────────────────────────────────────────────────
    def h_dequeue(self, st: Stmt) -> int:
        self.need("frontier", st)
        frontier = self.frontier
        assert frontier is not None
        if not frontier:
            raise ProgramError(st.tag, "Frontier đã rỗng nhưng dòng này vẫn cố lấy một nút ra.")
        if self.pq:
            cur = frontier.pop(0)[2]
            if self.fam == "slide":
                self.in_frontier.pop(cur.state, None)
        else:
            cur = frontier.pop() if self.fam == "lifo" else frontier.pop(0)
            if self.frontier_map.get(cur.state) == cur.node_id:
                del self.frontier_map[cur.state]
        self.cur = cur
        self.defined.add("cur_node")
        if self.counts_in_dequeue:
            self.mark_expanded(cur)
        if self.pq:
            msg = f"Pop nút #{cur.node_id} (g = {cur.path_cost}) — nút có g nhỏ nhất trong frontier → thành cur_node."
            lv = {"cur_node": f"#{cur.node_id}", "g": cur.path_cost, "frontier_len": len(frontier)}
        else:
            msg = f"Pop nút #{cur.node_id} (tầng {cur.depth}) khỏi {self.words['out_where']} → thành cur_node."
            lv = {"cur_node": f"#{cur.node_id}", "depth": cur.depth, "frontier_len": len(frontier)}
        self.dequeue_step = self.record("dequeue", st.tag, msg, True, cur.node_id, local_vars=lv)
        if self.counts_in_dequeue:
            self.nodes[cur.node_id]["expanded_step"] = self.dequeue_step
        return NEXT

    def h_check_stale(self, st: Stmt) -> int:
        self.need("cur_node", st)
        self.need("explored", st)
        cur, explored = self.cur, self.explored_map
        assert cur is not None and explored is not None
        if cur.state in explored:
            self.metrics["skipped_stale"] += 1
            step = self.record(
                "skip_stale", st.tag,
                f"#{cur.node_id} là nút CŨ: trạng thái này đã được mở rộng với đường rẻ hơn "
                f"(#{explored[cur.state]}) → bỏ qua (continue).",
                True, cur.node_id, collision_id=explored[cur.state],
                local_vars={"cur_node": f"#{cur.node_id}", "g": cur.path_cost, "in_explored": True},
            )
            self.nodes[cur.node_id]["discarded_step"] = step
            return CONT_WHILE
        self.mark_expanded(cur)
        self.record(
            "check_stale", st.tag,
            f"#{cur.node_id} chưa nằm trong explored → không phải nút cũ, tiếp tục mở rộng.",
            False, cur.node_id, local_vars={"cur_node": f"#{cur.node_id}", "in_explored": False},
        )
        self.nodes[cur.node_id]["expanded_step"] = self.dequeue_step
        return NEXT

    def h_check_late_goal(self, st: Stmt) -> int:
        self.need("cur_node", st)
        cur = self.cur
        assert cur is not None
        base = {"cur_node": f"#{cur.node_id}"}
        if self.pq:
            base["g"] = cur.path_cost
        if is_goal(self.puzzle, cur.state):
            sol = solution_node_ids(cur)
            tail = f", chi phí g = {cur.path_cost} (rẻ nhất)." if self.pq else "."
            self.record(
                "goal_late", st.tag, f"#{cur.node_id} là ĐÍCH! Lời giải {len(sol) - 1} bước{tail}",
                True, cur.node_id, solution_ids=sol, local_vars={**base, "is_goal": True},
            )
            self.status, self.solution_ids = "solved", sol
            return DONE
        self.record(
            "check_late", st.tag, f"#{cur.node_id} chưa phải đích → tiếp tục.", False, cur.node_id,
            local_vars={**base, "is_goal": False},
        )
        return NEXT

    def h_add_explored(self, st: Stmt) -> int:
        self.need("explored", st)
        self.need("cur_node", st)
        cur, explored = self.cur, self.explored_map
        assert cur is not None and explored is not None
        if cur.state not in explored:
            explored[cur.state] = cur.node_id
            self.rec.explored_order.append(cur.node_id)
        self.record(
            "explore", st.tag, f"Ghi #{cur.node_id} vào explored (tổng {len(self.rec.explored_order)}).",
            False, cur.node_id,
            local_vars={"cur_node": f"#{cur.node_id}", "explored_len": len(self.rec.explored_order)},
        )
        return NEXT

    # ── thân vòng for ──────────────────────────────────────────────────────
    def h_make_child(self, st: Stmt) -> int:
        self.need("cur_node", st)
        cur = self.cur
        assert cur is not None
        cand_id = self.next_id
        self.next_id += 1
        cand = child_node(self.puzzle, cur, self.move, node_id=cand_id)
        self.cand = cand
        self.defined.add("child")
        self.dup_entry = None
        self.metrics["generated"] += 1
        self.rec.register_node(cand, parent_state=cur.state, created_step=len(self.steps))
        n, idx, move = len(self.moves), self.move_idx, self.move
        if self.pq:
            cost = cand.path_cost - cur.path_cost
            msg = (
                f"Thử nước '{move}' ({idx}/{n}, tốn {cost}) → sinh nút con #{cand_id} "
                f"với g = {cur.path_cost} + {cost} = {cand.path_cost}."
            )
            lv = {
                "cur_node": f"#{cur.node_id}", "move": move, "child": f"#{cand_id}",
                "g(child)": f"{cur.path_cost}+{cost}={cand.path_cost}",
            }
        else:
            msg = f"Thử nước '{move}' ({idx}/{n}) → sinh nút con #{cand_id} (tầng {cand.depth})."
            lv = {"cur_node": f"#{cur.node_id}", "move": move, "child": f"#{cand_id}", "lượt": f"{idx}/{n}"}
        self.record("gen_child", st.tag, msg, False, cur.node_id, candidate_id=cand_id, local_vars=lv)
        return NEXT

    def _skip_explored(self, st: Stmt, cur: Node, cand: Node, holder: int, local_vars: dict[str, Any], msg: str) -> None:
        self.metrics["skipped_explored"] += 1
        self.mark_duplicate(cand.node_id, holder, "explored")
        step = self.record(
            "skip_explored", st.tag, msg, False, cur.node_id,
            candidate_id=cand.node_id, collision_id=holder, local_vars=local_vars,
        )
        self.nodes[cand.node_id]["resolved_step"] = step

    # c_<tag>: điều kiện của dòng if/elif, trả về "taken" | "skip" | "next"
    def c_check_duplicate(self, st: Stmt) -> str:
        self.need("child", st)
        self.need("explored", st)
        self.need("frontier", st)
        cur, cand, explored = self.cur, self.cand, self.explored_map
        assert cur is not None and cand is not None and explored is not None
        cid = cand.node_id
        in_explored = cand.state in explored

        if self.fam == "slide":
            if in_explored:
                holder = explored[cand.state]
                self._skip_explored(
                    st, cur, cand, holder, {"child": f"#{cid}", "in_explored": True},
                    f"#{cid} trùng #{holder} đã có trong explored → bỏ qua.",
                )
                return "skip"
            old_entry = self.in_frontier.get(cand.state)
            if old_entry is None:
                self.record(
                    "check_pass", st.tag, f"#{cid} chưa có trong explored và frontier → là trạng thái mới.",
                    False, cur.node_id, candidate_id=cid,
                    local_vars={"child": f"#{cid}", "in_explored": False, "in_frontier": False},
                )
                return "taken"
            self.dup_entry = old_entry
            old = old_entry[2]
            self.record(
                "dup_frontier", st.tag,
                f"#{cid} cùng trạng thái với #{old.node_id} đang chờ trong frontier (g = {old.path_cost}) "
                "→ không vào nhánh if, xét tiếp nhánh elif: đường nào rẻ hơn?",
                False, cur.node_id, candidate_id=cid, collision_id=old.node_id,
                local_vars={"child": f"#{cid}", "in_frontier": True, "collision": f"#{old.node_id}"},
            )
            return "next"

        # BFS / DFS (Graph Search)
        in_frontier = (not in_explored) and (cand.state in self.frontier_map)
        if in_explored or in_frontier:
            holder = explored[cand.state] if in_explored else self.frontier_map[cand.state]
            where = "explored" if in_explored else "frontier"
            self.metrics["skipped_explored" if in_explored else "skipped_frontier"] += 1
            self.mark_duplicate(cid, holder, where)
            step = self.record(
                "skip_explored" if in_explored else "skip_frontier", st.tag,
                f"#{cid} trùng #{holder} "
                f"{'đã có trong explored' if in_explored else 'đang chờ trong frontier'} → bỏ qua.",
                False, cur.node_id, candidate_id=cid, collision_id=holder,
                local_vars={
                    "child": f"#{cid}", "in_explored": in_explored, "in_frontier": in_frontier,
                    "collision": f"#{holder} ({where})",
                },
            )
            self.nodes[cid]["resolved_step"] = step
            return "skip"
        self.record(
            "check_pass", st.tag, f"#{cid} chưa có trong explored và frontier → là trạng thái mới.",
            False, cur.node_id, candidate_id=cid,
            local_vars={"child": f"#{cid}", "in_explored": False, "in_frontier": False},
        )
        return "taken"

    def c_check_better(self, st: Stmt) -> str:  # elif của UCS slide
        self.need("child", st)
        self.need("frontier", st)
        cur, cand, old_entry = self.cur, self.cand, self.dup_entry
        assert cur is not None and cand is not None
        if old_entry is None:
            raise ProgramError(st.tag, "Dòng elif này chỉ chạy khi nút con trùng một nút đang chờ trong frontier.")
        old, cid = old_entry[2], cand.node_id
        if cand.path_cost >= old.path_cost:
            self.metrics["skipped_frontier"] += 1
            self.mark_duplicate(cid, old.node_id, "frontier")
            step = self.record(
                "not_better", st.tag,
                f"g mới = {cand.path_cost} không thấp hơn g cũ = {old.path_cost} → giữ nút cũ, bỏ qua nút con.",
                False, cur.node_id, candidate_id=cid, collision_id=old.node_id,
                local_vars={"g(child)": cand.path_cost, "g(cũ)": old.path_cost},
            )
            self.nodes[cid]["resolved_step"] = step
            return "skip"
        self.record(
            "better", st.tag,
            f"g mới = {cand.path_cost} < g cũ = {old.path_cost} → tìm được đường RẺ HƠN, cần thay nút cũ.",
            False, cur.node_id, candidate_id=cid, collision_id=old.node_id,
            local_vars={"g(child)": cand.path_cost, "g(cũ)": old.path_cost},
        )
        return "taken"

    def c_check_best(self, st: Stmt) -> str:  # UCS tối ưu
        self.need("child", st)
        self.need("best_cost", st)
        cur, cand, best = self.cur, self.cand, self.best_cost
        assert cur is not None and cand is not None and best is not None
        cid = cand.node_id
        prev = best.get(cand.state)
        if prev is not None and cand.path_cost >= prev:
            holder = self.best_node.get(cand.state)
            self.mark_duplicate(cid, holder, "frontier")
            self.metrics["skipped_frontier"] += 1
            step = self.record(
                "not_better", st.tag,
                f"g = {cand.path_cost} không thấp hơn best_cost = {prev} (đã có #{holder}) → bỏ qua nút con.",
                False, cur.node_id, candidate_id=cid, collision_id=holder,
                local_vars={"child": f"#{cid}", "g(child)": cand.path_cost, "best_cost": prev},
            )
            self.nodes[cid]["resolved_step"] = step
            return "skip"
        self.record(
            "better", st.tag,
            "Trạng thái này chưa có trong best_cost → là đường đầu tiên tới nó."
            if prev is None
            else f"g = {cand.path_cost} < best_cost = {prev} → tìm được đường RẺ HƠN.",
            False, cur.node_id, candidate_id=cid, collision_id=self.best_node.get(cand.state),
            local_vars={
                "child": f"#{cid}", "g(child)": cand.path_cost, "best_cost": "chưa có" if prev is None else prev,
            },
        )
        return "taken"

    def h_check_explored_child(self, st: Stmt) -> int:  # UCS tối ưu: if child.state in explored: continue
        self.need("child", st)
        self.need("explored", st)
        cur, cand, explored = self.cur, self.cand, self.explored_map
        assert cur is not None and cand is not None and explored is not None
        cid = cand.node_id
        if cand.state in explored:
            holder = explored[cand.state]
            self._skip_explored(
                st, cur, cand, holder, {"child": f"#{cid}", "in_explored": True},
                f"#{cid} trùng #{holder} đã có trong explored → bỏ qua.",
            )
            return CONT_FOR
        self.record(
            "check_pass", st.tag, f"#{cid} chưa có trong explored.", False, cur.node_id, candidate_id=cid,
            local_vars={"child": f"#{cid}", "in_explored": False},
        )
        return NEXT

    def h_check_early_goal(self, st: Stmt) -> int:
        self.need("child", st)
        cur, cand = self.cur, self.cand
        assert cur is not None and cand is not None
        cid = cand.node_id
        if is_goal(self.puzzle, cand.state):
            sol = solution_node_ids(cand)
            step = self.record(
                "goal_early", st.tag, f"#{cid} là ĐÍCH! Lời giải {len(sol) - 1} bước.", True, cur.node_id,
                candidate_id=cid, solution_ids=sol,
                local_vars={"cur_node": f"#{cur.node_id}", "move": self.move, "child": f"#{cid}", "is_goal": True},
            )
            self.nodes[cid]["resolved_step"] = step
            self.status, self.solution_ids = "solved", sol
            return DONE
        self.record(
            "check_goal", st.tag, f"#{cid} chưa phải đích.", False, cur.node_id, candidate_id=cid,
            local_vars={"child": f"#{cid}", "is_goal": False},
        )
        return NEXT

    def h_update_best(self, st: Stmt) -> int:
        self.need("child", st)
        self.need("best_cost", st)
        cur, cand, best = self.cur, self.cand, self.best_cost
        assert cur is not None and cand is not None and best is not None
        best[cand.state] = cand.path_cost
        self.record(
            "update_best", st.tag, f"Ghi best_cost[trạng thái của #{cand.node_id}] = {cand.path_cost}.",
            False, cur.node_id, candidate_id=cand.node_id,
            local_vars={"child": f"#{cand.node_id}", "best_cost": cand.path_cost},
        )
        return NEXT

    def h_enqueue_child(self, st: Stmt) -> int:
        self.need("child", st)
        self.need("frontier", st)
        cur, cand, frontier = self.cur, self.cand, self.frontier
        assert cur is not None and cand is not None and frontier is not None
        cid = cand.node_id

        if self.fam == "fast":
            old_id = self.best_node.get(cand.state)
            self.best_node[cand.state] = cid
            self.put(cand)
            note = f" Nút #{old_id} trở thành nút CŨ (sẽ bị bỏ qua khi pop)." if old_id is not None else ""
            step = self.record(
                "enqueue", st.tag, f"Thêm #{cid} vào frontier đúng vị trí theo g = {cand.path_cost}.{note}",
                False, cur.node_id, candidate_id=cid, collision_id=old_id,
                local_vars={"child": f"#{cid}", "g(child)": cand.path_cost, "frontier_len": len(frontier)},
            )
            self.nodes[cid]["resolved_step"] = step
            if old_id is not None:
                self.metrics["replaced"] += 1
                self.nodes[old_id]["superseded_by"] = cid
                self.nodes[old_id]["superseded_step"] = step
                self.nodes[cid]["replaces"] = old_id
            return NEXT

        if self.fam == "slide":
            self.in_frontier[cand.state] = self.put(cand)
            step = self.record(
                "enqueue", st.tag, f"Thêm #{cid} vào frontier đúng vị trí theo g = {cand.path_cost}.",
                False, cur.node_id, candidate_id=cid,
                local_vars={"child": f"#{cid}", "g(child)": cand.path_cost, "frontier_len": len(frontier)},
            )
        else:
            frontier.append(cand)
            if cand.state not in self.frontier_map:
                self.frontier_map[cand.state] = cid
            step = self.record(
                "enqueue", st.tag, f"{self.words['in_verb']} #{cid} {self.words['in_where']}.",
                False, cur.node_id, candidate_id=cid,
                local_vars={
                    "cur_node": f"#{cur.node_id}", "move": self.move, "child": f"#{cid}",
                    "frontier_len": len(frontier),
                },
            )
        self.nodes[cid]["resolved_step"] = step
        return NEXT

    def h_replace_child(self, st: Stmt) -> int:
        self.need("child", st)
        self.need("frontier", st)
        cur, cand, frontier, entry = self.cur, self.cand, self.frontier, self.dup_entry
        assert cur is not None and cand is not None and frontier is not None
        if entry is None:
            raise ProgramError(st.tag, "Dòng này thay một nút đang chờ trong frontier, nhưng chưa có nút nào để thay.")
        old, cid = entry[2], cand.node_id
        if entry in frontier:
            frontier.remove(entry)
        self.in_frontier[cand.state] = self.put(cand)
        self.metrics["replaced"] += 1
        step = self.record(
            "replace", st.tag,
            f"Thay #{old.node_id} (g = {old.path_cost}) bằng #{cid} (g = {cand.path_cost}) trong frontier.",
            False, cur.node_id, candidate_id=cid, collision_id=old.node_id,
            local_vars={"child": f"#{cid}", "g(child)": cand.path_cost, "frontier_len": len(frontier)},
        )
        self.nodes[old.node_id]["superseded_by"] = cid
        self.nodes[old.node_id]["superseded_step"] = step
        self.nodes[cid]["replaces"] = old.node_id
        self.nodes[cid]["resolved_step"] = step
        return NEXT

    # ── kết thúc ───────────────────────────────────────────────────────────
    def h_return_none(self, st: Stmt) -> int:
        self.record(
            "failure", st.tag, "Frontier rỗng mà chưa thấy đích → không có lời giải.", True, None,
            local_vars={"frontier_len": 0, "explored_len": len(self.rec.explored_order)},
        )
        return DONE
