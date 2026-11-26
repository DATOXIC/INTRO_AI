"""Tests for UCS (slide version + optimised version), action costs and the n-room Vacuum world."""

from __future__ import annotations

import heapq
import itertools
import unittest
from typing import Any

from searchviz.core import (
    ALGORITHMS,
    BFS,
    UCS,
    Domain,
    Problem,
    UCS_fast,
    get_source_lines,
    search_trace,
)
from searchviz.problems import get_presets
from searchviz.problems.npuzzle import (
    NPUZZLE_MOVE_COSTS,
    actions_npuzzle,
    cost_npuzzle,
    make_goal_board,
    make_npuzzle_domain,
    result_npuzzle,
    shuffle_solvable,
)
from searchviz.problems.vacuum import (
    MAX_ROOMS,
    MIN_ROOMS,
    VACUUM_MOVE_COSTS,
    actions_vacuum,
    cost_vacuum,
    is_all_clean,
    make_vacuum_domain,
    result_vacuum,
    validate_vacuum_state,
    vacuum_presets,
)
from searchviz.web.api import handle

# Đồ thị nhỏ để ép xảy ra REPLACE: S→A tốn 5 nhưng S→B→A chỉ tốn 1+1.
TOY_GRAPH: dict[str, dict[str, int]] = {
    "S": {"A": 5, "B": 1},
    "B": {"A": 1},
    "A": {"G": 10},
    "G": {},
}


def toy_domain() -> Domain:
    return Domain(
        kind="graph",
        start_state="S",
        goal="G",
        get_moves=lambda s: sorted(TOY_GRAPH[s]),
        apply_move=lambda s, m: m,
        state_to_json=lambda s: s,
        node_extras=lambda s, parent, action: {},
        solvability={"solvable": True, "formula": "", "explanation": ""},
        goal_description="G",
        result_fields={"size": None, "start_board": None, "target_board": None},
        step_cost=lambda s, m: TOY_GRAPH[s][m],
        move_costs={},
    )


def toy_problem() -> Problem:
    return Problem("S", "G", lambda s: sorted(TOY_GRAPH[s]), lambda s, m: m, lambda s, m: TOY_GRAPH[s][m])


def dijkstra_cost(start: Any, domain: Domain) -> int | None:
    """Reference answer: cheapest cost from start to any goal state."""
    goal = domain.goal
    is_goal = goal if callable(goal) else (lambda s: s == goal)
    best = {start: 0}
    heap = [(0, 0, start)]
    tick = itertools.count(1)
    while heap:
        cost, _, state = heapq.heappop(heap)
        if cost > best[state]:
            continue
        if is_goal(state):
            return cost
        for move in domain.get_moves(state):
            nxt = domain.apply_move(state, move)
            ncost = cost + domain.step_cost(state, move)
            if ncost < best.get(nxt, 10**9):
                best[nxt] = ncost
                heapq.heappush(heap, (ncost, next(tick), nxt))
    return None


def events(result: dict[str, Any]) -> list[str]:
    return [step["event_type"] for step in result["steps"]]


class TestActionCosts(unittest.TestCase):
    def test_npuzzle_costs_follow_the_requested_model(self) -> None:
        board = make_goal_board(3)
        self.assertEqual(NPUZZLE_MOVE_COSTS, {"Lên": 1, "Xuống": 1, "Trái": 2, "Phải": 2})
        for move in ("Lên", "Xuống"):
            self.assertEqual(cost_npuzzle(board, move), 1)
        for move in ("Trái", "Phải"):
            self.assertEqual(cost_npuzzle(board, move), 2)

    def test_vacuum_costs_follow_the_requested_model(self) -> None:
        self.assertEqual(VACUUM_MOVE_COSTS, {"Trái": 2, "Phải": 2, "Hút bụi": 1})
        state = (0, True, True)
        self.assertEqual(cost_vacuum(state, "Hút bụi"), 1)
        self.assertEqual(cost_vacuum(state, "Trái"), 2)

    def test_path_cost_is_sum_of_step_costs_for_every_algorithm(self) -> None:
        start = ((1, 2, 3), (5, 0, 6), (4, 7, 8))
        domain = make_npuzzle_domain(start, make_goal_board(3))
        for algorithm in ALGORITHMS:
            res = search_trace(domain, algorithm=algorithm, max_nodes=800)
            self.assertEqual(res["move_costs"], NPUZZLE_MOVE_COSTS)
            by_id = {n["id"]: n for n in res["nodes"]}
            for node in res["nodes"]:
                parent_cost = by_id[node["parent_id"]]["path_cost"] if node["parent_id"] is not None else 0
                self.assertEqual(node["path_cost"], parent_cost + node["step_cost"], msg=algorithm)
                if node["action"] is not None:
                    self.assertEqual(node["step_cost"], NPUZZLE_MOVE_COSTS[node["action"]])

    def test_bfs_reports_the_real_cost_of_its_shortest_path(self) -> None:
        # BFS ít bước nhất (2 bước) nhưng đắt hơn đường UCS tìm được (3 bước).
        bfs = search_trace(toy_domain(), algorithm="bfs")
        ucs = search_trace(toy_domain(), algorithm="ucs")
        self.assertEqual(bfs["summary"]["solution_length"], 2)
        self.assertEqual(bfs["summary"]["solution_cost"], 15)
        self.assertEqual(ucs["summary"]["solution_length"], 3)
        self.assertEqual(ucs["summary"]["solution_cost"], 12)


