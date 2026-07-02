# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Acceptance criteria normalization (D1-A read boundary)."""

from __future__ import annotations

from typing import Any, Union

from aiecs.domain.agent.models import AgentGoal

from .models import AcceptanceCriterion


def normalize_acceptance_criteria(goal: Union[AgentGoal, dict[str, Any]]) -> list[AcceptanceCriterion]:
    """
    Coerce goal criteria for Verifier/Gate read paths only.

    Legacy string ``success_criteria`` is wrapped as a single implicit criterion
    without mutating stored ``AgentGoal``.
    """
    if isinstance(goal, dict):
        raw = goal.get("success_criteria")
        goal_id = goal.get("goal_id") or goal.get("id") or "legacy"
    else:
        raw = goal.success_criteria
        goal_id = goal.goal_id

    if raw is None:
        return []
    if isinstance(raw, list):
        out: list[AcceptanceCriterion] = []
        for item in raw:
            if isinstance(item, AcceptanceCriterion):
                out.append(item)
            elif isinstance(item, dict):
                out.append(AcceptanceCriterion.from_dict(item))
            else:
                out.append(AcceptanceCriterion(criterion_id=str(item), description=str(item)))
        return out
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return []
        return [
            AcceptanceCriterion(
                criterion_id=f"{goal_id}:legacy",
                description=text,
            )
        ]
    return []
