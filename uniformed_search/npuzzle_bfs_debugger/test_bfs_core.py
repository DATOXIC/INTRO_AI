"""Unit and integration tests for n-Puzzle BFS Core and HTTP Debugger Server."""

from __future__ import annotations

import json
import threading
import unittest
import urllib.error
import urllib.request
from typing import Any

from bfs_core import (
    BFS,
    BFS_trace,
    DFS,
    DFS_trace,
    Problem,
    actions_npuzzle,
    analyze_solvability,
    count_inversions,
    get_presets,
    is_solvable,
    make_goal_board,
    manhattan_distance,
    misplaced_tiles,
    result_npuzzle,
    search_trace,
    shuffle_solvable,
    validate_board,
)
from server import create_server
from vacuum_world import (
    actions_vacuum,
    is_all_clean,
    make_vacuum_domain,
    result_vacuum,
    validate_vacuum_state,
)


class TestNPuzzleDomain(unittest.TestCase):
    def test_make_goal_board_all_sizes(self) -> None:
        self.assertEqual(make_goal_board(2), ((1, 2), (3, 0)))
        self.assertEqual(make_goal_board(3), ((1, 2, 3), (4, 5, 6), (7, 8, 0)))
        self.assertEqual(
            make_goal_board(4),
            ((1, 2, 3, 4), (5, 6, 7, 8), (9, 10, 11, 12), (13, 14, 15, 0)),
        )

    def test_solvability_odd_and_even_grids(self) -> None:
        # 2x2 even grid
        self.assertTrue(is_solvable(((0, 2), (1, 3)), make_goal_board(2)))
        self.assertFalse(is_solvable(((2, 1), (3, 0)), make_goal_board(2)))

        # 3x3 odd grid
        self.assertTrue(is_solvable(((1, 2, 3), (4, 0, 6), (7, 5, 8)), make_goal_board(3)))
        self.assertFalse(is_solvable(((1, 2, 3), (4, 5, 6), (8, 7, 0)), make_goal_board(3)))

        # 4x4 even grid (Sam Loyd's classic unsolvable 14-15 swap)
        goal4 = make_goal_board(4)
        self.assertTrue(
            is_solvable(
                ((1, 2, 3, 4), (5, 6, 7, 8), (9, 10, 0, 11), (13, 14, 15, 12)),
                goal4,
            )
        )
        self.assertFalse(
            is_solvable(
                ((1, 2, 3, 4), (5, 6, 7, 8), (9, 10, 11, 12), (13, 15, 14, 0)),
                goal4,
            )
        )

    def test_heuristics_and_inversions(self) -> None:
        goal3 = make_goal_board(3)
        self.assertEqual(count_inversions(goal3), 0)
        self.assertEqual(manhattan_distance(goal3, goal3), 0)
        self.assertEqual(misplaced_tiles(goal3, goal3), 0)

        board = ((1, 2, 3), (4, 0, 6), (7, 5, 8))
        self.assertEqual(manhattan_distance(board, goal3), 2)
        self.assertEqual(misplaced_tiles(board, goal3), 2)

    def test_shuffle_solvable_is_deterministic_and_solvable(self) -> None:
        for size in (2, 3, 4):
            goal = make_goal_board(size)
            b1 = shuffle_solvable(goal, steps=6, seed=42)
            b2 = shuffle_solvable(goal, steps=6, seed=42)
            self.assertEqual(b1, b2)
            self.assertTrue(is_solvable(b1, goal))

    def test_validate_board_rejects_invalid_and_adversarial_inputs(self) -> None:
        bad_inputs: list[Any] = [
            [],
            [[0]],
            [[1, 2, 3, 4, 5]] * 5,
            [[1, 2], [3]],
            [[1, 1], [3, 0]],
            [[1, 2], [3, 4]],
            [[True, 2], [3, 0]],
            [["1", 2], [3, 0]],
            None,
            "not a board",
        ]
        for bad in bad_inputs:
            with self.assertRaises(ValueError, msg=f"Should reject {bad!r}"):
                validate_board(bad)


