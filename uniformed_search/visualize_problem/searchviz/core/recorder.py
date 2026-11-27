"""Ghi lại từng nút và từng bước của một lần chạy, rồi gói thành kết quả JSON cho giao diện."""

from __future__ import annotations

from typing import Any, Callable

from .models import Domain, Node


class Recorder:
    """Ghi lại từng nút và từng bước của một lần chạy (dùng chung cho BFS/DFS và UCS)."""

    def __init__(
        self,
        domain: Domain,
        tag_to_line: dict[str, int],
        frontier_ids: Callable[[], list[int]],
    ) -> None:
        self.domain = domain
        self.tag_to_line = tag_to_line
        self.frontier_ids = frontier_ids
        self.nodes: list[dict[str, Any]] = []
        self.steps: list[dict[str, Any]] = []
        self.explored_order: list[int] = []
        self.macro_counter = 0
        self.budget_used = 0
        self.metrics: dict[str, int] = {
            "expanded": 0,
            "generated": 0,
            "skipped_explored": 0,
            "skipped_frontier": 0,
            "skipped_stale": 0,
            "replaced": 0,
            "max_frontier_size": 0,
            "current_depth": 0,
        }

    def register_node(
        self,
        node: Node,
        parent_state: Any,
        created_step: int,
        *,
        is_duplicate: bool = False,
        duplicate_of: int | None = None,
        duplicate_reason: str | None = None,
    ) -> dict[str, Any]:
        domain = self.domain
        parent_cost = node.parent.path_cost if node.parent is not None else 0
        rec = {
            "id": node.node_id,
            "state": domain.state_to_json(node.state),
            "parent_id": node.parent.node_id if node.parent is not None else None,
            "action": node.action,
            "depth": node.depth,
            "path_cost": node.path_cost,
            "step_cost": node.path_cost - parent_cost,
            "actions": list(domain.get_moves(node.state)),
            **domain.node_extras(node.state, parent_state, node.action),
            "is_duplicate": is_duplicate,
            "duplicate_of": duplicate_of,
            "duplicate_reason": duplicate_reason,
            "created_step": created_step,
            "resolved_step": None,
            "expanded_step": None,
            "replaces": None,
            "superseded_by": None,
            "superseded_step": None,
            "discarded_step": None,
        }
        self.nodes.append(rec)
        return rec

    def record_step(
        self,
        *,
        event_type: str,
        code_tag: str,
        message: str,
        is_macro: bool,
        cur_id: int | None,
        candidate_id: int | None = None,
        collision_id: int | None = None,
        solution_ids: list[int] | None = None,
        local_vars: dict[str, Any] | None = None,
    ) -> int:
        if is_macro:
            self.macro_counter += 1
        step_idx = len(self.steps)
        frontier_ids = self.frontier_ids()
        self.metrics["max_frontier_size"] = max(self.metrics["max_frontier_size"], len(frontier_ids))
        self.budget_used += len(frontier_ids) + len(self.explored_order) + 1
        self.steps.append(
            {
                "index": step_idx,
                "macro_index": self.macro_counter,
                "is_macro": is_macro,
                "event_type": event_type,
                "code_tag": code_tag,
                "line": self.tag_to_line.get(code_tag, 1),
                "cur_id": cur_id,
                "candidate_id": candidate_id,
                "collision_id": collision_id,
                "frontier_ids": frontier_ids,
                "explored_ids": list(self.explored_order),
                "solution_ids": solution_ids,
                "vars": local_vars or {},
                "message": message,
                "metrics": {
                    **self.metrics,
                    "frontier_size": len(frontier_ids),
                    "explored_size": len(self.explored_order),
                },
            }
        )
        return step_idx


def build_result(
    *,
    domain: Domain,
    algorithm: str,
    status: str,
    graph_search: bool,
    early_goal_test: bool,
    max_nodes: int,
    source_lines: list[dict[str, Any]],
    nodes: list[dict[str, Any]],
    steps: list[dict[str, Any]],
    solution_ids: list[int] | None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    last_metrics = steps[-1]["metrics"] if steps else {}
    expanded = last_metrics.get("expanded", 0)
    generated = last_metrics.get("generated", 0)
    avg_branching = round((generated - 1) / expanded, 2) if expanded > 0 else 0.0

    result = {
        "status": status,
        "problem": domain.kind,
        "algorithm": algorithm,
        "goal_description": domain.goal_description,
        "start_state": domain.state_to_json(domain.start_state),
        **domain.result_fields,
        "move_costs": domain.move_costs,
        "config": {
            "graph_search": graph_search,
            "early_goal_test": early_goal_test,
            "max_nodes": max_nodes,
        },
        "solvability": domain.solvability,
        "source_lines": source_lines,
        "nodes": nodes,
        "steps": steps,
        "solution_ids": solution_ids,
        "summary": {
            "total_steps": len(steps),
            "total_macros": steps[-1]["macro_index"] if steps else 0,
            "solution_length": (len(solution_ids) - 1) if solution_ids is not None else None,
            "nodes_expanded": expanded,
            "nodes_generated": generated,
            "skipped_explored": last_metrics.get("skipped_explored", 0),
            "skipped_frontier": last_metrics.get("skipped_frontier", 0),
            "skipped_stale": last_metrics.get("skipped_stale", 0),
            "replaced": last_metrics.get("replaced", 0),
            "solution_cost": nodes[solution_ids[-1]]["path_cost"] if solution_ids else None,
            "max_frontier_size": last_metrics.get("max_frontier_size", 0),
            "avg_branching_factor": avg_branching,
        },
    }
    if extra:
        result.update(extra)
    return result
