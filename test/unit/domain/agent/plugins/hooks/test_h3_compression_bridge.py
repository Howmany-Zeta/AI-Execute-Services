"""
Phase H3 — compression bridge and DAWP hook tests (§4.1).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiecs.domain.agent import AgentConfiguration, HybridAgent
from aiecs.domain.agent.plugins.context import AgentPluginContext
from aiecs.domain.agent.plugins.hooks.bridge_compression import (
    BridgedCompactHookExecutor,
    resolve_bridged_compression_hooks,
)
from aiecs.domain.agent.plugins.hooks.events import AgentHookEvent
from aiecs.domain.agent.plugins.hooks.loader import load_hooks_from_json, normalize_event_key
from aiecs.domain.agent.plugins.hooks.registry import AgentHookRegistry
from aiecs.domain.agent.plugins.models import PluginConfig
from aiecs.domain.agent.tool_loop_core import ToolLoopCompressionContext, maybe_compact_before_llm
from aiecs.domain.context.compression.hooks import HookExecutor, HookRegistry
from aiecs.domain.context.compression.policy import CompressionPolicy
from aiecs.domain.context.compression.state import AutoCompactState
from aiecs.domain.context.compression.types import PreCompactContext, PreCompactResult
from aiecs.llm import LLMMessage


@pytest.mark.unit
class TestCompressionBridge:
    @pytest.mark.asyncio
    async def test_pre_compact_block_from_agent_skips_compact(self, mock_agent) -> None:
        from aiecs.domain.agent.plugins.builtin.hook_plugin import HookPlugin

        hook = HookPlugin(
            PluginConfig(
                name="hook",
                enabled=True,
                options={
                    "inline_hooks": {
                        "pre_compact": [
                            {
                                "type": "prompt",
                                "prompt": "block",
                                "block_on_failure": True,
                            }
                        ]
                    }
                },
            ),
            mock_agent,
        )
        ctx = AgentPluginContext(agent=mock_agent, task={}, context={}, task_description="t")
        await hook.on_agent_init(ctx)

        compression_registry = HookRegistry()
        compression_hooks = HookExecutor(compression_registry)

        messages = [LLMMessage(role="user", content="word " * 400)] * 8
        compression_ctx = ToolLoopCompressionContext(
            enabled=True,
            policy=CompressionPolicy(
                auto_compact_threshold_tokens=100,
                preserve_recent=1,
                chain=("microcompact",),
            ),
            llm_client=AsyncMock(),
            auto_compact_state=AutoCompactState(),
            hooks=compression_hooks,
        )

        block_result = MagicMock(blocked=True, results=[], modified_output=None)

        with (
            patch.object(ctx, "get_plugin", return_value=hook),
            patch(
                "aiecs.domain.agent.plugins.hooks.bridge_compression.dispatch_agent_hook",
                AsyncMock(return_value=block_result),
            ) as dispatch_spy,
        ):
            result = await maybe_compact_before_llm(
                messages,
                compression_ctx=compression_ctx,
                plugin_ctx=ctx,
            )

        assert result == messages
        dispatch_spy.assert_awaited_once()
        assert dispatch_spy.await_args.args[1] == AgentHookEvent.PRE_COMPACT

    @pytest.mark.asyncio
    async def test_d10_pre_order_compression_before_agent(self, mock_agent) -> None:
        from aiecs.domain.agent.plugins.builtin.hook_plugin import HookPlugin

        order: list[str] = []
        compression_registry = HookRegistry()

        async def compression_pre(_ctx: PreCompactContext) -> PreCompactResult:
            order.append("compression")
            return PreCompactResult()

        compression_registry.register_pre(compression_pre)
        compression_hooks = HookExecutor(compression_registry)

        hook = HookPlugin(
            PluginConfig(
                name="hook",
                enabled=True,
                options={"inline_hooks": {"pre_compact": [{"type": "http", "url": "https://example.com/pre"}]}},
            ),
            mock_agent,
        )
        plugin_ctx = AgentPluginContext(agent=mock_agent, task={}, context={}, task_description="t")
        await hook.on_agent_init(plugin_ctx)

        async def agent_dispatch(_ctx, event, _payload, **kwargs):
            order.append("agent")
            return MagicMock(blocked=False, results=[], modified_output=None)

        with (
            patch.object(plugin_ctx, "get_plugin", return_value=hook),
            patch(
                "aiecs.domain.agent.plugins.hooks.bridge_compression.dispatch_agent_hook",
                side_effect=agent_dispatch,
            ),
        ):
            bridged = resolve_bridged_compression_hooks(compression_hooks, plugin_ctx)
            assert isinstance(bridged, BridgedCompactHookExecutor)
            await bridged.execute_pre_compact(
                PreCompactContext(messages=[LLMMessage(role="user", content="hi")], trigger="auto")
            )

        assert order == ["compression", "agent"]

    @pytest.mark.asyncio
    async def test_d10_post_order_agent_before_compression(self, mock_agent) -> None:
        from aiecs.domain.agent.plugins.builtin.hook_plugin import HookPlugin

        order: list[str] = []
        compression_registry = HookRegistry()

        async def compression_post(_ctx) -> None:
            order.append("compression")

        compression_registry.register_post(compression_post)
        compression_hooks = HookExecutor(compression_registry)

        hook = HookPlugin(
            PluginConfig(
                name="hook",
                enabled=True,
                options={"inline_hooks": {"post_compact": [{"type": "http", "url": "https://example.com/post"}]}},
            ),
            mock_agent,
        )
        plugin_ctx = AgentPluginContext(agent=mock_agent, task={}, context={}, task_description="t")
        await hook.on_agent_init(plugin_ctx)

        async def agent_dispatch(_ctx, event, _payload, **kwargs):
            order.append("agent")
            return MagicMock(blocked=False, results=[], modified_output=None)

        from aiecs.domain.context.compression.types import PostCompactContext

        with (
            patch.object(plugin_ctx, "get_plugin", return_value=hook),
            patch(
                "aiecs.domain.agent.plugins.hooks.bridge_compression.dispatch_agent_hook",
                side_effect=agent_dispatch,
            ),
        ):
            bridged = resolve_bridged_compression_hooks(compression_hooks, plugin_ctx)
            assert isinstance(bridged, BridgedCompactHookExecutor)
            await bridged.execute_post_compact(PostCompactContext(summary_text="summary"))

        assert order == ["agent", "compression"]

    @pytest.mark.asyncio
    async def test_append_instructions_merge_both_sources(self, mock_agent) -> None:
        from aiecs.domain.agent.plugins.builtin.hook_plugin import HookPlugin

        compression_registry = HookRegistry()

        async def compression_pre(_ctx: PreCompactContext) -> PreCompactResult:
            return PreCompactResult(append_instructions="from compression")

        compression_registry.register_pre(compression_pre)
        compression_hooks = HookExecutor(compression_registry)

        hook = HookPlugin(
            PluginConfig(
                name="hook",
                enabled=True,
                options={"inline_hooks": {"pre_compact": [{"type": "http", "url": "https://example.com/pre"}]}},
            ),
            mock_agent,
        )
        plugin_ctx = AgentPluginContext(agent=mock_agent, task={}, context={}, task_description="t")
        await hook.on_agent_init(plugin_ctx)

        with (
            patch.object(plugin_ctx, "get_plugin", return_value=hook),
            patch(
                "aiecs.domain.agent.plugins.hooks.bridge_compression.dispatch_agent_hook",
                AsyncMock(
                    return_value=MagicMock(
                        blocked=False,
                        results=[],
                        modified_output="from agent",
                    )
                ),
            ),
        ):
            bridged = resolve_bridged_compression_hooks(compression_hooks, plugin_ctx)
            assert isinstance(bridged, BridgedCompactHookExecutor)
            result = await bridged.execute_pre_compact(
                PreCompactContext(messages=[LLMMessage(role="user", content="hi")], trigger="auto")
            )

        assert result.append_instructions == "from compression\nfrom agent"


@pytest.mark.unit
class TestSubagentStopAlias:
    def test_subagent_stop_maps_to_dawp_run_end(self) -> None:
        from aiecs.domain.agent.plugins.hooks.loader import HookLoadOptions

        event = normalize_event_key("SubagentStop", options=HookLoadOptions())
        assert event == AgentHookEvent.DAWP_RUN_END

    def test_loader_registers_subagent_stop_under_dawp_run_end(self) -> None:
        registry = AgentHookRegistry()
        load_hooks_from_json(
            {
                "hooks": {
                    "SubagentStop": [
                        {"type": "http", "url": "https://example.com/stop"},
                    ]
                }
            },
            registry,
        )
        assert len(registry.get_hooks(AgentHookEvent.DAWP_RUN_END)) == 1


@pytest.mark.unit
class TestNestedDawpToolHooks:
    @pytest.mark.asyncio
    async def test_nested_false_by_default_skips_hooks(self, mock_agent) -> None:
        from aiecs.domain.agent.plugins.hooks.dispatch import dispatch_agent_hook

        ctx = AgentPluginContext(
            agent=mock_agent,
            task={},
            context={},
            task_description="t",
        )
        ctx.plugin_state["dawp.active_run_id"] = "dawp-abc"
        mock_hook = MagicMock(is_enabled=True, fire_in_dawp_nested=False)

        with patch.object(ctx, "get_plugin", return_value=mock_hook):
            result = await dispatch_agent_hook(
                ctx,
                AgentHookEvent.PRE_TOOL_USE,
                {"tool_name": "x"},
                nested=True,
            )
        assert result.results == []

    @pytest.mark.asyncio
    async def test_nested_true_allows_hooks_when_enabled(self, mock_agent) -> None:
        from aiecs.domain.agent.plugins.builtin.hook_plugin import HookPlugin
        from aiecs.domain.agent.plugins.hooks.dispatch import dispatch_agent_hook

        hook = HookPlugin(
            PluginConfig(
                name="hook",
                enabled=True,
                options={
                    "fire_in_dawp_nested": True,
                    "inline_hooks": {
                        "pre_tool_use": [{"type": "http", "url": "https://example.com/pre"}]
                    },
                },
            ),
            mock_agent,
        )
        ctx = AgentPluginContext(agent=mock_agent, task={}, context={}, task_description="t")
        await hook.on_agent_init(ctx)
        ctx.plugin_state["dawp.active_run_id"] = "dawp-abc"

        with patch.object(ctx, "get_plugin", return_value=hook), patch.object(
            hook, "dispatch", AsyncMock(return_value=MagicMock(blocked=False, results=[MagicMock()]))
        ):
            result = await dispatch_agent_hook(
                ctx,
                AgentHookEvent.PRE_TOOL_USE,
                {"tool_name": "x"},
                nested=True,
            )
        assert len(result.results) == 1


@pytest.mark.unit
class TestH17DawpRunEnd:
    @pytest.mark.asyncio
    async def test_drain_dispatches_h16_h17(self) -> None:
        from aiecs.domain.agent.plugins.dawp.budget import TaskIterationBudget
        from aiecs.domain.agent.plugins.dawp.schema import (
            Contract,
            DAWPStep,
            DAWPWorkflow,
            DawpPendingRun,
            MarkerCompletion,
            WorkflowMetadata,
            WorkflowSpec,
        )

        _PROMPT_MARKER = "<STEP_DONE>"
        _DAWP_MARKER = "<DAWP_COMPLETE>"

        config = AgentConfiguration(
            llm_model="m",
            plugins=[
                PluginConfig(name="memory", enabled=False),
                PluginConfig(name="hook", enabled=True),
            ],
        )

        from aiecs.llm import BaseLLMClient, LLMResponse
        from aiecs.llm.clients.openai_compatible_mixin import StreamChunk

        class _LLM(BaseLLMClient):
            def __init__(self) -> None:
                super().__init__(provider_name="openai")

            async def generate_text(self, messages, **kwargs) -> LLMResponse:
                return LLMResponse(content=f"done\n{_DAWP_MARKER}", provider="openai", model="m", tokens_used=1)

            async def stream_text(self, *args, **kwargs):
                yield StreamChunk(type="token", content=f"done\n{_DAWP_MARKER}")

            async def close(self) -> None:
                return None

        agent = HybridAgent(agent_id="h17", name="H17", tools=[], config=config, llm_client=_LLM())
        await agent.initialize()

        plugin_ctx = agent._make_plugin_context(
            task={"description": "t"},
            context={},
            task_description="t",
        )
        plugin_ctx.plugin_state["dawp.pending"] = [
            DawpPendingRun(
                trigger="config",
                workflow_source="static",
                workflow_id="wf-1",
                enqueued_at_iteration=0,
                drain_mode="on_iteration_end",
            )
        ]
        plugin_ctx.plugin_state["dawp.workflow"] = DAWPWorkflow(
            metadata=WorkflowMetadata(name="wf-1"),
            spec=WorkflowSpec(
                contract=Contract(
                    action="Test",
                    prompt_marker=_PROMPT_MARKER,
                    dawp_marker=_DAWP_MARKER,
                )
            ),
            steps=[
                DAWPStep(
                    id="s1",
                    instruction="step",
                    completion=MarkerCompletion(
                        prompt_marker=_PROMPT_MARKER,
                        dawp_marker=_DAWP_MARKER,
                        is_last=True,
                    ),
                )
            ],
            activations=[],
        )
        budget = TaskIterationBudget(limit=5)
        messages: list[LLMMessage] = [LLMMessage(role="user", content="task")]

        dispatch_spy = AsyncMock(return_value=MagicMock(blocked=False, results=[]))
        with patch(
            "aiecs.domain.agent.plugins.hooks.dispatch.dispatch_agent_hook",
            dispatch_spy,
        ):
            events = []
            async for event in agent._drain_pending_dawp_runs(
                "on_iteration_end",
                messages,
                {},
                plugin_ctx,
                budget,
            ):
                events.append(event)

        start_calls = [c for c in dispatch_spy.await_args_list if c.args[1] == AgentHookEvent.DAWP_RUN_START]
        end_calls = [c for c in dispatch_spy.await_args_list if c.args[1] == AgentHookEvent.DAWP_RUN_END]
        assert len(start_calls) == 1
        assert len(end_calls) == 1
        assert end_calls[0].args[2]["workflow_id"] == "wf-1"
        assert end_calls[0].args[2]["status"] in {"success", "failed"}