class TestBFSTrace(unittest.TestCase):
    def _assert_valid_solution_trace(self, res: dict[str, Any]) -> None:
        self.assertEqual(res["status"], "solved")
        sol_ids = res["solution_ids"]
        self.assertIsNotNone(sol_ids)
        nodes = res["nodes"]
        self.assertEqual(nodes[sol_ids[0]]["state"], res["start_board"])
        self.assertEqual(nodes[sol_ids[-1]]["state"], res["target_board"])
        for i in range(len(sol_ids) - 1):
            cur_b = validate_board(nodes[sol_ids[i]]["state"])
            nxt_node = nodes[sol_ids[i + 1]]
            self.assertIn(nxt_node["action"], actions_npuzzle(cur_b))
            self.assertEqual(
                [list(r) for r in result_npuzzle(cur_b, nxt_node["action"])],
                nxt_node["state"],
            )

    def test_all_solvable_presets_match_standard_bfs(self) -> None:
        for preset in get_presets():
            if preset["problem"] != "npuzzle":
                continue
            start = validate_board(preset["start_board"])
            target = validate_board(preset["target_board"])
            if not is_solvable(start, target):
                continue
            res = BFS_trace(start, target, graph_search=True, early_goal_test=True, max_nodes=1000)
            self._assert_valid_solution_trace(res)

            std_path = BFS(Problem(start, target, actions_npuzzle, result_npuzzle))
            self.assertIsNotNone(std_path)
            self.assertEqual(res["summary"]["solution_length"], len(std_path) - 1)

    def test_already_at_goal_both_goal_modes(self) -> None:
        goal3 = make_goal_board(3)
        for early in (True, False):
            res = BFS_trace(goal3, goal3, graph_search=True, early_goal_test=early)
            self._assert_valid_solution_trace(res)
            self.assertEqual(res["summary"]["solution_length"], 0)

    def test_early_vs_late_goal_test_same_optimal_length(self) -> None:
        start = ((1, 2, 3), (5, 0, 6), (4, 7, 8))
        target = make_goal_board(3)
        res_early = BFS_trace(start, target, graph_search=True, early_goal_test=True)
        res_late = BFS_trace(start, target, graph_search=True, early_goal_test=False)

        self._assert_valid_solution_trace(res_early)
        self._assert_valid_solution_trace(res_late)
        self.assertEqual(res_early["summary"]["solution_length"], res_late["summary"]["solution_length"])
        self.assertLessEqual(res_early["summary"]["nodes_expanded"], res_late["summary"]["nodes_expanded"])

    def test_duplicate_collision_invariants_and_source_lines(self) -> None:
        start = ((1, 2, 3), (5, 0, 6), (4, 7, 8))
        target = make_goal_board(3)
        res = BFS_trace(start, target, graph_search=True, early_goal_test=True)

        valid_lines = {item["line"] for item in res["source_lines"]}
        nodes = res["nodes"]
        skipped_seen = 0
        for step in res["steps"]:
            self.assertIn(step["line"], valid_lines)
            if step["event_type"] in ("skip_explored", "skip_frontier"):
                skipped_seen += 1
                cand = nodes[step["candidate_id"]]
                coll = nodes[step["collision_id"]]
                self.assertTrue(cand["is_duplicate"])
                self.assertEqual(cand["state"], coll["state"])
        self.assertGreater(skipped_seen, 0)

    def _follow_events(self, steps: list[dict[str, Any]], gen_idx: int) -> list[str]:
        """Event types that resolve the child generated at steps[gen_idx]."""
        cid = steps[gen_idx]["candidate_id"]
        follow: list[str] = []
        j = gen_idx + 1
        while j < len(steps) and steps[j]["candidate_id"] == cid:
            follow.append(steps[j]["event_type"])
            j += 1
        return follow

    def test_each_pseudocode_line_is_its_own_step(self) -> None:
        start = ((1, 2, 3), (5, 0, 6), (4, 7, 8))
        res = BFS_trace(start, make_goal_board(3), graph_search=True, early_goal_test=True)
        steps, nodes = res["steps"], res["nodes"]

        self.assertEqual(
            [s["event_type"] for s in steps[:6]],
            ["init_root", "check_root", "init", "init_explored", "dequeue", "explore"],
        )
        allowed = [
            ["skip_explored"],
            ["skip_frontier"],
            ["check_pass", "check_goal", "enqueue"],
            ["check_pass", "goal_early"],
        ]
        gen_steps = [i for i, s in enumerate(steps) if s["event_type"] == "gen_child"]
        self.assertGreater(len(gen_steps), 0)
        for i in gen_steps:
            follow = self._follow_events(steps, i)
            self.assertIn(follow, allowed)
            cid = steps[i]["candidate_id"]
            self.assertEqual(nodes[cid]["created_step"], i)
            self.assertEqual(nodes[cid]["resolved_step"], i + len(follow))

    def test_late_goal_and_tree_search_step_shapes(self) -> None:
        start = ((1, 2, 3), (5, 0, 6), (4, 7, 8))
        goal = make_goal_board(3)

        late = BFS_trace(start, goal, graph_search=True, early_goal_test=False)
        late_events = {s["event_type"] for s in late["steps"]}
        self.assertIn("check_late", late_events)
        self.assertNotIn("check_goal", late_events)
        self.assertNotIn("check_root", late_events)

        tree = BFS_trace(start, goal, graph_search=False, early_goal_test=True, max_nodes=10)
        tree_events = {s["event_type"] for s in tree["steps"]}
        self.assertNotIn("init_explored", tree_events)
        self.assertNotIn("explore", tree_events)
        self.assertNotIn("check_pass", tree_events)
        self.assertNotIn("skip_explored", tree_events)
        for i, s in enumerate(tree["steps"]):
            if s["event_type"] == "gen_child":
                self.assertEqual(self._follow_events(tree["steps"], i)[-1:], ["enqueue"])

    def test_unsolvable_2x2_exhausts_frontier_cleanly(self) -> None:
        res = BFS_trace(((2, 1), (3, 0)), make_goal_board(2), graph_search=True, max_nodes=100)
        self.assertEqual(res["status"], "failure")
        self.assertIsNone(res["solution_ids"])
        self.assertEqual(res["summary"]["nodes_expanded"], 12)
        self.assertFalse(res["solvability"]["solvable"])

    def test_tree_search_respects_max_nodes_safety_cap(self) -> None:
        start = ((1, 2, 3), (5, 0, 6), (4, 7, 8))
        target = make_goal_board(3)
        res = BFS_trace(start, target, graph_search=False, early_goal_test=True, max_nodes=25)
        self.assertEqual(res["status"], "limit_reached")
        self.assertEqual(res["summary"]["nodes_expanded"], 25)
        self.assertEqual(res["summary"]["skipped_explored"], 0)
        self.assertEqual(res["summary"]["skipped_frontier"], 0)


