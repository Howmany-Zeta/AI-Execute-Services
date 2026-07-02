# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Hierarchical goal graph for GVR (A-3)."""

from __future__ import annotations

import json
import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any, Literal, Sequence

from aiecs.domain.agent.models import AgentGoal, GoalGraphConfig, GoalPriority, GoalStatus
from aiecs.domain.agent.verification.models import AcceptanceCriterion, Verdict

GoalOrigin = Literal["root", "decompose", "exploration", "expand"]
DecomposerFn = Callable[[str, str], Awaitable["GoalGraph"]]

_PRIORITY_RANK = {
    GoalPriority.CRITICAL: 0,
    GoalPriority.HIGH: 1,
    GoalPriority.MEDIUM: 2,
    GoalPriority.LOW: 3,
}


def resolve_goal_graph_config(raw: Any) -> GoalGraphConfig | None:
    if raw is None:
        return None
    if isinstance(raw, GoalGraphConfig):
        return raw
    if isinstance(raw, dict):
        return GoalGraphConfig.model_validate(raw)
    raise TypeError(f"Unsupported goal_graph config type: {type(raw)!r}")


def _coerce_structured_criteria(
    success_criteria: Sequence[AcceptanceCriterion | dict[str, Any]],
) -> list[AcceptanceCriterion]:
    if not success_criteria:
        raise ValueError("GoalGraph requires non-empty structured success_criteria")
    out: list[AcceptanceCriterion] = []
    for item in success_criteria:
        if isinstance(item, str):
            raise ValueError("GoalGraph paths require structured list[AcceptanceCriterion]; string criteria rejected")
        if isinstance(item, AcceptanceCriterion):
            out.append(item)
        elif isinstance(item, dict):
            out.append(AcceptanceCriterion.from_dict(item))
        else:
            raise TypeError(f"Unsupported criterion entry: {type(item)!r}")
    return out


class GoalGraph:
    """In-engine hierarchical goals for session resume and GVR context (A-3)."""

    def __init__(self) -> None:
        self._goals: dict[str, AgentGoal] = {}

    @property
    def goal_ids(self) -> list[str]:
        return list(self._goals.keys())

    def get_goal(self, goal_id: str) -> AgentGoal | None:
        return self._goals.get(goal_id)

    def all_goals(self) -> list[AgentGoal]:
        return list(self._goals.values())

    def add_goal(
        self,
        *,
        description: str,
        success_criteria: Sequence[AcceptanceCriterion | dict[str, Any]],
        parent_goal_id: str | None = None,
        depends_on: Sequence[str] | None = None,
        priority: GoalPriority = GoalPriority.MEDIUM,
        origin: GoalOrigin = "root",
        goal_id: str | None = None,
    ) -> AgentGoal:
        """Add a goal with structured criteria (string-only criteria rejected)."""
        criteria = _coerce_structured_criteria(success_criteria)
        goal = AgentGoal(
            goal_id=goal_id or str(uuid.uuid4()),
            description=description,
            success_criteria=criteria,
            parent_goal_id=parent_goal_id,
            depends_on=list(depends_on or []),
            priority=priority,
            origin=origin,
            deadline=None,
            started_at=None,
            achieved_at=None,
        )
        if parent_goal_id is not None and parent_goal_id not in self._goals:
            raise ValueError(f"Unknown parent_goal_id: {parent_goal_id}")
        for dep in goal.depends_on:
            if dep not in self._goals:
                raise ValueError(f"Unknown depends_on goal id: {dep}")
        self._goals[goal.goal_id] = goal
        return goal

    def close_goal(self, goal_id: str, *, status: GoalStatus = GoalStatus.ACHIEVED) -> None:
        goal = self._goals.get(goal_id)
        if goal is None:
            raise ValueError(f"Unknown goal_id: {goal_id}")
        goal.status = status
        if status == GoalStatus.IN_PROGRESS and goal.started_at is None:
            goal.started_at = datetime.utcnow()
        if status == GoalStatus.ACHIEVED:
            goal.progress = 100.0
            goal.achieved_at = datetime.utcnow()

    def _dependencies_satisfied(self, goal: AgentGoal) -> bool:
        for dep_id in goal.depends_on:
            dep = self._goals.get(dep_id)
            if dep is None or dep.status != GoalStatus.ACHIEVED:
                return False
        return True

    def next_open_goal(self) -> AgentGoal | None:
        """Return the next actionable goal (PENDING/IN_PROGRESS with satisfied depends_on)."""
        candidates = [g for g in self._goals.values() if g.status in (GoalStatus.PENDING, GoalStatus.IN_PROGRESS) and self._dependencies_satisfied(g)]
        if not candidates:
            return None
        candidates.sort(key=lambda g: (_PRIORITY_RANK.get(g.priority, 9), g.created_at))
        return candidates[0]

    def spawn_subgoals(
        self,
        parent_goal_id: str,
        missing: Sequence[AcceptanceCriterion | dict[str, Any]],
        *,
        origin: GoalOrigin = "expand",
    ) -> list[AgentGoal]:
        """EXPAND growth: spawn one sub-goal per missing criterion."""
        parent = self._goals.get(parent_goal_id)
        if parent is None:
            raise ValueError(f"Unknown parent_goal_id: {parent_goal_id}")
        criteria = _coerce_structured_criteria(missing)
        spawned: list[AgentGoal] = []
        for criterion in criteria:
            spawned.append(
                self.add_goal(
                    description=f"{parent.description} — {criterion.description or criterion.criterion_id}",
                    success_criteria=[criterion],
                    parent_goal_id=parent_goal_id,
                    origin=origin,
                    priority=parent.priority,
                )
            )
        return spawned

    def record_verdict(self, goal_id: str, verdict: Verdict | dict[str, Any]) -> None:
        """Append-only verdict history for a goal."""
        goal = self._goals.get(goal_id)
        if goal is None:
            raise ValueError(f"Unknown goal_id: {goal_id}")
        payload = verdict.to_dict() if isinstance(verdict, Verdict) else dict(verdict)
        goal.verdict_history = [*goal.verdict_history, payload]

    @classmethod
    async def decompose(
        cls,
        user_request: str,
        protocol: str,
        *,
        decomposer: DecomposerFn | None = None,
    ) -> GoalGraph:
        """
        Host-initiated decomposition hook (D2-A1).

        Raises ``NotImplementedError`` when ``decomposer`` is not provided.
        """
        if decomposer is None:
            raise NotImplementedError(
                "GoalGraph.decompose requires decomposer= callable or a GoalGraph subclass override. " "Built-in LLM decomposer is not available in this release (goal_graph.default_decomposer=none)."
            )
        graph = await decomposer(user_request, protocol)
        if not isinstance(graph, GoalGraph):
            raise TypeError(f"decomposer must return GoalGraph, got {type(graph)!r}")
        return graph

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "goals": [g.model_dump(mode="json") for g in self._goals.values()],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GoalGraph:
        graph = cls()
        for raw in data.get("goals") or []:
            goal = AgentGoal.model_validate(raw)
            graph._goals[goal.goal_id] = goal
        return graph

    @classmethod
    def from_json(cls, payload: str) -> GoalGraph:
        return cls.from_dict(json.loads(payload))

    def sync_to_agent_goals(self) -> dict[str, AgentGoal]:
        """Return a shallow copy map for BaseAIAgent._goals registration."""
        return dict(self._goals)
