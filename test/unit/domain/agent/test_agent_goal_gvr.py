"""
Unit tests for AgentGoal GVR extensions (A-3 / D1-A).
"""

from __future__ import annotations

import json

import pytest

from aiecs.domain.agent.models import AgentGoal
from aiecs.domain.agent.verification.models import AcceptanceCriterion, Verdict


@pytest.mark.unit
class TestAgentGoalSerialization:
    def test_legacy_string_success_criteria_unchanged(self) -> None:
        goal = AgentGoal(description="demo", success_criteria="Must include summary")
        assert goal.success_criteria == "Must include summary"
        dumped = goal.model_dump(mode="json")
        assert dumped["success_criteria"] == "Must include summary"
        assert "goal_id" in dumped
        assert "parent_goal_id" in dumped
        assert "id" not in dumped
        assert "parent_id" not in dumped

    def test_deserialize_gvr_aliases(self) -> None:
        goal = AgentGoal.model_validate(
            {
                "id": "g-alias",
                "parent_id": "p1",
                "description": "from aliases",
                "success_criteria": "legacy",
            }
        )
        assert goal.goal_id == "g-alias"
        assert goal.parent_goal_id == "p1"
        assert goal.id == "g-alias"
        assert goal.parent_id == "p1"
        dumped = goal.model_dump(mode="json")
        assert dumped["goal_id"] == "g-alias"
        assert dumped["parent_goal_id"] == "p1"

    def test_structured_success_criteria_round_trip(self) -> None:
        goal = AgentGoal(
            description="structured",
            success_criteria=[
                AcceptanceCriterion(criterion_id="c1", description="has tests"),
            ],
        )
        raw = json.loads(goal.model_dump_json())
        restored = AgentGoal.model_validate(raw)
        assert isinstance(restored.success_criteria, list)
        assert restored.success_criteria[0].criterion_id == "c1"

    def test_verdict_history_append_only(self) -> None:
        goal = AgentGoal(description="v")
        v1 = Verdict(passed=True, kind="PASS", feedback="ok")
        v2 = Verdict(passed=False, kind="FAIL", feedback="no")
        goal.append_verdict(v1)
        goal.append_verdict(v2)
        assert len(goal.verdict_history) == 2
        assert goal.verdict_history[0]["kind"] == "PASS"
        prior = goal.verdict_history[0]
        goal.append_verdict(Verdict(passed=False, kind="FAIL", feedback="x"))
        assert goal.verdict_history[0] == prior