class TestDFS(unittest.TestCase):
    START = ((1, 2, 3), (5, 0, 6), (4, 7, 8))

    def test_dfs_pops_from_the_top_of_the_stack(self) -> None:
        res = DFS_trace(self.START, make_goal_board(3), graph_search=True, early_goal_test=True)
        steps = res["steps"]
        for i, step in enumerate(steps):
            if step["event_type"] != "dequeue":
                continue
            # frontier right BEFORE the pop = frontier AFTER the pop + the popped node on top.
            before = steps[i - 1]["frontier_ids"]
            self.assertEqual(before[-1], step["cur_id"])
            self.assertEqual(before[:-1], step["frontier_ids"])

    def test_dfs_enqueue_pushes_on_top_and_pseudocode_mentions_stack(self) -> None:
        res = DFS_trace(self.START, make_goal_board(3))
        for step in res["steps"]:
            if step["event_type"] == "enqueue":
                self.assertEqual(step["frontier_ids"][-1], step["candidate_id"])
        code = "\n".join(item["code"] for item in res["source_lines"])
        self.assertIn("def DFS(problem):", code)
        self.assertIn("Stack()", code)
        self.assertIn("pop(frontier)", code)
        self.assertIn("push(frontier, child)", code)
        self.assertEqual(res["algorithm"], "dfs")

    def test_dfs_finds_valid_but_not_necessarily_shortest_solution(self) -> None:
        goal = make_goal_board(3)
        bfs = BFS_trace(self.START, goal)
        dfs = DFS_trace(self.START, goal, max_nodes=1000)
        self.assertEqual(dfs["status"], "solved")
        self.assertGreaterEqual(dfs["summary"]["solution_length"], bfs["summary"]["solution_length"])
        sol = dfs["solution_ids"]
        nodes = dfs["nodes"]
        self.assertEqual(nodes[sol[0]]["state"], dfs["start_board"])
        self.assertEqual(nodes[sol[-1]]["state"], dfs["target_board"])
        for a, b in zip(sol, sol[1:]):
            cur = validate_board(nodes[a]["state"])
            self.assertEqual(
                [list(r) for r in result_npuzzle(cur, nodes[b]["action"])],
                nodes[b]["state"],
            )

        plain = DFS(Problem(self.START, goal, actions_npuzzle, result_npuzzle))
        self.assertIsNotNone(plain)

    def test_invalid_algorithm_rejected(self) -> None:
        with self.assertRaises(ValueError):
            search_trace(make_vacuum_domain((0, True, True)), algorithm="astar")


