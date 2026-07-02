"""
HybridAgent.verify hook tests (A-1).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from aiecs.domain.agent.hybrid_agent import HybridAgent
from aiecs.domain.agent.models import AgentConfiguration
from aiecs.domain.agent.verification.models import AcceptanceCriterion, Verdict, VerificationContext


class _MockVerifier:
    kind = "mock"

    def __init__(self, verdict: Verdict) -> None:
        self._verdict = verdict
        self.calls: list[dict[str, Any]] = []

    async def verify(
        self,
        *,
        goal: Any,
        result: dict[str, Any],
        criteria: list[AcceptanceCriterion],
        context: VerificationContext,
    ) -> Verdict:
        self.calls.append(
            {
                "goal": goal,
                "result": result,
                "criteria": criteria,
                "context": context,
            }
        )
        assert "system_prompt" not in context.model_dump()
        return self._verdict


@pytest.mark.unit
class TestHybridAgentVerify:
    @pytest.fixture
    def agent(self) -> HybridAgent:
        llm = MagicMock()
        llm.provider_name = "mock"
        return HybridAgent(
            agent_id="agent-verify",
            name="Verify Agent",
            llm_client=llm,
            tools=[],
            config=AgentConfiguration(),
        )

    @pytest.mark.asyncio
    async def test_verify_without_verifiers_returns_na(self, agent: HybridAgent) -> None:
        verdict = await agent.verify({"output": "ok"}, [])
        assert verdict.kind == "NA"
        assert verdict.passed is True

    @pytest.mark.asyncio
    async def test_verify_runs_registered_verifier(self, agent: HybridAgent) -> None:
        expected = Verdict(passed=True, kind="PASS", feedback="mock ok")
        mock = _MockVerifier(expected)
        agent.register_verifier(mock)
        criteria = [AcceptanceCriterion(criterion_id="c1", description="demo")]
        result = {"output": "demo content"}
        verdict = await agent.verify(result, criteria)
        assert verdict.kind == "PASS"
        assert len(mock.calls) == 1
        assert mock.calls[0]["criteria"][0].criterion_id == "c1"

    @pytest.mark.asyncio
    async def test_execute_task_streaming_unchanged_when_verify_not_called(self, agent: HybridAgent) -> None:
        """Task 2.8: verify hook is opt-in; streaming entrypoint still exists."""
        assert hasattr(agent, "execute_task_streaming")
        import inspect

        assert inspect.isasyncgenfunction(agent.execute_task_streaming)
