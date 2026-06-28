"""
Phase H2 — loop and task boundary hook wiring tests (§3.6).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiecs.domain.agent import AgentConfiguration, HybridAgent, LLMAgent
from aiecs.domain.agent.plugins.context import AgentPluginContext
from aiecs.domain.agent.plugins.hooks.events import AgentHookEvent
from aiecs.domain.agent.plugins.hooks.task_boundary import (
    canonical_stop_reason,
    prepare_hook_task_entry,
)
from aiecs.domain.agent.plugins.models import PluginConfig
from aiecs.domain.agent.tool_loop_core import ToolLoopIterationOutcome, ToolLoopRunState
from aiecs.llm import BaseLLMClient, LLMMessage, LLMResponse


class _SeqLLM(BaseLLMClient):
    def __init__(self, responses: list[str]) -> None:
        super().__init__(provider_name="openai")
        self._responses = responses
        self._idx = 0
        self.call_count = 0

    async def generate_text(self, messages, **kwargs) -> LLMResponse:
        self.call_count += 1
        content = self._responses[min(self._idx, len(self._responses) - 1)]
        self._idx += 1
        return LLMResponse(content=content, provider="openai", model="m", tokens_used=1)

    async def stream_text(self, *args, **kwargs):
        from aiecs.llm.clients.openai_compatible_mixin import StreamChunk

        content = self._responses[min(self._idx, len(self._responses) - 1)]
        self._idx += 1
        yield StreamChunk(type="token", content=content)

    async def close(self) -> None:
        return None


@pytest.mark.unit
class TestH2PayloadHelpers:
    def test_canonical_stop_reason_final(self) -> None:
        outcome = ToolLoopIterationOutcome(
            kind="final",
            result={"final_response": "done"},
        )
        assert canonical_stop_reason(outcome) == "tool_uses_empty"

    def test_canonical_stop_reason_stop_match(self) -> None:
        outcome = ToolLoopIterationOutcome(
            kind="stop_match",
            result={"final_response": "x", "stop_reason": "tool_result_matched"},
        )
        assert canonical_stop_reason(outcome) == "tool_result_matched"


@pytest.mark.unit
class TestH5TaskEntry:
    @pytest.mark.asyncio
    async def test_h5_fires_before_pre_task(self, mock_agent) -> None:
        from aiecs.domain.agent.plugins.builtin.hook_plugin import HookPlugin

        hook = HookPlugin(
            PluginConfig(
                name="hook",
                enabled=True,
                options={"inline_hooks": {"user_prompt_submit": [{"type": "prompt", "prompt": "audit"}]}},
            ),
            mock_agent,
        )
        await hook.on_agent_init(
            AgentPluginContext(agent=mock_agent, task={}, context={}, task_description="t")
        )

        agent = HybridAgent(
            agent_id="h5-agent",
            name="H5",
            tools=[],
            config=AgentConfiguration(
                llm_model="m",
                plugins=[
                    PluginConfig(name="memory", enabled=False),
                    PluginConfig(name="hook", enabled=True),
                ],
            ),
            llm_client=_SeqLLM(["answer"]),
        )
        await agent.initialize()

        dispatch_spy = AsyncMock(return_value=MagicMock(blocked=False, results=[]))
        phase_order: list[str] = []

        original_run = agent._plugin_manager.run_phase

        async def _track_phase(phase, **kwargs):
            phase_order.append(str(phase))
            return await original_run(phase, **kwargs)

        with patch(
            "aiecs.domain.agent.plugins.hooks.task_boundary.dispatch_agent_hook",
            dispatch_spy,
        ):
            agent._plugin_manager.run_phase = _track_phase  # type: ignore[method-assign]
            await agent.execute_task({"description": "hello task"}, {})

        assert dispatch_spy.await_count >= 1
        first_event = dispatch_spy.await_args_list[0].args[1]
        assert first_event == AgentHookEvent.USER_PROMPT_SUBMIT
        assert any("pre_task" in p.lower() for p in phase_order)
        assert dispatch_spy.await_args_list[0].args[2]["prompt"] == "hello task"


@pytest.mark.unit
class TestH6StopHook:
    @pytest.mark.asyncio
    async def test_h6_fires_once_on_non_streaming_final(self) -> None:
        agent = HybridAgent(
            agent_id="h6-agent",
            name="H6",
            tools=[],
            config=AgentConfiguration(
                llm_model="m",
                plugins=[
                    PluginConfig(name="memory", enabled=False),
                    PluginConfig(name="hook", enabled=True, options={"inline_hooks": {"stop": []}}),
                ],
            ),
            llm_client=_SeqLLM(["final answer"]),
        )
        await agent.initialize()

        dispatch_spy = AsyncMock(return_value=MagicMock(blocked=False, results=[]))
        with patch(
            "aiecs.domain.agent.plugins.hooks.task_boundary.dispatch_agent_hook",
            dispatch_spy,
        ):
            await agent.execute_task({"description": "task"}, {})

        stop_calls = [
            c for c in dispatch_spy.await_args_list if c.args[1] == AgentHookEvent.STOP
        ]
        assert len(stop_calls) == 1
        assert stop_calls[0].args[2]["stop_reason"] == "tool_uses_empty"

    @pytest.mark.asyncio
    async def test_h6_skipped_when_dawp_drained(self) -> None:
        """H6-02: DAWP continue → H6 count 0 on that iteration."""
        _FIXTURE_PATH = str(
            Path(__file__).parents[5] / "fixtures" / "dawp" / "trigger_inline.dawp.md"
        )
        _TRIGGER = "<START_INLINE_REVIEW>"
        _PROMPT_MARKER = "<INLINE_STEP_DONE>"
        _DAWP_MARKER = "<INLINE_REVIEW_COMPLETE>"

        config = AgentConfiguration(
            llm_model="m",
            plugins=[
                PluginConfig(name="memory", enabled=False),
                PluginConfig(name="skill", enabled=False),
                PluginConfig(
                    name="dawp",
                    enabled=True,
                    options={"document_path": _FIXTURE_PATH},
                ),
                PluginConfig(name="hook", enabled=True),
            ],
        )
        mock_tool = MagicMock()
        mock_tool.name = "mock_tool"
        mock_tool.run_async = AsyncMock(return_value="ok")

        responses = [
            f"Trigger.\n{_TRIGGER}",
            f"Evidence.\n{_PROMPT_MARKER}",
            f"Done.\n{_DAWP_MARKER}",
            "Main final answer.",
        ]
        with patch("aiecs.tools.get_tool", return_value=mock_tool):
            agent = HybridAgent(
                agent_id="h6-dawp",
                name="H6 DAWP",
                config=config,
                llm_client=_SeqLLM(responses),
                tools=["mock_tool"],
            )
            await agent.initialize()

        dispatch_spy = AsyncMock(return_value=MagicMock(blocked=False, results=[]))
        with patch(
            "aiecs.domain.agent.plugins.hooks.task_boundary.dispatch_agent_hook",
            dispatch_spy,
        ):
            result = await agent.execute_task({"description": "task"}, {})

        stop_calls = [
            c for c in dispatch_spy.await_args_list if c.args[1] == AgentHookEvent.STOP
        ]
        assert len(stop_calls) == 1
        assert result.get("output") == "Main final answer." or result.get("final_response") == "Main final answer."


@pytest.mark.unit
class TestH13BuildMessages:
    @pytest.mark.asyncio
    async def test_h13_fires_after_build_messages_phase(self, mock_agent) -> None:
        agent = LLMAgent(
            agent_id="h13-agent",
            name="H13",
            config=AgentConfiguration(
                llm_model="m",
                plugins=[
                    PluginConfig(name="memory", enabled=False),
                    PluginConfig(name="hook", enabled=True),
                ],
            ),
            llm_client=_SeqLLM(["hello"]),
        )
        await agent.initialize()

        dispatch_spy = AsyncMock(return_value=MagicMock(blocked=False, results=[]))
        with patch(
            "aiecs.domain.agent.plugins.hooks.task_boundary.dispatch_agent_hook",
            dispatch_spy,
        ):
            await agent.execute_task({"description": "user task"}, {})

        build_calls = [
            c for c in dispatch_spy.await_args_list if c.args[1] == AgentHookEvent.BUILD_MESSAGES
        ]
        assert len(build_calls) == 1
        assert build_calls[0].args[2]["message_count"] >= 1


@pytest.mark.unit
class TestH2RegistryRebuild:
    @pytest.mark.asyncio
    async def test_prepare_hook_task_entry_rebuilds_registry(self, mock_agent) -> None:
        agent = HybridAgent(
            agent_id="rebuild-agent",
            name="Rebuild",
            tools=[],
            config=AgentConfiguration(
                llm_model="m",
                plugins=[
                    PluginConfig(
                        name="hook",
                        enabled=True,
                        options={"inline_hooks": {"stop": []}},
                    ),
                ],
            ),
            llm_client=_SeqLLM(["x"]),
        )
        await agent.initialize()
        hook = agent._plugin_manager.get_plugin("hook")  # type: ignore[union-attr]
        assert hook is not None
        hook._registry = None  # type: ignore[attr-defined]
        ctx = agent._make_plugin_context(
            task={"description": "t"},
            context={"hook_sources": []},
            task_description="t",
        )
        prepare_hook_task_entry(ctx, task_description="t")
        assert hook.registry is not None  # type: ignore[attr-defined]


@pytest.mark.unit
@pytest.mark.asyncio
class TestDawpNs01:
    """DAWP-NS-01: non-streaming continues after on_iteration_end drain (HookPlugin optional)."""

    async def test_non_streaming_requires_two_iterations_after_dawp_drain(self) -> None:
        _FIXTURE_PATH = str(
            Path(__file__).parents[5] / "fixtures" / "dawp" / "trigger_inline.dawp.md"
        )
        _TRIGGER = "<START_INLINE_REVIEW>"
        _PROMPT_MARKER = "<INLINE_STEP_DONE>"
        _DAWP_MARKER = "<INLINE_REVIEW_COMPLETE>"

        config = AgentConfiguration(
            llm_model="m",
            plugins=[
                PluginConfig(name="memory", enabled=False),
                PluginConfig(name="skill", enabled=False),
                PluginConfig(
                    name="dawp",
                    enabled=True,
                    options={"document_path": _FIXTURE_PATH},
                ),
            ],
        )
        mock_tool = MagicMock()
        mock_tool.name = "mock_tool"
        mock_tool.run_async = AsyncMock(return_value="ok")

        llm = _SeqLLM(
            [
                f"Trigger.\n{_TRIGGER}",
                f"Evidence.\n{_PROMPT_MARKER}",
                f"Done.\n{_DAWP_MARKER}",
                "Main final answer.",
            ]
        )
        with patch("aiecs.tools.get_tool", return_value=mock_tool):
            agent = HybridAgent(
                agent_id="dawp-ns-01",
                name="DAWP NS",
                config=config,
                llm_client=llm,
                tools=["mock_tool"],
            )
            await agent.initialize()

        result = await agent.execute_task({"description": "task"}, {})

        assert llm.call_count >= 2, f"Expected ≥2 LLM calls after DAWP drain, got {llm.call_count}"
        output = result.get("output") or result.get("final_response")
        assert output == "Main final answer."