class TestVacuumWorld(unittest.TestCase):
    def test_transition_model(self) -> None:
        self.assertEqual(result_vacuum((0, True, True), "Hút bụi"), (0, False, True))
        self.assertEqual(result_vacuum((1, True, True), "Hút bụi"), (1, True, False))
        self.assertEqual(result_vacuum((0, True, False), "Phải"), (1, True, False))
        # Bumping into the wall is a legal no-op.
        self.assertEqual(result_vacuum((0, True, False), "Trái"), (0, True, False))
        self.assertEqual(actions_vacuum((0, True, True)), ["Trái", "Phải", "Hút bụi"])
        self.assertTrue(is_all_clean((1, False, False)))
        self.assertFalse(is_all_clean((1, False, True)))
        with self.assertRaises(ValueError):
            result_vacuum((0, True, True), "Bay")

    def test_validate_state_rejects_bad_input(self) -> None:
        self.assertEqual(validate_vacuum_state({"robot": 1, "dirt": [True, False]}), (1, True, False))
        for bad in [None, [], {"robot": 2, "dirt": [True, True]}, {"robot": True, "dirt": [True, True]},
                    {"robot": 0, "dirt": [True]}, {"robot": 0, "dirt": [1, 0]}, {"robot": 0}]:
            with self.assertRaises(ValueError, msg=repr(bad)):
                validate_vacuum_state(bad)

    def test_bfs_and_dfs_solve_every_start_state(self) -> None:
        for robot in (0, 1):
            for dirt_a in (False, True):
                for dirt_b in (False, True):
                    start = (robot, dirt_a, dirt_b)
                    for algorithm in ("bfs", "dfs"):
                        res = search_trace(make_vacuum_domain(start), algorithm=algorithm)
                        self.assertEqual(res["status"], "solved", msg=f"{algorithm} {start}")
                        self.assertEqual(res["problem"], "vacuum")
                        last = res["nodes"][res["solution_ids"][-1]]["state"]
                        self.assertEqual(last["dirt"], [False, False])
                    # BFS is optimal: it needs exactly (#dirty rooms) Suck actions plus at most one move.
                    bfs = search_trace(make_vacuum_domain(start), algorithm="bfs")
                    dirty = int(dirt_a) + int(dirt_b)
                    self.assertGreaterEqual(bfs["summary"]["solution_length"], dirty)
                    self.assertLessEqual(bfs["summary"]["solution_length"], dirty + 1)

    def test_known_optimal_solution_length_and_actions(self) -> None:
        res = search_trace(make_vacuum_domain((0, True, True)), algorithm="bfs")
        self.assertEqual(res["summary"]["solution_length"], 3)
        actions = [res["nodes"][i]["action"] for i in res["solution_ids"][1:]]
        self.assertEqual(actions, ["Hút bụi", "Phải", "Hút bụi"])

    def test_self_loops_are_pruned_by_explored_and_loop_forever_in_tree_dfs(self) -> None:
        graph = search_trace(make_vacuum_domain((0, True, True)), algorithm="bfs", graph_search=True)
        self.assertGreater(graph["summary"]["skipped_explored"], 0)
        for step in graph["steps"]:
            if step["event_type"] == "skip_explored":
                cand = graph["nodes"][step["candidate_id"]]
                coll = graph["nodes"][step["collision_id"]]
                self.assertEqual(cand["state"], coll["state"])

        # Tree-search DFS keeps taking the same "Hút bụi" no-op: it never terminates by itself.
        loop = search_trace(
            make_vacuum_domain((0, True, True)), algorithm="dfs", graph_search=False, max_nodes=40
        )
        self.assertEqual(loop["status"], "limit_reached")
        self.assertEqual(loop["summary"]["nodes_expanded"], 40)

    def test_node_records_expose_actions_and_changes(self) -> None:
        res = search_trace(make_vacuum_domain((0, True, True)), algorithm="bfs")
        for node in res["nodes"]:
            self.assertEqual(node["actions"], ["Trái", "Phải", "Hút bụi"])
            self.assertIn("changed", node)
        sucked = next(n for n in res["nodes"] if n["action"] == "Hút bụi" and n["depth"] == 1)
        self.assertEqual(sucked["changed"], ["dirt0"])
        moved = next(n for n in res["nodes"] if n["action"] == "Phải" and n["depth"] == 1)
        self.assertEqual(moved["changed"], ["robot"])

    def test_vacuum_presets_are_listed_and_valid(self) -> None:
        vac = [p for p in get_presets() if p["problem"] == "vacuum"]
        self.assertGreaterEqual(len(vac), 3)
        for preset in vac:
            validate_vacuum_state(preset["start_state"])


class TestHTTPServerIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = create_server("127.0.0.1", 0)
        cls.port = cls.server.server_address[1]
        cls.base_url = f"http://127.0.0.1:{cls.port}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()

    def _request(self, method: str, path: str, body: bytes | None = None) -> tuple[int, str]:
        req = urllib.request.Request(
            f"{self.base_url}{path}",
            data=body,
            method=method,
            headers={"Content-Type": "application/json"} if body is not None else {},
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status, resp.read().decode("utf-8")
        except urllib.error.HTTPError as err:
            return err.code, err.read().decode("utf-8")

    def test_static_pages_and_presets(self) -> None:
        code, html = self._request("GET", "/")
        self.assertEqual(code, 200)
        self.assertIn("Search Debugger", html)

        code, raw = self._request("GET", "/api/presets")
        self.assertEqual(code, 200)
        data = json.loads(raw)
        self.assertGreaterEqual(len(data["presets"]), 5)

    def test_path_traversal_blocked(self) -> None:
        code, _ = self._request("GET", "/../server.py")
        self.assertEqual(code, 404)

    def test_solve_endpoint_happy_and_unsolvable(self) -> None:
        payload = json.dumps({
            "size": 3,
            "start_board": [[1, 2, 3], [4, 0, 6], [7, 5, 8]],
            "target_board": [[1, 2, 3], [4, 5, 6], [7, 8, 0]],
        }).encode("utf-8")
        code, raw = self._request("POST", "/api/solve", payload)
        self.assertEqual(code, 200)
        res = json.loads(raw)
        self.assertEqual(res["status"], "solved")
        self.assertEqual(res["summary"]["solution_length"], 2)

        # Unsolvable blocked by default
        unsolv = json.dumps({
            "size": 2,
            "start_board": [[2, 1], [3, 0]],
            "target_board": [[1, 2], [3, 0]],
        }).encode("utf-8")
        code, raw = self._request("POST", "/api/solve", unsolv)
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(raw)["status"], "unsolvable_blocked")

        # Unsolvable with force_run=True runs to failure
        unsolv_force = json.dumps({
            "size": 2,
            "start_board": [[2, 1], [3, 0]],
            "target_board": [[1, 2], [3, 0]],
            "force_run": True,
        }).encode("utf-8")
        code, raw = self._request("POST", "/api/solve", unsolv_force)
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(raw)["status"], "failure")

    def test_solve_endpoint_supports_dfs_and_vacuum(self) -> None:
        dfs = json.dumps({
            "size": 3,
            "algorithm": "dfs",
            "max_nodes": 500,
            "start_board": [[1, 2, 3], [5, 0, 6], [4, 7, 8]],
        }).encode("utf-8")
        code, raw = self._request("POST", "/api/solve", dfs)
        self.assertEqual(code, 200)
        res = json.loads(raw)
        self.assertEqual(res["algorithm"], "dfs")
        self.assertEqual(res["problem"], "npuzzle")
        self.assertEqual(res["status"], "solved")

        vac = json.dumps({
            "problem": "vacuum",
            "algorithm": "bfs",
            "start_state": {"robot": 0, "dirt": [True, True]},
        }).encode("utf-8")
        code, raw = self._request("POST", "/api/solve", vac)
        self.assertEqual(code, 200)
        res = json.loads(raw)
        self.assertEqual(res["problem"], "vacuum")
        self.assertEqual(res["summary"]["solution_length"], 3)
        self.assertEqual(res["goal_description"], "Cả hai phòng đều sạch")

        code, raw = self._request("GET", "/api/presets")
        presets = json.loads(raw)["presets"]
        self.assertIn("vacuum", {p["problem"] for p in presets})
        self.assertIn("npuzzle", {p["problem"] for p in presets})

    def test_unknown_problem_algorithm_or_vacuum_state_return_400(self) -> None:
        bad_payloads = [
            {"problem": "chess", "start_board": [[1, 2], [3, 0]]},
            {"algorithm": "astar", "start_board": [[1, 2], [3, 0]]},
            {"problem": "vacuum", "start_state": {"robot": 5, "dirt": [True, True]}},
            {"problem": "vacuum"},
        ]
        for payload in bad_payloads:
            code, raw = self._request("POST", "/api/solve", json.dumps(payload).encode("utf-8"))
            self.assertEqual(code, 400, msg=repr(payload))
            self.assertIn("error", json.loads(raw))

    def test_invalid_payloads_return_400(self) -> None:
        code, _ = self._request("POST", "/api/solve", b"{bad json")
        self.assertEqual(code, 400)

        bad_board = json.dumps({"size": 3, "start_board": [[1, 1, 1], [0, 0, 0], [2, 3, 4]]}).encode("utf-8")
        code, raw = self._request("POST", "/api/solve", bad_board)
        self.assertEqual(code, 400)
        self.assertIn("error", json.loads(raw))

        bad_max = json.dumps({
            "size": 2,
            "start_board": [[1, 2], [3, 0]],
            "max_nodes": -5,
        }).encode("utf-8")
        code, _ = self._request("POST", "/api/solve", bad_max)
        self.assertEqual(code, 400)


if __name__ == "__main__":
    unittest.main()
