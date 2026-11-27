"""Tests cho việc tắt dòng / đổi chỗ dòng mã giả ("nếu bỏ lệnh này thì sao?")."""

from __future__ import annotations

import unittest
from typing import Any

from searchviz.core import get_source_lines
from searchviz.core.program import LOCKED_TAGS, apply_edits, build_program, render_lines
from searchviz.web.api import handle

BOARD = {
    "problem": "npuzzle",
    "start_board": [[1, 2, 3], [5, 0, 6], [4, 7, 8]],
    "target_board": [[1, 2, 3], [4, 5, 6], [7, 8, 0]],
    "max_nodes": 60,
}


def solve(algorithm: str = "bfs", program: Any = None, **extra: Any) -> dict[str, Any]:
    payload = {**BOARD, "algorithm": algorithm, **extra}
    if program is not None:
        payload["program"] = program
    status, body = handle("POST", "/api/solve", payload)
    assert status == 200, body
    return body


class ApplyEditsTests(unittest.TestCase):
    def test_no_edits_leaves_program_untouched(self) -> None:
        for algo in ("bfs", "dfs", "ucs", "ucs_fast"):
            base = render_lines(build_program(algo))
            prog, disabled, applied = apply_edits(build_program(algo), None)
            self.assertEqual(render_lines(prog, disabled), base)
            self.assertEqual(applied, {"disabled": [], "order": {}})

    def test_unknown_tags_are_ignored_and_missing_tags_keep_their_place(self) -> None:
        prog, disabled, applied = apply_edits(
            build_program("bfs"),
            {"disabled": ["nope"], "order": {"while_loop": ["add_explored"], "ghost": ["x"]}},
        )
        self.assertEqual(disabled, frozenset())
        tags = [l["tag"] for l in render_lines(prog, disabled)]
        # add_explored được kéo lên đầu khối; dequeue và for_move giữ thứ tự cũ phía sau
        self.assertEqual(tags[tags.index("while_loop") + 1:][:3], ["add_explored", "dequeue", "for_move"])
        self.assertEqual(applied["order"], {"while_loop": ["add_explored", "dequeue", "for_move"]})

    def test_structural_lines_cannot_be_disabled_or_moved(self) -> None:
        prog, disabled, _ = apply_edits(
            build_program("bfs"),
            {"disabled": sorted(LOCKED_TAGS), "order": {"root": ["return_none", "init_root"]}},
        )
        self.assertEqual(disabled, frozenset())
        root_tags = [l["tag"] for l in render_lines(prog, disabled) if l["block"] == "root"]
        self.assertEqual(root_tags[-1], "return_none")
        self.assertEqual(root_tags[0], "init_root")

    def test_bad_shapes_raise_value_error(self) -> None:
        for bad in ("x", {"disabled": "x"}, {"disabled": [1]}, {"order": []}, {"order": {"a": "b"}}):
            with self.assertRaises(ValueError, msg=str(bad)):
                apply_edits(build_program("bfs"), bad)

    def test_elif_branch_moves_together_with_its_if(self) -> None:
        lines = render_lines(build_program("ucs"))
        by_tag = {l["tag"]: l for l in lines}
        self.assertTrue(by_tag["check_duplicate"]["unit"])
        self.assertFalse(by_tag["check_better"]["unit"])
        self.assertEqual(by_tag["check_better"]["block"], by_tag["check_duplicate"]["block"])

    def test_move_flags(self) -> None:
        by_tag = {l["tag"]: l for l in get_source_lines("bfs")}
        self.assertFalse(by_tag["init_root"]["can_up"])
        self.assertTrue(by_tag["init_root"]["can_down"])
        self.assertTrue(by_tag["dequeue"]["can_down"])
        self.assertFalse(by_tag["return_none"]["can_up"] or by_tag["return_none"]["can_down"])
        self.assertTrue(by_tag["return_none"]["locked"])


