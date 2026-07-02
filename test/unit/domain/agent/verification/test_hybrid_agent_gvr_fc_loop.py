"""
HybridAgent FC-loop GVR integration (A-4 + A-8 + A-2).

Exercises real pre-exit wiring in ``_run_tool_loop_with_iteration_hooks`` at
``HybridAgent._handle_pre_exit_gvr`` — only ``_run_tool_loop_core_iteration`` is
stubbed to simulate LLM final responses across iterations.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from aiecs.domain.agent.hybrid_agent import HybridAgent
from aiecs.domain.agent.models import AgentConfiguration
from aiecs.domain.agent.plugins.context import AgentPluginContext
from aiecs.domain.agent.plugins.models import PluginConfig
from aiecs.domain.agent.tool_loop_core import ToolLoopIterationOutcome, ToolLoopRunState
from aiecs.llm import BaseLLMClient, LLMMessage, LLMResponse


def _structured_output() -> dict[str, Any]:
    text = "GIVEN context\nWHEN action\nTHEN outcome"
    return {
        "success": True,
        "output": text,
        "final_response": text,
        "steps": [],
        "tool_calls_count": 0,
        "total_tokens": 0,
    }


def _bad_output() -> dict[str, Any]:
    return {
        "success": True,
        "output": "unstructured draft",
        "final_response": "unstructured draft",
        "steps": [],
        "tool_calls_count": 0,
        "total_tokens": 0,
    }


class _MockLLM(BaseLLMClient):
    def __init__(self) -> None:
        super().__init__(provider_name="openai")

    async def generate_text(self, messages: list[LLMMessage], **kwargs: Any) -> LLMResponse:
        return LLMResponse(content="unused", provider="openai", model="test", tokens_used=0)

    async def stream_text(self, *args: Any, **kwargs: Any):
        yield "unused"

    async def close(self) -> None:
        pass


async def _make_agent(
    *,
    verification_policy: dict[str, Any] | None = None,
    deterministic_gates: list[str] | None = None,
    max_iterations: int = 5,
) -> HybridAgent:
    config = AgentConfiguration(
        goal="gvr fc loop test",
        llm_model="test-model",
        plugins=[
            PluginConfig(name="memory", enabled=False),
            PluginConfig(name="skill", enabled=False),
        ],
        verification_policy=verification_policy,
        deterministic_gates=deterministic_gates,
    )
    agent = HybridAgent(
        agent_id="gvr-fc-loop",
        name="GVR FC Loop",
        llm_client=_MockLLM(),
        tools=[],
        config=config,
        max_iterations=max_iterations,
    )
    await agent.initialize()
    return agent


def _final_outcome(payload: dict[str, Any], iteration: int) -> ToolLoopIterationOutcome:
    body = dict(payload)
    body.setdefault("iterations", iteration + 1)
    return ToolLoopIterationOutcome(kind="final", result=body)


@pytest.mark.unit
class TestHybridAgentGvrFcLoop:
    @pytest.mark.asyncio
    async def test_verification_policy_spec_gate_fail_then_pass_in_fc_loop(self) -> None:
        """A-2 policy + A-4 SpecGate via real ``_run_tool_loop_with_iteration_hooks``."""
        agent = await _make_agent(
            verification_policy={
                "enabled": True,
                "registered_verifiers": ["spec_gate"],
                "max_refines_per_goal": 2,
                "blocking": True,
            },
        )
        plugin_ctx = agent._make_plugin_context(
            task={"task_id": "t1", "description": "spec task"},
            context={},
            task_description="spec task",
        )
        messages = [LLMMessage(role="user", content="spec task")]
        core_calls: list[int] = []
        pre_exit_calls: list[int] = []
        original_pre_exit = agent._handle_pre_exit_gvr

        async def stub_core_iteration(
            msgs: list[LLMMessage],
            context: dict[str, Any],
            iteration: int,
            state: ToolLoopRunState,
            plugin_ctx: AgentPluginContext | None = None,
        ) -> ToolLoopIterationOutcome:
            core_calls.append(iteration)
            payload = _bad_output() if iteration == 0 else _structured_output()
            return _final_outcome(payload, iteration)

        async def spy_pre_exit(*args: Any, **kwargs: Any) -> bool:
            pre_exit_calls.append(kwargs.get("iteration", args[4] if len(args) > 4 else -1))
            return await original_pre_exit(*args, **kwargs)

        with patch.object(agent, "_run_tool_loop_core_iteration", side_effect=stub_core_iteration):
            with patch.object(agent, "_handle_pre_exit_gvr", side_effect=spy_pre_exit):
                result = await agent._run_tool_loop_with_iteration_hooks(
                    messages,
                    {},
                    plugin_ctx=plugin_ctx,
                )

        assert core_calls == [0, 1]
        assert pre_exit_calls == [0, 1]
        assert result["success"] is True
        assert "GIVEN" in result["final_response"]
        assert any(
            msg.role == "user" and msg.content and "GVR verification" in msg.content
            for msg in messages
        )
        events = plugin_ctx.plugin_state.get("gvr.verification_events", [])
        assert any(e.get("event") == "refine" for e in events)
        assert any(e.get("event") == "verdict" and e.get("passed") is True for e in events)

    @pytest.mark.asyncio
    async def test_gate_fail_pre_exit_continues_fc_loop_then_pass(self) -> None:
        """A-4 + A-8 gate pre-exit (policy off) through the same FC-loop wiring."""
        agent = await _make_agent(
            verification_policy={"enabled": False},
            deterministic_gates=["spec_gate"],
        )
        plugin_ctx = agent._make_plugin_context(
            task={"task_id": "t2", "description": "gate task"},
            context={},
            task_description="gate task",
        )
        messages = [LLMMessage(role="user", content="gate task")]

        async def stub_core_iteration(
            msgs: list[LLMMessage],
            context: dict[str, Any],
            iteration: int,
            state: ToolLoopRunState,
            plugin_ctx: AgentPluginContext | None = None,
        ) -> ToolLoopIterationOutcome:
            payload = _bad_output() if iteration == 0 else _structured_output()
            return _final_outcome(payload, iteration)

        with patch.object(agent, "_run_tool_loop_core_iteration", side_effect=stub_core_iteration):
            with patch(
                "aiecs.domain.agent.plugins.hooks.gvr_blocking.dispatch_pre_exit_task_completed_hook",
                new_callable=AsyncMock,
            ) as mock_hook:
                from aiecs.domain.agent.plugins.hooks.types import AggregatedHookResult

                mock_hook.return_value = AggregatedHookResult.empty()
                result = await agent._run_tool_loop_with_iteration_hooks(
                    messages,
                    {},
                    plugin_ctx=plugin_ctx,
                )

        assert result["success"] is True
        assert "THEN" in result["final_response"]
        assert len(messages) == 2
        assert "GVR verification" in (messages[-1].content or "")
        assert mock_hook.await_count == 2

    @pytest.mark.asyncio
    async def test_pre_exit_gvr_not_called_when_plugin_ctx_none(self) -> None:
        """Regression: pre-exit path requires plugin_ctx (rc4 parity when absent)."""
        agent = await _make_agent(
            verification_policy={"enabled": True, "registered_verifiers": ["spec_gate"]},
        )
        messages = [LLMMessage(role="user", content="task")]
        pre_exit_mock = AsyncMock(return_value=False)
        agent._handle_pre_exit_gvr = pre_exit_mock  # type: ignore[method-assign]

        async def stub_core(_m, _c, iteration, _s, plugin_ctx=None):
            return _final_outcome(_bad_output(), iteration)

        with patch.object(agent, "_run_tool_loop_core_iteration", side_effect=stub_core):
            result = await agent._run_tool_loop_with_iteration_hooks(messages, {}, plugin_ctx=None)

        pre_exit_mock.assert_not_awaited()
        assert "final_response" in result


@pytest.mark.unit
class TestHybridAgentGvrStreamingFcLoop:
    """Streaming FC-loop GVR wiring via ``_tool_loop_streaming_with_plugins`` (1068–1114)."""

    @staticmethod
    async def _collect_stream_events(
        agent: HybridAgent,
        plugin_ctx: AgentPluginContext,
        messages: list[LLMMessage],
    ) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        async for event in agent._tool_loop_streaming_with_plugins(
            "gvr streaming task",
            {},
            plugin_ctx,
            initial_messages=messages,
        ):
            events.append(event)
        return events

    @pytest.mark.asyncio
    async def test_verification_policy_spec_gate_fail_then_pass_streaming(self) -> None:
        agent = await _make_agent(
            verification_policy={
                "enabled": True,
                "registered_verifiers": ["spec_gate"],
                "max_refines_per_goal": 2,
                "blocking": True,
            },
        )
        plugin_ctx = agent._make_plugin_context(
            task={"task_id": "t-stream-1", "description": "spec task"},
            context={},
            task_description="spec task",
        )
        messages = [LLMMessage(role="user", content="spec task")]
        core_calls: list[int] = []
        pre_exit_calls: list[int] = []
        original_pre_exit = agent._handle_pre_exit_gvr

        async def stub_core_streaming(
            msgs: list[LLMMessage],
            context: dict[str, Any],
            iteration: int,
            state: ToolLoopRunState,
            plugin_ctx: AgentPluginContext | None = None,
        ):
            core_calls.append(iteration)
            payload = _bad_output() if iteration == 0 else _structured_output()
            state.last_outcome = _final_outcome(payload, iteration)
            yield {"type": "token", "content": "chunk"}

        async def spy_pre_exit(*args: Any, **kwargs: Any) -> bool:
            pre_exit_calls.append(kwargs.get("iteration", args[4] if len(args) > 4 else -1))
            return await original_pre_exit(*args, **kwargs)

        from aiecs.domain.agent.verification import policy_runner

        with patch.object(agent, "_run_tool_loop_core_iteration_streaming", side_effect=stub_core_streaming):
            with patch.object(agent, "_handle_pre_exit_gvr", side_effect=spy_pre_exit):
                with patch.object(
                    policy_runner,
                    "inject_blocking_user_message",
                    wraps=policy_runner.inject_blocking_user_message,
                ) as mock_inject:
                    events = await self._collect_stream_events(agent, plugin_ctx, messages)

        result_events = [e for e in events if e.get("type") == "result"]
        assert core_calls == [0, 1]
        assert pre_exit_calls == [0, 1]
        assert mock_inject.call_count >= 1
        assert len(result_events) == 1
        assert result_events[0]["success"] is True
        assert "GIVEN" in str(result_events[0].get("final_response", ""))
        gvr_events = plugin_ctx.plugin_state.get("gvr.verification_events", [])
        assert any(e.get("event") == "refine" for e in gvr_events)

    @pytest.mark.asyncio
    async def test_gate_fail_pre_exit_continues_streaming_fc_loop_then_pass(self) -> None:
        agent = await _make_agent(
            verification_policy={"enabled": False},
            deterministic_gates=["spec_gate"],
        )
        plugin_ctx = agent._make_plugin_context(
            task={"task_id": "t-stream-2", "description": "gate task"},
            context={},
            task_description="gate task",
        )
        messages = [LLMMessage(role="user", content="gate task")]

        async def stub_core_streaming(
            msgs: list[LLMMessage],
            context: dict[str, Any],
            iteration: int,
            state: ToolLoopRunState,
            plugin_ctx: AgentPluginContext | None = None,
        ):
            payload = _bad_output() if iteration == 0 else _structured_output()
            state.last_outcome = _final_outcome(payload, iteration)
            yield {"type": "token", "content": "chunk"}

        with patch.object(agent, "_run_tool_loop_core_iteration_streaming", side_effect=stub_core_streaming):
            with patch(
                "aiecs.domain.agent.plugins.hooks.gvr_blocking.dispatch_pre_exit_task_completed_hook",
                new_callable=AsyncMock,
            ) as mock_hook:
                from aiecs.domain.agent.plugins.hooks import gvr_blocking
                from aiecs.domain.agent.plugins.hooks.types import AggregatedHookResult

                mock_hook.return_value = AggregatedHookResult.empty()
                with patch.object(
                    gvr_blocking,
                    "inject_blocking_user_message",
                    wraps=gvr_blocking.inject_blocking_user_message,
                ) as mock_inject:
                    events = await self._collect_stream_events(agent, plugin_ctx, messages)

        result_events = [e for e in events if e.get("type") == "result"]
        assert len(result_events) == 1
        assert "THEN" in str(result_events[0].get("final_response", ""))
        assert mock_inject.call_count >= 1
        assert mock_hook.await_count == 2
