"""Bài toán n-Puzzle: bảng k × k trượt ô (k = 2, 3, 4).

Chỉ chứa phần riêng của n-Puzzle: trạng thái, hành động, chuyển trạng thái, kiểm tra giải được,
đề mẫu và cách xử lý yêu cầu. Thuật toán và ghi vết nằm ở ``searchviz.core``.
Chi phí: Lên/Xuống tốn 1, Trái/Phải tốn 2 (dùng cho UCS).
"""

from __future__ import annotations

import random
from typing import Any

from ..core import Domain, get_source_lines, search_trace
from .base import SolveOptions, parse_int

KIND = "npuzzle"
Board = tuple[tuple[int, ...], ...]
Move = str
ALLOWED_SIZES = (2, 3, 4)
MOVE_ORDER: tuple[Move, ...] = ("Lên", "Xuống", "Trái", "Phải")
MOVE_DELTAS: dict[Move, tuple[int, int]] = {
    "Lên": (-1, 0),
    "Xuống": (1, 0),
    "Trái": (0, -1),
    "Phải": (0, 1),
}


def make_goal_board(size: int) -> Board:
    """Build standard goal board for a size x size n-puzzle (1..n, 0 at bottom-right)."""
    if size not in ALLOWED_SIZES:
        raise ValueError(f"Kích thước bảng phải thuộc {ALLOWED_SIZES}, nhận được: {size}")
    nums = list(range(1, size * size)) + [0]
    return tuple(tuple(nums[r * size : (r + 1) * size]) for r in range(size))


def validate_board(raw_board: Any, expected_size: int | None = None) -> Board:
    """Validate and normalize an incoming 2D board into an immutable Board tuple.

    Raises:
        ValueError: If structure, dimensions, or tile values are invalid.
    """
    if not isinstance(raw_board, (list, tuple)) or len(raw_board) == 0:
        raise ValueError("Bảng phải là danh sách 2 chiều không rỗng.")

    size = len(raw_board)
    if size not in ALLOWED_SIZES:
        raise ValueError(f"Chỉ hỗ trợ bảng kích thước {ALLOWED_SIZES}, nhận được {size}x{size}.")
    if expected_size is not None and size != expected_size:
        raise ValueError(f"Kích thước bảng ({size}x{size}) không khớp size={expected_size}.")

    rows: list[tuple[int, ...]] = []
    seen_tiles: list[int] = []
    for row_idx, row in enumerate(raw_board):
        if not isinstance(row, (list, tuple)) or len(row) != size:
            raise ValueError(f"Hàng {row_idx} phải có đúng {size} phần tử.")
        parsed_row: list[int] = []
        for val in row:
            if isinstance(val, bool) or not isinstance(val, int):
                raise ValueError(f"Giá trị ô phải là số nguyên, nhận được: {val!r}")
            parsed_row.append(val)
            seen_tiles.append(val)
        rows.append(tuple(parsed_row))

    expected_tiles = set(range(size * size))
    if set(seen_tiles) != expected_tiles or len(seen_tiles) != size * size:
        raise ValueError(
            f"Bảng {size}x{size} phải chứa đủ và duy nhất các số từ 0 đến {size * size - 1}."
        )

    return tuple(rows)


def find_blank(board: Board) -> tuple[int, int]:
    """Return (row, col) coordinates of the blank tile (0)."""
    size = len(board)
    for r in range(size):
        for c in range(size):
            if board[r][c] == 0:
                return r, c
    raise ValueError("Không tìm thấy ô trống (0) trên bảng.")


def actions_npuzzle(board: Board) -> list[Move]:
    """Return valid blank-tile moves for any k x k n-puzzle board."""
    size = len(board)
    blank_r, blank_c = find_blank(board)
    valid_moves: list[Move] = []
    if blank_r > 0:
        valid_moves.append("Lên")
    if blank_r < size - 1:
        valid_moves.append("Xuống")
    if blank_c > 0:
        valid_moves.append("Trái")
    if blank_c < size - 1:
        valid_moves.append("Phải")
    return valid_moves


def result_npuzzle(board: Board, move: Move) -> Board:
    """Return the new Board after sliding the blank tile in the given direction."""
    if move not in MOVE_DELTAS:
        raise ValueError(f"Hướng di chuyển không hợp lệ: {move!r}")
    size = len(board)
    blank_r, blank_c = find_blank(board)
    dr, dc = MOVE_DELTAS[move]
    new_r, new_c = blank_r + dr, blank_c + dc
    if not (0 <= new_r < size and 0 <= new_c < size):
        raise ValueError(f"Nước đi {move!r} từ {(blank_r, blank_c)} vượt ra ngoài biên bảng {size}x{size}.")

    grid = [list(row) for row in board]
    grid[blank_r][blank_c] = grid[new_r][new_c]
    grid[new_r][new_c] = 0
    return tuple(tuple(row) for row in grid)


