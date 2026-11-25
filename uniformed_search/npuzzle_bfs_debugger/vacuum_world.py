"""Vacuum Robot domain: the classic two-room vacuum world from AIMA.

State  : (robot_room, dirt_in_A, dirt_in_B), robot_room 0 = room A, 1 = room B  → 8 states.
Actions: "Trái", "Phải", "Hút bụi". Moving into a wall is a legal no-op (the state does not
         change), which creates self-loops and makes the explored set / Tree Search loops visible.
Goal   : both rooms clean (the robot may stop in either room).
"""

from __future__ import annotations

from typing import Any

from search_core import Domain, Move

VacuumState = tuple[int, bool, bool]
ROOM_NAMES = ("A", "B")
VACUUM_ACTIONS: tuple[Move, ...] = ("Trái", "Phải", "Hút bụi")


def validate_vacuum_state(raw: Any) -> VacuumState:
    """Validate and normalize ``{"robot": 0|1, "dirt": [bool, bool]}`` into a state tuple.

    Raises:
        ValueError: If the structure or values are invalid.
    """
    if not isinstance(raw, dict):
        raise ValueError("Trạng thái Vacuum phải là một object {robot, dirt}.")
    robot = raw.get("robot")
    dirt = raw.get("dirt")
    if isinstance(robot, bool) or robot not in (0, 1):
        raise ValueError("Trường 'robot' phải là 0 (phòng A) hoặc 1 (phòng B).")
    if not isinstance(dirt, (list, tuple)) or len(dirt) != 2 or not all(isinstance(d, bool) for d in dirt):
        raise ValueError("Trường 'dirt' phải là danh sách 2 giá trị boolean (phòng A, phòng B).")
    return (int(robot), bool(dirt[0]), bool(dirt[1]))


def actions_vacuum(state: VacuumState) -> list[Move]:
    """All three actions are always legal in the vacuum world."""
    return list(VACUUM_ACTIONS)


def result_vacuum(state: VacuumState, move: Move) -> VacuumState:
    """Transition model of the two-room vacuum world."""
    robot, dirt_a, dirt_b = state
    if move == "Trái":
        return (0, dirt_a, dirt_b)
    if move == "Phải":
        return (1, dirt_a, dirt_b)
    if move == "Hút bụi":
        return (robot, False if robot == 0 else dirt_a, False if robot == 1 else dirt_b)
    raise ValueError(f"Hành động không hợp lệ: {move!r}")


def is_all_clean(state: VacuumState) -> bool:
    """Goal test: no dirt left in either room."""
    return not state[1] and not state[2]


def vacuum_state_to_json(state: VacuumState) -> dict[str, Any]:
    return {"robot": state[0], "dirt": [state[1], state[2]]}


def _vacuum_extras(state: VacuumState, parent: VacuumState | None, action: Move | None) -> dict[str, Any]:
    """Which parts of the world changed vs. the parent (for highlighting in the UI)."""
    changed: list[str] = []
    if parent is not None:
        if state[0] != parent[0]:
            changed.append("robot")
        for idx in (0, 1):
            if state[1 + idx] != parent[1 + idx]:
                changed.append(f"dirt{idx}")
    return {"changed": changed}


def make_vacuum_domain(start_state: VacuumState) -> Domain:
    """Build the trace domain for one vacuum-world instance."""
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
            "formula": "Vacuum luôn giải được: hút bụi ở phòng hiện tại, đi sang phòng kia rồi hút tiếp.",
            "explanation": "Chỉ có 8 trạng thái và từ mọi trạng thái đều tới được trạng thái sạch hoàn toàn.",
        },
        goal_description="Cả hai phòng đều sạch",
        result_fields={"size": None, "start_board": None, "target_board": None},
    )


def vacuum_presets() -> list[dict[str, Any]]:
    """Curated vacuum-world learning presets."""
    return [
        {
            "id": "v_both_a",
            "problem": "vacuum",
            "name": "Vacuum (2 phòng) — Cả hai bẩn, robot ở A",
            "description": "Bài toán kinh điển trong AIMA. Lời giải tối ưu 3 bước: Hút bụi → Phải → Hút bụi.",
            "start_state": {"robot": 0, "dirt": [True, True]},
        },
        {
            "id": "v_both_b",
            "problem": "vacuum",
            "name": "Vacuum (2 phòng) — Cả hai bẩn, robot ở B",
            "description": "Đối xứng với bài trên: Hút bụi → Trái → Hút bụi.",
            "start_state": {"robot": 1, "dirt": [True, True]},
        },
        {
            "id": "v_far",
            "problem": "vacuum",
            "name": "Vacuum (2 phòng) — Chỉ phòng B bẩn, robot ở A",
            "description": "Robot phải sang phòng B trước rồi mới hút: Phải → Hút bụi.",
            "start_state": {"robot": 0, "dirt": [False, True]},
        },
        {
            "id": "v_near",
            "problem": "vacuum",
            "name": "Vacuum (2 phòng) — Chỉ phòng A bẩn, robot ở A",
            "description": "Chỉ cần 1 bước: Hút bụi. Quan sát kiểm tra đích ngay khi sinh con.",
            "start_state": {"robot": 0, "dirt": [True, False]},
        },
    ]
