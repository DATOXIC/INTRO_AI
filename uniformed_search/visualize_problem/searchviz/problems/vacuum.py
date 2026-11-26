"""Vacuum Robot domain: a row of ``n`` rooms (A, B, C, ...), the classic AIMA vacuum world for n = 2.

State  : ``(robot_room, dirt_0, dirt_1, ..., dirt_{n-1})`` — robot_room is the index of the robot's room,
         dirt_i is True while room i is dirty. There are ``n * 2**n`` states (8 for two rooms).
Actions: "Trái", "Phải", "Hút bụi". Moving into a wall is a legal no-op (the state does not change),
         which creates self-loops and makes the explored set / Tree Search loops visible.
Costs  : moving (Trái / Phải) costs 2, sucking dirt (Hút bụi) costs 1.
Goal   : every room is clean (the robot may stop in any room).
"""

from __future__ import annotations

from typing import Any

from ..core import Domain, Move, search_trace
from .base import SolveOptions

KIND = "vacuum"
VacuumState = tuple  # (robot, dirt_0, ..., dirt_{n-1})
MIN_ROOMS = 2
MAX_ROOMS = 6
ROOM_NAMES = "ABCDEF"
VACUUM_ACTIONS: tuple[Move, ...] = ("Trái", "Phải", "Hút bụi")
VACUUM_MOVE_COSTS: dict[str, int] = {"Trái": 2, "Phải": 2, "Hút bụi": 1}


def room_count(state: VacuumState) -> int:
    return len(state) - 1


def validate_vacuum_state(raw: Any) -> VacuumState:
    """Validate and normalize ``{"robot": int, "dirt": [bool, ...]}`` into a state tuple.

    Raises:
        ValueError: If the structure or values are invalid.
    """
    if not isinstance(raw, dict):
        raise ValueError("Trạng thái Vacuum phải là một object {robot, dirt}.")
    robot = raw.get("robot")
    dirt = raw.get("dirt")
    if not isinstance(dirt, (list, tuple)) or not all(isinstance(d, bool) for d in dirt):
        raise ValueError("Trường 'dirt' phải là danh sách giá trị boolean (mỗi phòng một giá trị).")
    if not (MIN_ROOMS <= len(dirt) <= MAX_ROOMS):
        raise ValueError(f"Số phòng phải nằm trong khoảng [{MIN_ROOMS}, {MAX_ROOMS}].")
    if isinstance(robot, bool) or not isinstance(robot, int) or not (0 <= robot < len(dirt)):
        raise ValueError(f"Trường 'robot' phải là số nguyên trong khoảng [0, {len(dirt) - 1}] (chỉ số phòng).")
    return (robot, *[bool(d) for d in dirt])


def actions_vacuum(state: VacuumState) -> list[Move]:
    """All three actions are always legal in the vacuum world."""
    return list(VACUUM_ACTIONS)


def result_vacuum(state: VacuumState, move: Move) -> VacuumState:
    """Transition model of the n-room vacuum world."""
    robot = state[0]
    rooms = room_count(state)
    if move == "Trái":
        return (max(0, robot - 1), *state[1:])
    if move == "Phải":
        return (min(rooms - 1, robot + 1), *state[1:])
    if move == "Hút bụi":
        dirt = list(state[1:])
        dirt[robot] = False
        return (robot, *dirt)
    raise ValueError(f"Hành động không hợp lệ: {move!r}")


def cost_vacuum(state: VacuumState, move: Move) -> int:
    """Moving costs 2, sucking costs 1."""
    return VACUUM_MOVE_COSTS[move]


def is_all_clean(state: VacuumState) -> bool:
    """Goal test: no dirt left in any room."""
    return not any(state[1:])


def vacuum_state_to_json(state: VacuumState) -> dict[str, Any]:
    return {"robot": state[0], "dirt": [bool(d) for d in state[1:]]}


def _vacuum_extras(state: VacuumState, parent: VacuumState | None, action: Move | None) -> dict[str, Any]:
    """Which parts of the world changed vs. the parent (for highlighting in the UI)."""
    changed: list[str] = []
    if parent is not None:
        if state[0] != parent[0]:
            changed.append("robot")
        for idx in range(room_count(state)):
            if state[1 + idx] != parent[1 + idx]:
                changed.append(f"dirt{idx}")
    return {"changed": changed}