def count_inversions(board: Board) -> int:
    """Count permutation inversions of non-zero tiles in row-major order."""
    flat = [val for row in board for val in row if val != 0]
    inversions = 0
    for i in range(len(flat)):
        for j in range(i + 1, len(flat)):
            if flat[i] > flat[j]:
                inversions += 1
    return inversions


def analyze_solvability(start_board: Board, target_board: Board) -> dict[str, Any]:
    """Check whether start_board can reach target_board and explain the parity math."""
    size = len(start_board)
    start_inv = count_inversions(start_board)
    target_inv = count_inversions(target_board)
    start_blank_r, _ = find_blank(start_board)
    target_blank_r, _ = find_blank(target_board)

    if size % 2 == 1:
        start_parity = start_inv % 2
        target_parity = target_inv % 2
        solvable = start_parity == target_parity
        formula = "Bảng kích thước lẻ (k lẻ): Giải được ⇔ số nghịch thế (inversions) cùng tính chẵn/lẻ với Đích."
        detail = (
            f"Start có {start_inv} nghịch thế ({'chẵn' if start_parity == 0 else 'lẻ'}), "
            f"Goal có {target_inv} nghịch thế ({'chẵn' if target_parity == 0 else 'lẻ'}) "
            f"→ {'CÙNG tính chẵn/lẻ (GIẢI ĐƯỢC)' if solvable else 'KHÁC tính chẵn/lẻ (VÔ NGHIỆM)'}."
        )
    else:
        start_parity = (start_inv + start_blank_r) % 2
        target_parity = (target_inv + target_blank_r) % 2
        solvable = start_parity == target_parity
        formula = (
            "Bảng kích thước chẵn (k chẵn): Giải được ⇔ (số nghịch thế + chỉ số hàng của ô 0) "
            "cùng tính chẵn/lẻ với Đích."
        )
        detail = (
            f"Start: ({start_inv} + hàng {start_blank_r}) mod 2 = {start_parity}, "
            f"Goal: ({target_inv} + hàng {target_blank_r}) mod 2 = {target_parity} "
            f"→ {'BẰNG NHAU (GIẢI ĐƯỢC)' if solvable else 'KHÁC NHAU (VÔ NGHIỆM)'}."
        )

    return {
        "solvable": solvable,
        "size": size,
        "start_inversions": start_inv,
        "target_inversions": target_inv,
        "start_blank_row": start_blank_r,
        "target_blank_row": target_blank_r,
        "start_parity": start_parity,
        "target_parity": target_parity,
        "formula": formula,
        "explanation": detail,
    }


def is_solvable(start_board: Board, target_board: Board) -> bool:
    """Return True if start_board is reachable from target_board."""
    return bool(analyze_solvability(start_board, target_board)["solvable"])


def manhattan_distance(board: Board, target_board: Board) -> int:
    """Compute Manhattan distance heuristic h1 (sum of L1 distances of tiles 1..n)."""
    size = len(board)
    goal_pos: dict[int, tuple[int, int]] = {}
    for r in range(size):
        for c in range(size):
            val = target_board[r][c]
            if val != 0:
                goal_pos[val] = (r, c)

    total = 0
    for r in range(size):
        for c in range(size):
            val = board[r][c]
            if val != 0:
                gr, gc = goal_pos[val]
                total += abs(r - gr) + abs(c - gc)
    return total


def misplaced_tiles(board: Board, target_board: Board) -> int:
    """Count non-zero tiles not in their target position (Hamming heuristic)."""
    size = len(board)
    count = 0
    for r in range(size):
        for c in range(size):
            val = board[r][c]
            if val != 0 and val != target_board[r][c]:
                count += 1
    return count


def shuffle_solvable(
    target_board: Board,
    steps: int,
    seed: int | None = None,
) -> Board:
    """Generate a guaranteed-solvable board by applying random valid moves from target_board.

    Avoids immediately undoing the previous move so the resulting board is non-trivial.
    """
    if steps < 0 or steps > 50:
        raise ValueError("Số bước xáo trộn phải nằm trong khoảng [0, 50].")
    rng = random.Random(seed)
    opposite: dict[Move, Move] = {
        "Lên": "Xuống",
        "Xuống": "Lên",
        "Trái": "Phải",
        "Phải": "Trái",
    }

    cur = target_board
    last_move: Move | None = None
    visited_walk: set[Board] = {cur}
    for _ in range(steps):
        moves = actions_npuzzle(cur)
        if last_move is not None and len(moves) > 1:
            filtered = [m for m in moves if m != opposite[last_move]]
            if filtered:
                moves = filtered
        fresh = [m for m in moves if result_npuzzle(cur, m) not in visited_walk]
        chosen = rng.choice(fresh if fresh else moves)
        cur = result_npuzzle(cur, chosen)
        visited_walk.add(cur)
        last_move = chosen
    return cur


