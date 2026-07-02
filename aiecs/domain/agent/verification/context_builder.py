# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Build VerificationContext from engine state without executor prompt leakage."""

from __future__ import annotations

from typing import Any, Optional, Sequence, Union

from aiecs.domain.agent.models import AgentGoal

from .models import VerificationContext, VerificationPhase


def _extract_deliverable_refs(result: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    for key in ("deliverable_refs", "artifacts", "files"):
        value = result.get(key)
        if isinstance(value, list):
            refs.extend(str(item) for item in value)
    output = result.get("output")
    if isinstance(output, dict):
        for key in ("deliverable_refs", "artifacts", "files"):
            value = output.get(key)
            if isinstance(value, list):
                refs.extend(str(item) for item in value)
    return sorted(set(refs))


def _goal_snapshot(goal: Optional[Union[AgentGoal, dict[str, Any]]]) -> dict[str, Any]:
    if goal is None:
        return {}
    if isinstance(goal, dict):
        goal_id = goal.get("goal_id") or goal.get("id")
        return {
            "goal_id": goal_id,
            "description": goal.get("description"),
            "status": goal.get("status"),
        }
    return {
        "goal_id": goal.goal_id,
        "description": goal.description,
        "status": goal.status.value if hasattr(goal.status, "value") else goal.status,
    }


def build_verification_context(
    *,
    result: dict[str, Any],
    goal: Optional[Union[AgentGoal, dict[str, Any]]] = None,
    registered_verifier_ids: Optional[Sequence[str]] = None,
    gate_issues: Optional[list[str]] = None,
    iteration: Optional[int] = None,
    phase: Optional[VerificationPhase] = None,
) -> VerificationContext:
    """Construct a minimal VerificationContext for HybridAgent.verify()."""
    registry_snapshot = {
        "registered_verifiers": list(registered_verifier_ids or ()),
    }
    return VerificationContext(
        deliverable_refs=_extract_deliverable_refs(result),
        gate_issues=list(gate_issues or ()),
        registry_snapshot=registry_snapshot,
        goal_snapshot=_goal_snapshot(goal),
        iteration=iteration,
        phase=phase,
    )
