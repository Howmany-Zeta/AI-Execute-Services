"""
Unit tests for execute_with_recovery stabilization (A-9).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from aiecs.domain.agent.exceptions import TaskExecutionError, VerificationExhausted
from aiecs.domain.agent.models import RecoveryResult, RecoveryStrategy
from aiecs.domain.agent.tool_agent import ToolAgent
from aiecs.domain.agent.models import AgentConfiguration
from aiecs.domain.agent.verification.models import Verdict


@pytest.mark.unit
class TestExecuteWithRecovery:
    @pytest.mark.asyncio
    async def test_structured_success(self) -> None:
        agent = ToolAgent(
            agent_id="a1",
            name="A",
            description="d",
            config=AgentConfiguration(name="A", description="d"),
            tools={},
        )
        agent.execute_task = AsyncMock(return_value={"success": True, "output": "ok"})

        outcome = await agent.execute_with_recovery(
            {"description": "t"},
            {},
            strategies=[RecoveryStrategy.RETRY],
            structured=True,
        )
        assert isinstance(outcome, RecoveryResult)
        assert outcome.success is True
        assert outcome.result is not None

    @pytest.mark.asyncio
    async def test_abort_propagates_verification_exhausted(self) -> None:
        agent = ToolAgent(
            agent_id="a1",
            name="A",
            description="d",
            config=AgentConfiguration(name="A", description="d"),
            tools={},
        )
        verdict = Verdict(passed=False, kind="FAIL", feedback="exhausted")
        agent.execute_task = AsyncMock(
            side_effect=VerificationExhausted(verdict),
        )

        with pytest.raises(VerificationExhausted):
            await agent.execute_with_recovery(
                {"description": "t"},
                {},
                strategies=[RecoveryStrategy.RETRY, RecoveryStrategy.ABORT],
            )

    @pytest.mark.asyncio
    async def test_structured_verification_exhausted_escalation(self) -> None:
        agent = ToolAgent(
            agent_id="a1",
            name="A",
            description="d",
            config=AgentConfiguration(name="A", description="d"),
            tools={},
        )
        verdict = Verdict(passed=False, kind="FAIL", feedback="exhausted")
        agent.execute_task = AsyncMock(
            side_effect=VerificationExhausted(verdict),
        )

        outcome = await agent.execute_with_recovery(
            {"description": "t"},
            {},
            strategies=[RecoveryStrategy.RETRY, RecoveryStrategy.ABORT],
            structured=True,
        )
        assert isinstance(outcome, RecoveryResult)
        assert outcome.success is False
        assert outcome.escalation_reason == "verification_exhausted"
        assert outcome.verdict is not None

    @pytest.mark.asyncio
    async def test_default_execute_unchanged_without_recovery(self) -> None:
        agent = ToolAgent(
            agent_id="a1",
            name="A",
            description="d",
            config=AgentConfiguration(name="A", description="d"),
            tools={},
        )
        agent.execute_task = AsyncMock(return_value={"success": True, "output": "direct"})

        result = await agent.execute_task({"description": "t"}, {})
        assert result["output"] == "direct"
        agent.execute_task.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_recovery_streaming_yields_recovery_result(self) -> None:
        agent = ToolAgent(
            agent_id="a1",
            name="A",
            description="d",
            config=AgentConfiguration(name="A", description="d"),
            tools={},
        )

        async def _stream(task, context):
            yield {"type": "token", "content": "x"}
            yield {"type": "result", "success": True, "output": "done"}

        agent.execute_task_streaming = _stream

        events = []
        async for event in agent.execute_with_recovery_streaming(
            {"description": "t"},
            {},
            strategies=[RecoveryStrategy.RETRY],
        ):
            events.append(event)

        assert events[-1]["type"] == "recovery_result"
        assert events[-1]["recovery"]["success"] is True