class TestUCSTrace(unittest.TestCase):
    def test_slide_version_replaces_the_costlier_frontier_node(self) -> None:
        res = search_trace(toy_domain(), algorithm="ucs")
        self.assertEqual(res["status"], "solved")
        self.assertEqual(res["summary"]["solution_cost"], 12)
        self.assertEqual(res["summary"]["replaced"], 1)
        evs = events(res)
        self.assertEqual(evs.count("replace"), 1)
        # thứ tự dòng: dup_frontier → better → replace
        i = evs.index("dup_frontier")
        self.assertEqual(evs[i : i + 3], ["dup_frontier", "better", "replace"])

        replace_step = res["steps"][evs.index("replace")]
        old = res["nodes"][replace_step["collision_id"]]
        new = res["nodes"][replace_step["candidate_id"]]
        self.assertEqual((old["path_cost"], new["path_cost"]), (5, 2))
        self.assertEqual(old["superseded_by"], new["id"])
        self.assertEqual(old["superseded_step"], replace_step["index"])
        self.assertEqual(new["replaces"], old["id"])
        # sau bước replace, nút cũ không còn trong frontier
        self.assertNotIn(old["id"], replace_step["frontier_ids"])
        self.assertIn(new["id"], replace_step["frontier_ids"])

    def test_slide_version_drops_a_costlier_duplicate(self) -> None:
        graph = {"S": {"A": 1, "B": 1}, "A": {"C": 5}, "B": {"C": 7}, "C": {}}
        domain = Domain(
            kind="graph", start_state="S", goal="Z",
            get_moves=lambda s: sorted(graph[s]), apply_move=lambda s, m: m,
            state_to_json=lambda s: s, node_extras=lambda s, p, a: {},
            solvability={"solvable": True, "formula": "", "explanation": ""},
            goal_description="Z", result_fields={"size": None, "start_board": None, "target_board": None},
            step_cost=lambda s, m: graph[s][m],
        )
        for algorithm in ("ucs", "ucs_fast"):
            res = search_trace(domain, algorithm=algorithm)
            self.assertEqual(res["status"], "failure")
            self.assertIn("not_better", events(res), msg=algorithm)
            dropped = [n for n in res["nodes"] if n["is_duplicate"] and n["duplicate_reason"] == "frontier"]
            self.assertEqual(len(dropped), 1, msg=algorithm)
            self.assertEqual(dropped[0]["path_cost"], 8)
            self.assertIsNotNone(dropped[0]["resolved_step"])

    def test_fast_version_keeps_a_stale_node_and_skips_it_on_pop(self) -> None:
        res = search_trace(toy_domain(), algorithm="ucs_fast")
        self.assertEqual(res["status"], "solved")
        self.assertEqual(res["summary"]["solution_cost"], 12)
        evs = events(res)
        self.assertEqual(evs.count("skip_stale"), 1)
        self.assertEqual(res["summary"]["skipped_stale"], 1)

        enqueue_steps = [s for s in res["steps"] if s["event_type"] == "enqueue" and s["collision_id"] is not None]
        self.assertEqual(len(enqueue_steps), 1)
        old = res["nodes"][enqueue_steps[0]["collision_id"]]
        # nút cũ vẫn nằm trong frontier cho tới khi bị pop và bỏ qua
        self.assertIn(old["id"], enqueue_steps[0]["frontier_ids"])
        stale_step = res["steps"][evs.index("skip_stale")]
        self.assertEqual(stale_step["cur_id"], old["id"])
        self.assertEqual(old["discarded_step"], stale_step["index"])
        self.assertIsNone(old["expanded_step"])
        self.assertNotIn(old["id"], stale_step["frontier_ids"])
        # nút cũ không được mở rộng nên không vào explored
        self.assertNotIn(old["id"], res["steps"][-1]["explored_ids"])

    def test_both_versions_share_the_same_expansion_order_without_stale_nodes(self) -> None:
        domain = make_vacuum_domain((1, True, True, True))
        slide = search_trace(domain, algorithm="ucs")
        fast = search_trace(domain, algorithm="ucs_fast")

        def expanded(res: dict[str, Any]) -> list[Any]:
            return [res["nodes"][s["cur_id"]]["state"] for s in res["steps"] if s["event_type"] == "dequeue"]

        self.assertEqual(expanded(slide), expanded(fast))
        self.assertEqual(slide["summary"]["solution_cost"], fast["summary"]["solution_cost"])

    def test_nodes_are_popped_in_non_decreasing_cost_order(self) -> None:
        start = ((1, 2, 3), (5, 0, 6), (4, 7, 8))
        for algorithm in ("ucs", "ucs_fast"):
            res = search_trace(make_npuzzle_domain(start, make_goal_board(3)), algorithm=algorithm, max_nodes=800)
            costs = [res["nodes"][s["cur_id"]]["path_cost"] for s in res["steps"] if s["event_type"] == "dequeue"]
            self.assertEqual(costs, sorted(costs), msg=algorithm)
            for step in res["steps"]:
                fcosts = [res["nodes"][i]["path_cost"] for i in step["frontier_ids"]]
                self.assertEqual(fcosts, sorted(fcosts), msg=f"{algorithm} frontier must stay sorted")

    def test_ucs_is_optimal_on_npuzzle(self) -> None:
        goal = make_goal_board(3)
        for steps, seed in [(3, 1), (5, 2), (7, 3), (8, 4), (9, 5), (10, 6)]:
            start = shuffle_solvable(goal, steps, seed)
            domain = make_npuzzle_domain(start, goal)
            expected = dijkstra_cost(start, domain)
            for algorithm in ("ucs", "ucs_fast"):
                res = search_trace(domain, algorithm=algorithm, max_nodes=3000)
                self.assertEqual(res["status"], "solved", msg=f"{algorithm} {start}")
                self.assertEqual(res["summary"]["solution_cost"], expected, msg=f"{algorithm} {start}")
            problem = Problem(start, goal, actions_npuzzle, result_npuzzle, cost_npuzzle)
            self.assertEqual(UCS(problem)[-1], goal)
            self.assertEqual(UCS_fast(problem)[-1], goal)

    def test_plain_functions_agree_with_the_tracer_on_the_toy_graph(self) -> None:
        self.assertEqual(UCS(toy_problem()), ["S", "B", "A", "G"])
        self.assertEqual(UCS_fast(toy_problem()), ["S", "B", "A", "G"])
        self.assertEqual(BFS(toy_problem()), ["S", "A", "G"])
        for algorithm in ("ucs", "ucs_fast"):
            res = search_trace(toy_domain(), algorithm=algorithm)
            self.assertEqual([res["nodes"][i]["state"] for i in res["solution_ids"]], ["S", "B", "A", "G"])

    def test_ucs_ignores_graph_and_early_goal_options(self) -> None:
        res = search_trace(toy_domain(), algorithm="ucs", graph_search=False, early_goal_test=True)
        self.assertTrue(res["config"]["graph_search"])
        self.assertFalse(res["config"]["early_goal_test"])
        self.assertIn("goal_late", events(res))
        self.assertNotIn("goal_early", events(res))

    def test_every_step_points_to_a_real_pseudocode_line(self) -> None:
        for algorithm in ("ucs", "ucs_fast"):
            lines = get_source_lines(algorithm)
            tags = {item["tag"] for item in lines}
            numbers = {item["line"] for item in lines}
            self.assertEqual(len(numbers), len(lines))
            res = search_trace(toy_domain(), algorithm=algorithm)
            self.assertEqual(res["source_lines"], lines)
            for step in res["steps"]:
                self.assertIn(step["code_tag"], tags, msg=f"{algorithm}: {step['event_type']}")
                self.assertIn(step["line"], numbers)

    def test_pseudocode_text_matches_the_slide(self) -> None:
        slide = [item["code"] for item in get_source_lines("ucs")]
        self.assertEqual(slide[0], "def UCS(problem):")
        self.assertTrue(any("replace(frontier, child)" in code for code in slide))
        self.assertTrue(any("elif child in frontier with higher path_cost" in code for code in slide))
        fast = [item["code"] for item in get_source_lines("ucs_fast")]
        self.assertTrue(any("best_cost" in code for code in fast))
        self.assertFalse(any("replace(" in code for code in fast))

    def test_limit_reached_for_both_versions(self) -> None:
        domain = make_vacuum_domain((1, True, True, True, True))
        for algorithm in ("ucs", "ucs_fast"):
            res = search_trace(domain, algorithm=algorithm, max_nodes=2)
            self.assertEqual(res["status"], "limit_reached")
            self.assertEqual(res["steps"][-1]["event_type"], "limit_reached")