def make_vacuum_domain(start_state: VacuumState) -> Domain:
    """Build the trace domain for one vacuum-world instance."""
    rooms = room_count(start_state)
    return Domain(
        kind="vacuum",
        start_state=start_state,
        goal=is_all_clean,
        get_moves=actions_vacuum,
        apply_move=result_vacuum,
        state_to_json=vacuum_state_to_json,
        node_extras=_vacuum_extras,
        solvability={
            "solvable": True,
            "formula": "Vacuum luôn giải được: hút bụi ở phòng hiện tại, đi sang phòng bẩn kế tiếp rồi hút tiếp.",
            "explanation": (
                f"Chỉ có {rooms * 2 ** rooms} trạng thái ({rooms} phòng × 2^{rooms} cách bụi) "
                "và từ mọi trạng thái đều tới được trạng thái sạch hoàn toàn."
            ),
        },
        goal_description="Tất cả các phòng đều sạch" if rooms > 2 else "Cả hai phòng đều sạch",
        result_fields={"size": None, "start_board": None, "target_board": None, "rooms": rooms},
        step_cost=cost_vacuum,
        move_costs=dict(VACUUM_MOVE_COSTS),
    )


def _preset(pid: str, rooms: int, name: str, description: str, robot: int, dirt: list[bool]) -> dict[str, Any]:
    return {
        "id": pid,
        "problem": "vacuum",
        "rooms": rooms,
        "name": f"Vacuum ({rooms} phòng) — {name}",
        "description": description,
        "start_state": {"robot": robot, "dirt": dirt},
    }


def vacuum_presets() -> list[dict[str, Any]]:
    """Curated vacuum-world learning presets for 2..MAX_ROOMS rooms."""
    presets = [
        _preset(
            "v_both_a", 2, "Cả hai bẩn, robot ở A",
            "Bài toán kinh điển trong AIMA. Lời giải tối ưu 3 bước: Hút bụi → Phải → Hút bụi.",
            0, [True, True],
        ),
        _preset(
            "v_both_b", 2, "Cả hai bẩn, robot ở B",
            "Đối xứng với bài trên: Hút bụi → Trái → Hút bụi.",
            1, [True, True],
        ),
        _preset(
            "v_far", 2, "Chỉ phòng B bẩn, robot ở A",
            "Robot phải sang phòng B trước rồi mới hút: Phải → Hút bụi.",
            0, [False, True],
        ),
        _preset(
            "v_near", 2, "Chỉ phòng A bẩn, robot ở A",
            "Chỉ cần 1 bước: Hút bụi. Quan sát kiểm tra đích ngay khi sinh con.",
            0, [True, False],
        ),
    ]
    for rooms in range(3, MAX_ROOMS + 1):
        last = ROOM_NAMES[rooms - 1]
        mid = rooms // 2
        presets += [
            _preset(
                f"v{rooms}_all_left", rooms, "Tất cả bẩn, robot ở A",
                f"Robot phải quét qua cả {rooms} phòng: càng nhiều phòng, cây tìm kiếm càng rộng.",
                0, [True] * rooms,
            ),
            _preset(
                f"v{rooms}_all_mid", rooms, f"Tất cả bẩn, robot ở {ROOM_NAMES[mid]} (giữa)",
                "Robot ở giữa nên phải chọn đi bên nào trước: thấy rõ DFS và BFS chọn khác nhau.",
                mid, [True] * rooms,
            ),
            _preset(
                f"v{rooms}_far", rooms, f"Chỉ phòng {last} bẩn, robot ở A",
                f"Robot phải đi qua {rooms - 1} phòng sạch mới tới phòng bẩn duy nhất.",
                0, [False] * (rooms - 1) + [True],
            ),
            _preset(
                f"v{rooms}_alt", rooms, f"Bẩn xen kẽ, robot ở {last}",
                "Phòng A, C, E... bẩn xen kẽ phòng sạch: nhiều cách xếp thứ tự hút khác nhau.",
                rooms - 1, [i % 2 == 0 for i in range(rooms)],
            ),
        ]
    return presets


# ── Xử lý yêu cầu từ API ────────────────────────────────────────────────────

presets = vacuum_presets


def solve(payload: dict[str, Any], options: SolveOptions) -> dict[str, Any]:
    """Chạy thuật toán trên một đề Vacuum (``start_state`` = {robot, dirt})."""
    domain = make_vacuum_domain(validate_vacuum_state(payload.get("start_state")))
    return search_trace(
        domain,
        algorithm=options.algorithm,
        graph_search=options.graph_search,
        early_goal_test=options.early_goal_test,
        max_nodes=options.max_nodes,
    )
