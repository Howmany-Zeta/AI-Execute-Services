"""
GVR integration helpers — policy priority unit tests.

Full HybridAgent FC-loop verify-fix coverage lives in
``test_hybrid_agent_gvr_fc_loop.py`` (real ``_run_tool_loop_with_iteration_hooks``
pre-exit wiring).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiecs.domain.agent.verification.gates.registry import build_gate_registry_from_config
from aiecs.domain.agent.verification.policy_models import VerificationPolicy
from aiecs.domain.agent.verification.policy_runner import run_gvr_pre_exit
from aiecs.llm import LLMMessage


def _bad_output() -> dict:
    return {"output": "unstructured draft", "final_response": "unstructured draft"}


@pytest.mark.unit
class TestGvrPolicyPriority:
    @pytest.mark.asyncio
    async def test_run_gvr_pre_exit_policy_over_hook_priority(self) -> None:
        """A-2 verification_policy takes priority over A-8 hook path."""
        agent = MagicMock()
        agent._config.verification_policy = VerificationPolicy(
            enabled=True,
            registered_verifiers=["spec_gate"],
        )
        agent._verifiers = []
        agent._gate_registry = build_gate_registry_from_config(["spec_gate"])
        agent._current_goal_for_gvr = lambda: None

        plugin_ctx = MagicMock()
        plugin_ctx.plugin_state = {}
        messages = [LLMMessage(role="user", content="task")]

        with patch(
            "aiecs.domain.agent.verification.policy_runner.run_verification_policy",
            new_callable=AsyncMock,
        ) as mock_policy:
            from aiecs.domain.agent.verification.policy_runner import PolicyRunResult
            from aiecs.domain.agent.verification.models import Verdict

            mock_policy.return_value = PolicyRunResult(
                verdict=Verdict(passed=False, kind="FAIL", feedback="policy"),
                continued_loop=True,
            )
            continued = await run_gvr_pre_exit(
                agent=agent,
                plugin_ctx=plugin_ctx,
                messages=messages,
                loop_result=_bad_output(),
                trigger="on_task_completed",
                iteration=0,
            )

        assert continued is True
        mock_policy.assert_awaited_once()
