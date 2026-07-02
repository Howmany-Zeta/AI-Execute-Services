"""CWE multi-perspective verifier tests (A-11)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from aiecs.domain.agent.models import AgentGoal
from aiecs.domain.agent.verification.cwe_verifier import (
    CweVerifier,
    build_cwe_verifier_from_config,
    is_h1_goal,
    run_dual_spawn_verifier_path,
)
from aiecs.domain.agent.verification.cwe_verifier_policy_models import CweVerifierPolicy
from aiecs.domain.agent.verification.models import AcceptanceCriterion, VerificationContext
from aiecs.domain.agent.verification.review_refinement import (
    REVIEW_REFINEMENT_TEMPLATE,
    build_review_refinement_task,
)
from aiecs.domain.community.collaborative_workflow import (
    REVIEW_REFINEMENT_PHASE_CONFIG,
    CollaborativeWorkflowEngine,
)


def _h1_goal() -> AgentGoal:
    criteria = [
        AcceptanceCriterion(criterion_id=f"c{i}", description=f"requirement {i}")
        for i in range(5)
    ]
    return AgentGoal(description="H1 report", success_criteria=criteria)


def _context() -> VerificationContext:
    return VerificationContext(
        deliverable_refs=["output.md"],
        gate_issues=[],
        registry_snapshot={},
        goal_snapshot={"goal_id": "g1", "description": "H1 report"},
    )


def _task_and_result() -> tuple[dict, dict]:
    return (
        {"task_id": "g1", "description": "H1 report"},
        {"output": "contains alpha content", "final_response": "contains alpha content"},
    )


@pytest.mark.unit
class TestIsH1Goal:
    def test_five_criteria_is_h1(self) -> None:
        assert is_h1_goal(_h1_goal()) is True

    def test_delivery_kind_report_is_h1(self) -> None:
        goal = AgentGoal(description="report task", metadata={"delivery_kind": "report"})
        assert is_h1_goal(goal) is True

    def test_quick_goal_not_h1(self) -> None:
        goal = AgentGoal(
            description="quick",
            success_criteria=[AcceptanceCriterion(criterion_id="c1", description="one")],
        )
        assert is_h1_goal(goal) is False


@pytest.mark.unit
class TestReviewRefinementTemplate:
    def test_template_sourced_from_cwe_engine(self) -> None:
        assert REVIEW_REFINEMENT_TEMPLATE["phase"] == "review_refinement"
        assert REVIEW_REFINEMENT_TEMPLATE["roles"] == REVIEW_REFINEMENT_PHASE_CONFIG["roles"]
        assert REVIEW_REFINEMENT_TEMPLATE["sequential"] is True

    def test_build_task_includes_role_and_phase_contract(self) -> None:
        task = build_review_refinement_task(
            role="fact",
            task={"task_id": "t1", "description": "d"},
            result={"output": "hello"},
            criteria=[AcceptanceCriterion(criterion_id="c1", description="hello")],
        )
        assert task["role"] == "fact"
        assert task["phase"] == "review_refinement"
        assert task["review_contract"] == "gvr_cwe_review_refinement_v1"


@pytest.mark.unit
class TestCollaborativeWorkflowEngineReviewRefinement:
    @pytest.mark.asyncio
    async def test_engine_runs_fact_then_style_sequentially(self) -> None:
        call_order: list[str] = []

        async def spawn_verifier(review_task: dict) -> dict:
            call_order.append(review_task["role"])
            passed = review_task["role"] == "fact"
            return {
                "passed": passed,
                "kind": "PASS" if passed else "FAIL",
                "feedback": f"{review_task['role']} done",
                "failed_criteria": [] if passed else ["c1"],
            }

        engine = CollaborativeWorkflowEngine()
        task, result = _task_and_result()
        criteria = [AcceptanceCriterion(criterion_id="c1", description="alpha")]

        payload = await engine.review_refinement(
            task=task,
            result=result,
            criteria=criteria,
            spawn_verifier=spawn_verifier,
        )

        assert call_order == ["fact", "style"]
        assert payload["phase"]["phase_name"] == "review_refinement"
        assert len(payload["role_reviews"]) == 2
        assert payload["verdict"]["passed"] is False
        assert payload["verdict"]["kind"] == "FAIL"


@pytest.mark.unit
class TestCweVerifier:
    @pytest.mark.asyncio
    async def test_disabled_returns_na(self) -> None:
        verifier = CweVerifier(CweVerifierPolicy(enabled=False))
        verdict = await verifier.verify(
            goal=_h1_goal(),
            result={"output": "x"},
            criteria=[],
            context=_context(),
        )
        assert verdict.kind == "NA"

    @pytest.mark.asyncio
    async def test_non_h1_returns_na_when_enabled(self) -> None:
        verifier = CweVerifier(CweVerifierPolicy(enabled=True))
        goal = AgentGoal(description="quick")
        verdict = await verifier.verify(
            goal=goal,
            result={"output": "x"},
            criteria=[],
            context=_context(),
        )
        assert verdict.kind == "NA"

    @pytest.mark.asyncio
    async def test_enabled_without_spawn_verifier_fails_not_silent_pass(self) -> None:
        verifier = CweVerifier(CweVerifierPolicy(enabled=True))
        verdict = await verifier.verify(
            goal=_h1_goal(),
            result={"output": "x"},
            criteria=[],
            context=_context(),
        )
        assert verdict.passed is False
        assert verdict.kind == "FAIL"
        assert "spawn_verifier" in verdict.feedback

    @pytest.mark.asyncio
    async def test_delegates_to_collaborative_workflow_engine(self) -> None:
        engine = MagicMock(spec=CollaborativeWorkflowEngine)
        engine.review_refinement = AsyncMock(
            return_value={
                "verdict": {"passed": True, "kind": "PASS", "feedback": "ok"},
                "role_reviews": [],
                "phase": {},
            }
        )

        async def spawn_verifier(_review_task: dict) -> dict:
            return {"passed": True, "kind": "PASS", "feedback": "ok"}

        verifier = CweVerifier(
            CweVerifierPolicy(enabled=True),
            engine=engine,
            spawn_verifier=spawn_verifier,
        )
        criteria = [AcceptanceCriterion(criterion_id="c1", description="alpha")]
        verdict = await verifier.verify(
            goal=_h1_goal(),
            result={"output": "alpha"},
            criteria=criteria,
            context=_context(),
        )

        engine.review_refinement.assert_awaited_once()
        assert verdict.passed is True
        call_kwargs = engine.review_refinement.await_args.kwargs
        assert call_kwargs["spawn_verifier"] is spawn_verifier

    @pytest.mark.asyncio
    async def test_cwe_path_matches_dual_spawn_subagent_equivalence(self) -> None:
        """A-11 acceptance: CWE engine path ≡ sequential dual spawn_subagent(verifier)."""
        criteria = [AcceptanceCriterion(criterion_id="c1", description="alpha")]
        task, result = _task_and_result()
        spawn_calls: list[str] = []

        async def spawn_verifier(review_task: dict) -> dict:
            spawn_calls.append(review_task["role"])
            if review_task["role"] == "fact":
                return {"passed": True, "kind": "PASS", "feedback": "fact ok"}
            return {
                "passed": False,
                "kind": "FAIL",
                "feedback": "style gap",
                "failed_criteria": ["c1"],
            }

        engine = CollaborativeWorkflowEngine()
        cwe = CweVerifier(
            CweVerifierPolicy(enabled=True),
            engine=engine,
            spawn_verifier=spawn_verifier,
        )
        cwe_verdict = await cwe.verify(
            goal=_h1_goal(),
            result=result,
            criteria=criteria,
            context=_context(),
        )

        dual_verdict = await run_dual_spawn_verifier_path(
            task=task,
            result=result,
            criteria=criteria,
            spawn_verifier=spawn_verifier,
        )

        assert spawn_calls == ["fact", "style", "fact", "style"]
        assert cwe_verdict.passed == dual_verdict.passed
        assert cwe_verdict.kind == dual_verdict.kind
        assert cwe_verdict.failed_criteria == dual_verdict.failed_criteria

    @pytest.mark.asyncio
    async def test_enabled_off_build_returns_none(self) -> None:
        assert build_cwe_verifier_from_config(None) is None
        assert build_cwe_verifier_from_config({"enabled": False}) is None

        async def spawn_verifier(_: dict) -> dict:
            return {"passed": True, "kind": "PASS"}

        built = build_cwe_verifier_from_config(
            {"enabled": True},
            spawn_verifier=spawn_verifier,
        )
        assert built is not None
        assert built.engine is not None
