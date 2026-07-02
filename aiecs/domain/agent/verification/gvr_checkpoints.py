# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""GVR checkpoint dedupe helpers (policy + A-8 gate paths)."""

from __future__ import annotations

from typing import Any

_GATES_RUN_KEY = "gvr.gate_checkpoints"


def gates_dedupe_key(goal_id: str | None, iteration: int) -> str:
    """Trigger-independent key: one L2 gate evaluation per goal iteration."""
    return f"{goal_id or 'none'}:{iteration}:gates"


def _gate_checkpoints(plugin_state: dict[str, Any]) -> list[str]:
    raw = plugin_state.get(_GATES_RUN_KEY)
    if raw is None:
        checkpoints: list[str] = []
    elif isinstance(raw, set):
        checkpoints = sorted(str(item) for item in raw)
    elif isinstance(raw, list):
        checkpoints = [str(item) for item in raw]
    else:
        checkpoints = [str(raw)]
    plugin_state[_GATES_RUN_KEY] = checkpoints
    return checkpoints


def gates_already_run(plugin_state: dict[str, Any] | None, goal_id: str | None, iteration: int) -> bool:
    if not isinstance(plugin_state, dict):
        return False
    return gates_dedupe_key(goal_id, iteration) in _gate_checkpoints(plugin_state)


def mark_gates_run(plugin_state: dict[str, Any] | None, goal_id: str | None, iteration: int) -> None:
    if not isinstance(plugin_state, dict):
        return
    dedupe = gates_dedupe_key(goal_id, iteration)
    checkpoints = _gate_checkpoints(plugin_state)
    if dedupe not in checkpoints:
        checkpoints.append(dedupe)
    plugin_state[_GATES_RUN_KEY] = checkpoints
