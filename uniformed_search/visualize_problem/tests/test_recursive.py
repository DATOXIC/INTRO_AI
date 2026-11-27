"""DLS và IDS đệ quy: ghi vết phải khớp bản chạy thuần (cùng kết quả, cùng lời giải) và ngăn xếp lời gọi phải nhất quán."""

from __future__ import annotations

import unittest
from typing import Any

from searchviz.core import CUTOFF, DLS, IDS, Problem, search_trace
from searchviz.problems import get_presets
from searchviz.problems.npuzzle import make_goal_board, make_npuzzle_domain, shuffle_solvable, validate_board
from searchviz.problems.vacuum import make_vacuum_domain, validate_vacuum_state
from searchviz.web.api import handle

BIG = 3000


def domains() -> list[tuple[str, Any]]:
    out = []
    goal = make_goal_board(3)
    for seed, steps in ((1, 3), (2, 5), (3, 6)):
        out.append((f"npuzzle{seed}", make_npuzzle_domain(shuffle_solvable(goal, steps=steps, seed=seed), goal)))
    for preset in get_presets():
        if preset["problem"] == "vacuum" and preset["rooms"] <= 3:
            out.append((preset["id"], make_vacuum_domain(validate_vacuum_state(preset["start_state"]))))
    return out


def pure_problem(domain: Any) -> Problem:
    return Problem(domain.start_state, domain.goal, domain.get_moves, domain.apply_move, domain.step_cost)


def states_of(trace: dict[str, Any]) -> list[Any]:
    return [trace["nodes"][i]["state"] for i in trace["solution_ids"]]


class MatchesPureAlgorithm(unittest.TestCase):
    def test_dls_status_and_solution_match(self) -> None:
        for name, domain in domains():
            for check_cycle in (True, False):
                for limit in range(0, 5):
                    with self.subTest(case=name, cycle=check_cycle, limit=limit):
                        trace = search_trace(
                            domain, algorithm="dls", graph_search=check_cycle, depth_limit=limit, max_nodes=BIG
                        )
                        pure = DLS(pure_problem(domain), limit, check_cycle)
                        if pure == CUTOFF:
                            self.assertEqual(trace["status"], "cutoff")
                        elif pure is None:
                            self.assertEqual(trace["status"], "failure")
                        else:
                            self.assertEqual(trace["status"], "solved")
                            self.assertEqual(trace["summary"]["solution_length"], len(pure) - 1)
                            self.assertEqual(
                                [domain.state_to_json(s) for s in pure], states_of(trace)
                            )

    def test_ids_matches_and_finds_shallowest(self) -> None:
        for name, domain in domains():
            for check_cycle in (True, False):
                with self.subTest(case=name, cycle=check_cycle):
                    trace = search_trace(domain, algorithm="ids", graph_search=check_cycle, max_nodes=BIG)
                    pure = IDS(pure_problem(domain), check_cycle=check_cycle)
                    self.assertEqual(trace["status"], "solved")
                    self.assertEqual(trace["summary"]["solution_length"], len(pure) - 1)
                    self.assertEqual(trace["iterations"], len(pure))


class CycleCheck(unittest.TestCase):
    def test_unreachable_goal_gives_failure_only_with_cycle_check(self) -> None:
        domain = make_vacuum_domain(validate_vacuum_state({"robot": 0, "dirt": [True, True]}))
        impossible = domain.__class__(**{**domain.__dict__, "goal": lambda s: False})
        with_cycle = search_trace(impossible, algorithm="dls", graph_search=True, depth_limit=20, max_nodes=BIG)
        without = search_trace(impossible, algorithm="dls", graph_search=False, depth_limit=4, max_nodes=BIG)
        self.assertEqual(with_cycle["status"], "failure")
        self.assertEqual(without["status"], "cutoff")
        ids = search_trace(impossible, algorithm="ids", graph_search=True, max_nodes=BIG)
        self.assertEqual(ids["status"], "failure")

    def test_cycle_nodes_are_marked_as_pruned(self) -> None:
        domain = make_vacuum_domain(validate_vacuum_state({"robot": 0, "dirt": [True, True]}))
        trace = search_trace(domain, algorithm="dls", graph_search=True, depth_limit=4, max_nodes=BIG)
        pruned = [n for n in trace["nodes"] if n["is_duplicate"]]
        self.assertTrue(pruned)
        self.assertTrue(all(n["duplicate_reason"] == "cycle" for n in pruned))
        for n in pruned:
            anc = trace["nodes"][n["duplicate_of"]]
            self.assertEqual(anc["state"], n["state"])


