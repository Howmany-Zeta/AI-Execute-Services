"""
Unit tests for criteria normalization and verifiers (A-1).
"""

from __future__ import annotations

import pytest

from aiecs.domain.agent.models import AgentGoal
from aiecs.domain.agent.verification.criteria import normalize_acceptance_criteria
from aiecs.domain.agent.verification.models import AcceptanceCriterion, Verdict
from aiecs.domain.agent.verification.read_only_verifier import ReadOnlyAdversarialVerifier
from aiecs.domain.agent.verification.context_builder import build_verification_context
from aiecs.domain.agent.verification.verifier import merge_verdicts


@pytest.mark.unit
class TestNormalizeAcceptanceCriteria:
    def test_legacy_string_not_mutated_on_agent_goal(self) -> None:
        goal = AgentGoal(description="demo", success_criteria="Must include summary")
        criteria = normalize_acceptance_criteria(goal)
        assert len(criteria) == 1
        assert criteria[0].description == "Must include summary"
        assert goal.success_criteria == "Must include summary"

    def test_structured_list_from_dict_goal(self) -> None:
        goal = {
            "goal_id": "g1",
            "success_criteria": [
                {"criterion_id": "c1", "description": "has tests"},
            ],
        }
        criteria = normalize_acceptance_criteria(goal)
        assert len(criteria) == 1
        assert criteria[0].criterion_id == "c1"


@pytest.mark.unit
class TestReadOnlyAdversarialVerifier:
    @pytest.mark.asyncio
    async def test_pass_when_criterion_in_result(self) -> None:
        verifier = ReadOnlyAdversarialVerifier()
        criteria = [AcceptanceCriterion(criterion_id="c1", description="summary section")]
        result = {"output": "This deliverable has summary section content."}
        context = build_verification_context(result=result)
        verdict = await verifier.verify(goal={}, result=result, criteria=criteria, context=context)
        assert verdict.passed is True
        assert verdict.kind == "PASS"

    @pytest.mark.asyncio
    async def test_fail_when_criterion_missing(self) -> None:
        verifier = ReadOnlyAdversarialVerifier()
        criteria = [AcceptanceCriterion(criterion_id="c1", description="GIVEN WHEN THEN")]
        result = {"output": "unstructured text only"}
        context = build_verification_context(result=result)
        verdict = await verifier.verify(goal={}, result=result, criteria=criteria, context=context)
        assert verdict.passed is False
        assert verdict.kind == "FAIL"
        assert "c1" in verdict.failed_criteria


@pytest.mark.unit
class TestMergeVerdicts:
    def test_empty_returns_na(self) -> None:
        verdict = merge_verdicts([])
        assert verdict.kind == "NA"
        assert verdict.passed is True

    def test_merge_fail_and_pass(self) -> None:
        v1 = Verdict(passed=True, kind="PASS", feedback="a")
        v2 = Verdict(passed=False, kind="FAIL", failed_criteria=["c1"], feedback="b")
        merged = merge_verdicts([v1, v2])
        assert merged.passed is False
        assert merged.kind == "FAIL"
        assert "c1" in merged.failed_criteria