class TestVacuumRooms(unittest.TestCase):
    def test_validate_accepts_two_to_six_rooms(self) -> None:
        for rooms in range(MIN_ROOMS, MAX_ROOMS + 1):
            raw = {"robot": rooms - 1, "dirt": [True] * rooms}
            self.assertEqual(validate_vacuum_state(raw), (rooms - 1, *([True] * rooms)))

    def test_validate_rejects_bad_room_counts_and_robot_positions(self) -> None:
        bad = [
            {"robot": 0, "dirt": [True]},
            {"robot": 0, "dirt": [True] * (MAX_ROOMS + 1)},
            {"robot": 3, "dirt": [True, True, True]},
            {"robot": -1, "dirt": [True, True, True]},
            {"robot": 0, "dirt": [True, 1, True]},
            {"robot": True, "dirt": [True, True]},
            {"dirt": [True, True]},
        ]
        for raw in bad:
            with self.assertRaises(ValueError, msg=repr(raw)):
                validate_vacuum_state(raw)

    def test_transitions_in_a_four_room_corridor(self) -> None:
        state = (1, True, False, True, True)
        self.assertEqual(result_vacuum(state, "Phải"), (2, True, False, True, True))
        self.assertEqual(result_vacuum(state, "Trái"), (0, True, False, True, True))
        self.assertEqual(result_vacuum(state, "Hút bụi"), (1, True, False, True, True))  # phòng sạch: không đổi
        self.assertEqual(result_vacuum((2, True, False, True, True), "Hút bụi"), (2, True, False, False, True))
        # chạm tường là nước đi hợp lệ nhưng không đổi trạng thái
        self.assertEqual(result_vacuum((0, True, True, True, True), "Trái"), (0, True, True, True, True))
        self.assertEqual(result_vacuum((3, True, True, True, True), "Phải"), (3, True, True, True, True))
        self.assertEqual(actions_vacuum(state), ["Trái", "Phải", "Hút bụi"])

    def test_goal_requires_every_room_clean(self) -> None:
        self.assertTrue(is_all_clean((2, False, False, False)))
        self.assertFalse(is_all_clean((2, False, False, True)))

    def test_every_start_state_is_solved_by_every_algorithm(self) -> None:
        for rooms in (2, 3):
            for robot in range(rooms):
                for dirt in itertools.product([False, True], repeat=rooms):
                    start = (robot, *dirt)
                    domain = make_vacuum_domain(start)
                    expected = dijkstra_cost(start, domain)
                    for algorithm in ALGORITHMS:
                        res = search_trace(domain, algorithm=algorithm, max_nodes=3000)
                        self.assertEqual(res["status"], "solved", msg=f"{algorithm} {start}")
                        self.assertEqual(res["rooms"], rooms)
                        if algorithm.startswith("ucs"):
                            self.assertEqual(res["summary"]["solution_cost"], expected, msg=f"{algorithm} {start}")
                        else:
                            self.assertGreaterEqual(res["summary"]["solution_cost"], expected)

    def test_known_optimal_costs(self) -> None:
        # 3 phòng, robot ở A, cả ba bẩn: hút, phải, hút, phải, hút = 3×1 + 2×2 = 7
        res = search_trace(make_vacuum_domain((0, True, True, True)), algorithm="ucs")
        self.assertEqual(res["summary"]["solution_cost"], 7)
        self.assertEqual(res["summary"]["solution_length"], 5)
        # chỉ phòng cuối bẩn: đi qua 2 phòng sạch rồi hút = 2×2 + 1 = 5
        res = search_trace(make_vacuum_domain((0, False, False, True)), algorithm="ucs_fast")
        self.assertEqual(res["summary"]["solution_cost"], 5)

    def test_robot_in_the_middle_prefers_the_cheaper_side_first(self) -> None:
        # Robot ở B (giữa), cả ba phòng bẩn: B → A → B → C (4 bước di chuyển ... ) tối ưu = 3 hút + 3 di chuyển = 9
        res = search_trace(make_vacuum_domain((1, True, True, True)), algorithm="ucs")
        self.assertEqual(res["summary"]["solution_cost"], 9)

    def test_trace_describes_the_world_for_the_ui(self) -> None:
        res = search_trace(make_vacuum_domain((2, True, False, True, False)), algorithm="bfs")
        self.assertEqual(res["rooms"], 4)
        self.assertEqual(res["start_state"], {"robot": 2, "dirt": [True, False, True, False]})
        self.assertEqual(res["goal_description"], "Tất cả các phòng đều sạch")
        self.assertEqual(res["move_costs"], VACUUM_MOVE_COSTS)
        changed = {tuple(n["changed"]) for n in res["nodes"]}
        self.assertIn(("robot",), changed)
        self.assertIn(("dirt2",), changed)

    def test_presets_cover_every_room_count(self) -> None:
        presets = vacuum_presets()
        ids = [p["id"] for p in presets]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual({p["rooms"] for p in presets}, set(range(MIN_ROOMS, MAX_ROOMS + 1)))
        for preset in presets:
            state = validate_vacuum_state(preset["start_state"])
            self.assertEqual(len(state) - 1, preset["rooms"])
            self.assertTrue(any(state[1:]), msg=f"{preset['id']} phải có ít nhất một phòng bẩn")
            res = search_trace(make_vacuum_domain(state), algorithm="ucs", max_nodes=3000)
            self.assertEqual(res["status"], "solved", msg=preset["id"])
        self.assertEqual(len([p for p in get_presets() if p["problem"] == "vacuum"]), len(presets))