class CallStack(unittest.TestCase):
    def test_stack_is_consistent_in_every_step(self) -> None:
        for name, domain in domains():
            for algo in ("dls", "ids"):
                trace = search_trace(domain, algorithm=algo, depth_limit=3, max_nodes=BIG)
                for step in trace["steps"]:
                    with self.subTest(case=name, algo=algo, step=step["index"]):
                        frames, limits = step["frontier_ids"], step["frame_limits"]
                        self.assertEqual(len(frames), len(limits))
                        for a, b in zip(limits, limits[1:]):
                            self.assertEqual(a - 1, b)
                        for parent, child in zip(frames, frames[1:]):
                            self.assertEqual(trace["nodes"][child]["parent_id"], parent)
                        self.assertGreaterEqual(min(limits, default=0), 0)

    def test_ids_reuses_node_ids_and_counts_every_regeneration(self) -> None:
        goal = make_goal_board(3)
        domain = make_npuzzle_domain(shuffle_solvable(goal, steps=5, seed=2), goal)
        dls = search_trace(domain, algorithm="dls", depth_limit=trace_depth(domain), max_nodes=BIG)
        ids = search_trace(domain, algorithm="ids", max_nodes=BIG)
        self.assertEqual(ids["summary"]["solution_length"], dls["summary"]["solution_length"])
        self.assertGreaterEqual(ids["summary"]["nodes_generated"], len(ids["nodes"]))
        self.assertGreater(ids["summary"]["nodes_generated"], dls["summary"]["nodes_generated"] - 1)
        keys = {(n["parent_id"], n["action"]) for n in ids["nodes"]}
        self.assertEqual(len(keys), len(ids["nodes"]))

    def test_source_lines_are_read_only_and_follow_options(self) -> None:
        domain = make_vacuum_domain(validate_vacuum_state({"robot": 0, "dirt": [True, True]}))
        for graph in (True, False):
            trace = search_trace(domain, algorithm="ids", graph_search=graph, max_nodes=BIG)
            tags = [line["tag"] for line in trace["source_lines"]]
            self.assertEqual("check_cycle" in tags, graph)
            self.assertTrue(all(line["locked"] and not line["unit"] for line in trace["source_lines"]))
            self.assertEqual([line["line"] for line in trace["source_lines"]], list(range(1, len(tags) + 1)))
            for step in trace["steps"]:
                self.assertIn(step["code_tag"], tags)

    def test_edits_are_ignored(self) -> None:
        domain = make_vacuum_domain(validate_vacuum_state({"robot": 0, "dirt": [True, True]}))
        plain = search_trace(domain, algorithm="dls", depth_limit=3, max_nodes=BIG)
        edited = search_trace(
            domain, algorithm="dls", depth_limit=3, max_nodes=BIG, edits={"disabled": ["check_goal"], "order": {}}
        )
        self.assertEqual(plain["steps"], edited["steps"])


def trace_depth(domain: Any) -> int:
    return search_trace(domain, algorithm="ids", max_nodes=BIG)["summary"]["solution_length"]


class SafetyLimit(unittest.TestCase):
    def test_runaway_search_is_stopped(self) -> None:
        goal = make_goal_board(3)
        domain = make_npuzzle_domain(shuffle_solvable(goal, steps=30, seed=7), goal)
        trace = search_trace(domain, algorithm="dls", graph_search=False, depth_limit=30, max_nodes=50)
        self.assertEqual(trace["status"], "limit_reached")
        self.assertLessEqual(trace["summary"]["nodes_expanded"], 50)


class Api(unittest.TestCase):
    payload = {"problem": "vacuum", "start_state": {"robot": 0, "dirt": [True, True]}}

    def test_depth_limit_is_validated(self) -> None:
        status, body = handle("POST", "/api/solve", {**self.payload, "algorithm": "dls", "depth_limit": 99})
        self.assertEqual(status, 400)
        self.assertIn("depth_limit", body["error"])

    def test_dls_and_ids_are_available(self) -> None:
        for algo in ("dls", "ids"):
            status, body = handle("POST", "/api/solve", {**self.payload, "algorithm": algo, "depth_limit": 3})
            self.assertEqual(status, 200)
            self.assertEqual(body["algorithm"], algo)
            self.assertTrue(body["recursive"])
        status, body = handle("GET", "/api/presets", None)
        self.assertIn("dls", body["algorithms"])
        self.assertIn("ids", body["algorithms"])


if __name__ == "__main__":
    unittest.main()