def presets() -> list[dict[str, Any]]:
    """Return curated n-puzzle learning presets across 2x2, 3x3, and 4x4 sizes."""
    return [
        {
            "problem": "npuzzle",
            "id": "p3_easy",
            "name": "3-Puzzle (2×2) — 3 bước",
            "size": 2,
            "description": "Bảng nhỏ nhất (2×2), cực kỳ dễ quan sát toàn bộ cây tìm kiếm và cơ chế lọc trùng.",
            "start_board": [[0, 2], [1, 3]],
            "target_board": [[1, 2], [3, 0]],
        },
        {
            "problem": "npuzzle",
            "id": "p8_slide",
            "name": "8-Puzzle (3×3) — Mẫu slide (2 bước)",
            "size": 3,
            "description": "Đúng bài mẫu trong notebook buổi 5, lời giải tối ưu 2 bước.",
            "start_board": [[1, 2, 3], [4, 0, 6], [7, 5, 8]],
            "target_board": [[1, 2, 3], [4, 5, 6], [7, 8, 0]],
        },
        {
            "problem": "npuzzle",
            "id": "p8_branch",
            "name": "8-Puzzle (3×3) — Phân nhánh rõ (5 bước)",
            "size": 3,
            "description": "Cách đích 5 bước: thấy rõ sóng BFS mở rộng tầng 0→5, nhiều nhánh trùng bị cắt ở frontier & explored.",
            "start_board": [[1, 2, 3], [5, 0, 6], [4, 7, 8]],
            "target_board": [[1, 2, 3], [4, 5, 6], [7, 8, 0]],
        },
        {
            "problem": "npuzzle",
            "id": "p8_medium",
            "name": "8-Puzzle (3×3) — Trung bình (7 bước)",
            "size": 3,
            "description": "Cách đích 7 bước: minh họa sự tăng trưởng nhanh của kích thước frontier theo O(b^d).",
            "start_board": [[1, 3, 6], [4, 2, 0], [7, 5, 8]],
            "target_board": [[1, 2, 3], [4, 5, 6], [7, 8, 0]],
        },
        {
            "problem": "npuzzle",
            "id": "p8_unsolvable",
            "name": "8-Puzzle (3×3) — Vô nghiệm (1 nghịch thế lẻ)",
            "size": 3,
            "description": "Hoán đổi ô 7 và 8: khác tính chẵn/lẻ số nghịch thế nên không bao giờ tới đích được.",
            "start_board": [[1, 2, 3], [4, 5, 6], [8, 7, 0]],
            "target_board": [[1, 2, 3], [4, 5, 6], [7, 8, 0]],
        },
        {
            "problem": "npuzzle",
            "id": "p15_easy",
            "name": "15-Puzzle (4×4) — 4 bước",
            "size": 4,
            "description": "Mở rộng sang bảng 4×4 (15-puzzle) với 4 bước tối ưu, chứng minh thuật toán hoạt động tổng quát cho mọi n.",
            "start_board": [
                [1, 2, 3, 4],
                [5, 6, 7, 8],
                [9, 10, 0, 11],
                [13, 14, 15, 12],
            ],
            "target_board": [
                [1, 2, 3, 4],
                [5, 6, 7, 8],
                [9, 10, 11, 12],
                [13, 14, 15, 0],
            ],
        },
    ]


NPUZZLE_MOVE_COSTS: dict[str, int] = {"Lên": 1, "Xuống": 1, "Trái": 2, "Phải": 2}


def cost_npuzzle(board: Board, move: Move) -> int:
    """Chi phí một nước đi: Lên/Xuống tốn 1, Trái/Phải tốn 2."""
    return NPUZZLE_MOVE_COSTS[move]


def make_npuzzle_domain(start_board: Board, target_board: Board) -> Domain:
    """Build the trace domain for one n-puzzle instance."""
    if len(start_board) != len(target_board):
        raise ValueError("start_board và target_board phải cùng kích thước.")

    def extras(state: Board, parent: Board | None, action: Move | None) -> dict[str, Any]:
        blank_from: list[int] | None = None
        moved_tile: int | None = None
        if parent is not None:
            pr, pc = find_blank(parent)
            blank_from = [pr, pc]
            moved_tile = state[pr][pc]
        return {
            "manhattan": manhattan_distance(state, target_board),
            "misplaced": misplaced_tiles(state, target_board),
            "inversions": count_inversions(state),
            "moved_tile": moved_tile,
            "blank_from": blank_from,
            "blank_to": list(find_blank(state)),
        }

    size = len(start_board)
    return Domain(
        kind="npuzzle",
        start_state=start_board,
        goal=target_board,
        get_moves=actions_npuzzle,
        apply_move=result_npuzzle,
        state_to_json=lambda board: [list(row) for row in board],
        node_extras=extras,
        solvability=analyze_solvability(start_board, target_board),
        goal_description="Bảng đích",
        result_fields={
            "size": size,
            "start_board": [list(r) for r in start_board],
            "target_board": [list(r) for r in target_board],
        },
        step_cost=cost_npuzzle,
        move_costs=dict(NPUZZLE_MOVE_COSTS),
    )