class EditedRunTests(unittest.TestCase):
    def test_unedited_result_has_no_program_key(self) -> None:
        self.assertNotIn("program", solve())

    def test_edited_result_echoes_what_took_effect(self) -> None:
        body = solve(program={"disabled": ["add_explored", "zzz"]})
        self.assertEqual(body["program"], {"disabled": ["add_explored"], "order": {}})
        by_tag = {l["tag"]: l for l in body["source_lines"]}
        self.assertTrue(by_tag["add_explored"]["disabled"])
        self.assertTrue(all(s["code_tag"] != "add_explored" for s in body["steps"]))

    def test_disabling_the_frontier_setup_is_a_clear_program_error(self) -> None:
        body = solve(program={"disabled": ["init_queue"]})
        self.assertEqual(body["status"], "program_error")
        self.assertIn("`frontier`", body["error"]["message"])
        self.assertIn("TẮT", body["error"]["message"])
        last = body["steps"][-1]
        self.assertEqual(last["event_type"], "program_error")
        self.assertEqual(last["line"], body["error"]["line"])

    def test_using_a_variable_before_it_exists_is_reported(self) -> None:
        body = solve(program={"order": {"while_loop": ["add_explored", "dequeue", "for_move"]}})
        self.assertEqual(body["status"], "program_error")
        self.assertIn("`cur_node`", body["error"]["message"])
        self.assertIn("chưa chạy trước", body["error"]["message"])

    def test_moving_add_explored_after_the_loop_still_finds_the_same_solution(self) -> None:
        base = solve()
        moved = solve(program={"order": {"while_loop": ["dequeue", "for_move", "add_explored"]}})
        self.assertEqual(moved["status"], "solved")
        self.assertEqual(moved["summary"]["solution_length"], base["summary"]["solution_length"])

    def test_without_explored_dfs_loops_until_the_safety_limit(self) -> None:
        body = solve("dfs", {"disabled": ["add_explored"]})
        self.assertEqual(body["status"], "limit_reached")
        self.assertEqual(body["steps"][-1]["event_type"], "limit_reached")

    def test_without_any_goal_test_the_search_never_stops_on_its_own(self) -> None:
        self.assertEqual(solve(program={"disabled": ["check_early_goal"]})["status"], "limit_reached")
        self.assertEqual(solve("ucs", {"disabled": ["check_late_goal"]})["status"], "limit_reached")

    def test_never_enqueueing_children_exhausts_the_frontier(self) -> None:
        body = solve(program={"disabled": ["enqueue_child"]})
        self.assertEqual(body["status"], "failure")

    def test_goal_test_after_enqueue_changes_the_trace_but_not_the_answer(self) -> None:
        base = solve()
        swapped = solve(program={"order": {"check_duplicate": ["enqueue_child", "check_early_goal"]}})
        self.assertEqual(swapped["summary"]["solution_length"], base["summary"]["solution_length"])
        self.assertNotEqual(swapped["steps"], base["steps"])

    def test_dropping_the_duplicate_check_makes_the_search_do_more_work(self) -> None:
        base = solve()
        no_check = solve(program={"disabled": ["check_duplicate"]})
        self.assertGreater(no_check["summary"]["nodes_generated"], base["summary"]["nodes_generated"])

    def test_ucs_variants_accept_edits(self) -> None:
        for tag in ("check_stale", "check_best", "update_best"):
            body = solve("ucs_fast", {"disabled": [tag]})
            self.assertEqual(body["status"], "solved", tag)
        body = solve("ucs", {"disabled": ["check_better"]})
        self.assertEqual(body["status"], "solved")

    def test_edits_from_another_algorithm_are_harmless(self) -> None:
        body = solve("bfs", {"disabled": ["check_stale", "replace_child"], "order": {"check_best": ["a"]}})
        self.assertEqual(body["status"], "solved")
        self.assertNotIn("program", body)

    def test_api_rejects_malformed_program(self) -> None:
        status, body = handle("POST", "/api/solve", {**BOARD, "program": {"disabled": "add_explored"}})
        self.assertEqual(status, 400)
        self.assertIn("program", body["error"])

    def test_blocked_unsolvable_board_still_returns_edited_source_lines(self) -> None:
        payload = {
            "problem": "npuzzle",
            "algorithm": "bfs",
            "start_board": [[1, 2, 3], [4, 5, 6], [8, 7, 0]],
            "target_board": [[1, 2, 3], [4, 5, 6], [7, 8, 0]],
            "program": {"disabled": ["add_explored"]},
        }
        status, body = handle("POST", "/api/solve", payload)
        self.assertEqual((status, body["status"]), (200, "unsolvable_blocked"))
        self.assertTrue(next(l for l in body["source_lines"] if l["tag"] == "add_explored")["disabled"])


if __name__ == "__main__":
    unittest.main()