class TestApi(unittest.TestCase):
    def test_solve_accepts_ucs_algorithms_and_forces_their_options(self) -> None:
        for algorithm in ("ucs", "ucs_fast"):
            status, res = handle(
                "POST",
                "/api/solve",
                {
                    "problem": "vacuum",
                    "algorithm": algorithm,
                    "graph_search": False,
                    "early_goal_test": True,
                    "start_state": {"robot": 1, "dirt": [True, True, True, True]},
                },
            )
            self.assertEqual(status, 200)
            self.assertEqual(res["algorithm"], algorithm)
            self.assertEqual(res["rooms"], 4)
            self.assertEqual(res["status"], "solved")
            self.assertTrue(res["config"]["graph_search"])
            self.assertFalse(res["config"]["early_goal_test"])

    def test_solve_npuzzle_with_ucs_reports_cost(self) -> None:
        status, res = handle(
            "POST",
            "/api/solve",
            {"size": 3, "algorithm": "ucs", "start_board": [[1, 2, 3], [4, 0, 6], [7, 5, 8]]},
        )
        self.assertEqual(status, 200)
        self.assertEqual(res["summary"]["solution_length"], 2)
        self.assertEqual(res["summary"]["solution_cost"], 3)  # Xuống (1) + Phải (2)
        self.assertEqual(res["move_costs"]["Phải"], 2)

    def test_bad_vacuum_requests_return_400(self) -> None:
        bad = [
            {"problem": "vacuum", "start_state": {"robot": 0, "dirt": [True]}},
            {"problem": "vacuum", "start_state": {"robot": 4, "dirt": [True, True, True]}},
            {"problem": "vacuum", "start_state": {"robot": 0, "dirt": [True] * 9}},
        ]
        for payload in bad:
            status, res = handle("POST", "/api/solve", payload)
            self.assertEqual(status, 400, msg=repr(payload))
            self.assertIn("error", res)

    def test_presets_endpoint_lists_algorithms_and_room_counts(self) -> None:
        status, res = handle("GET", "/api/presets")
        self.assertEqual(status, 200)
        self.assertEqual(res["algorithms"], ["bfs", "dfs", "ucs", "ucs_fast"])
        self.assertEqual(res["vacuum_rooms"], list(range(MIN_ROOMS, MAX_ROOMS + 1)))


if __name__ == "__main__":
    unittest.main()