def BFS_trace(
    start_board: Board,
    target_board: Board,
    *,
    graph_search: bool = True,
    early_goal_test: bool = True,
    max_nodes: int = 300,
) -> dict[str, Any]:
    """Run instrumented BFS on an n-puzzle and return the complete line-by-line debug trace."""
    return search_trace(
        make_npuzzle_domain(start_board, target_board),
        algorithm="bfs",
        graph_search=graph_search,
        early_goal_test=early_goal_test,
        max_nodes=max_nodes,
    )


def DFS_trace(
    start_board: Board,
    target_board: Board,
    *,
    graph_search: bool = True,
    early_goal_test: bool = True,
    max_nodes: int = 300,
) -> dict[str, Any]:
    """Run instrumented DFS on an n-puzzle and return the complete line-by-line debug trace."""
    return search_trace(
        make_npuzzle_domain(start_board, target_board),
        algorithm="dfs",
        graph_search=graph_search,
        early_goal_test=early_goal_test,
        max_nodes=max_nodes,
    )


def _target_board(payload: dict[str, Any], size: int) -> Board:
    raw_target = payload.get("target_board")
    return validate_board(raw_target, expected_size=size) if raw_target is not None else make_goal_board(size)


def solve(payload: dict[str, Any], options: SolveOptions) -> dict[str, Any]:
    """Chạy thuật toán trên một đề n-Puzzle; đề vô nghiệm bị chặn trừ khi ``force_run``."""
    raw_start = payload.get("start_board")
    if raw_start is None:
        raise ValueError("Thiếu trường 'start_board'.")
    size = parse_int(payload.get("size"), "size", len(raw_start) if isinstance(raw_start, list) else 3, 2, 4)
    start_board = validate_board(raw_start, expected_size=size)
    target_board = _target_board(payload, size)

    solvability = analyze_solvability(start_board, target_board)
    if not solvability["solvable"] and not options.force_run:
        return {
            "status": "unsolvable_blocked",
            "problem": KIND,
            "algorithm": options.algorithm,
            "size": size,
            "start_board": [list(r) for r in start_board],
            "target_board": [list(r) for r in target_board],
            "config": {
                "graph_search": options.graph_search,
                "early_goal_test": options.early_goal_test,
                "max_nodes": options.max_nodes,
            },
            "solvability": solvability,
            "source_lines": get_source_lines(options.algorithm, options.graph_search, options.early_goal_test, options.edits),
            "nodes": [],
            "steps": [],
            "solution_ids": None,
            "summary": None,
        }

    return search_trace(
        make_npuzzle_domain(start_board, target_board),
        algorithm=options.algorithm,
        graph_search=options.graph_search,
        early_goal_test=options.early_goal_test,
        max_nodes=options.max_nodes,
        edits=options.edits,
        depth_limit=options.depth_limit,
    )


def shuffle(payload: dict[str, Any]) -> dict[str, Any]:
    """Tạo đề ngẫu nhiên chắc chắn giải được bằng cách xáo ngược từ bảng đích."""
    size = parse_int(payload.get("size"), "size", 3, 2, 4)
    if size not in ALLOWED_SIZES:
        raise ValueError(f"Kích thước phải thuộc {ALLOWED_SIZES}.")
    steps = parse_int(payload.get("steps"), "steps", 5, 0, 50)
    raw_seed = payload.get("seed")
    seed = parse_int(raw_seed, "seed", 0, -2_147_483_648, 2_147_483_647) if raw_seed is not None else None

    target_board = _target_board(payload, size)
    shuffled = shuffle_solvable(target_board, steps=steps, seed=seed)
    return {
        "size": size,
        "start_board": [list(r) for r in shuffled],
        "target_board": [list(r) for r in target_board],
        "solvability": analyze_solvability(shuffled, target_board),
    }


def check(payload: dict[str, Any]) -> dict[str, Any]:
    """Kiểm tra bảng xuất phát hợp lệ và có giải được không."""
    raw_start = payload.get("start_board")
    if raw_start is None:
        raise ValueError("Thiếu trường 'start_board'.")
    start_board = validate_board(raw_start)
    size = len(start_board)
    target_board = _target_board(payload, size)
    return {
        "valid": True,
        "size": size,
        "solvability": analyze_solvability(start_board, target_board),
    }
