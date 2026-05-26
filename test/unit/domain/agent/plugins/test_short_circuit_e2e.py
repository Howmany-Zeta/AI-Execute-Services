"""
End-to-end PRE_MAIN_LOOP short-circuit tests (P2-13, §4.4, §12).

``KnowledgeStubPlugin`` is test-only — placeholder for Phase 3 ``KnowledgePlugin``
(see PLUGIN_SYSTEM_DESIGN.md §4.4, §4.6). Do not add production KnowledgePlugin here.
"""

from __future__ import annotations

from typing import Any, ClassVar
from unittest.mock import AsyncMock, patch

import pytest

from aiecs.domain.agent.hybrid_agent import HybridAgent
from aiecs.domain.agent.models import AgentConfiguration
from aiecs.domain.agent.plugins.base import BaseAgentPlugin
from aiecs.domain.agent.plugins.context import AgentPluginContext, PluginShortCircuitResult
from aiecs.domain.agent.plugins.models import PluginConfig, PluginMetadata, PluginPhase
from aiecs.domain.agent.plugins.registry import PluginRegistry
from aiecs.llm import BaseLLMClient, LLMMessage, LLMResponse

# Phase 3: replace stub with ``KnowledgePlugin`` (``knowledge@builtin``, priority 40).
# See issue_report/new_function_request/PLUGIN_SYSTEM_DESIGN.md §4.4.


class KnowledgeStubPlugin(BaseAgentPlugin):
    """
    Test-only stand-in for future KnowledgePlugin graph-reasoning short-circuit.

    Returns a tool-loop kernel dict from PRE_MAIN_LOOP; HybridAgent maps it to
    ``output`` / ``reasoning_steps`` via ``_format_execute_task_response`` (§4.4).
    """

    metadata: ClassVar[PluginMetadata] = PluginMetadata(
        name="knowledge_stub",
        version="0.0.0",
        description="E2E stub for KnowledgePlugin (Phase 3)",
        priority=40,
    )

    async def on_pre_main_loop(self, ctx: AgentPluginContext) -> PluginShortCircuitResult:
        return PluginShortCircuitResult(
            result={
                "success": True,
                "final_response": "Knowledge graph high-confidence answer",
                "steps": [
                    {
                        "type": "knowledge",
                        "content": "matched entity graph",
                        "iteration": 0,
                    }
                ],
                "iterations": 0,
                "tool_calls_count": 0,
                "total_tokens": 0,
            },
            source_plugin_id="knowledge_stub@registry",
            reason="knowledge_graph_short_circuit",
        )


class AfterKnowledgePlugin(BaseAgentPlugin):
    """Must not run when KnowledgeStubPlugin short-circuits first (§4.4)."""

    metadata: ClassVar[PluginMetadata] = PluginMetadata(
        name="after_knowledge",
        version="1.0.0",
        description="PRE_MAIN_LOOP spy — should not run after short-circuit",
        priority=200,
    )

    async def on_pre_main_loop(self, ctx: AgentPluginContext) -> None:
        ctx.plugin_state["after_knowledge_called"] = True
        return None


class PostTaskMarkerPlugin(BaseAgentPlugin):
    """Spy that POST_TASK ran after short-circuit (§4.4)."""

    metadata: ClassVar[PluginMetadata] = PluginMetadata(
        name="post_marker",
        version="1.0.0",
        description="POST_TASK execution marker",
        priority=200,
    )

    async def on_post_task(self, ctx: AgentPluginContext, result: dict[str, Any]) -> dict[str, Any]:
        ctx.plugin_state["post_task_ran"] = True
        return result


class MockLLMClient(BaseLLMClient):
    def __init__(self) -> None:
        super().__init__(provider_name="openai")
        self.call_count = 0

    async def generate_text(self, messages: list[LLMMessage], **kwargs: Any) -> LLMResponse:
        self.call_count += 1
        return LLMResponse(content="must not run", provider="openai", model="test", tokens_used=0)

    async def stream_text(self, *args: Any, **kwargs: Any):
        yield "must not run"

    async def close(self) -> None:
        pass


def _e2e_registry() -> PluginRegistry:
    registry = PluginRegistry()
    registry.register("knowledge_stub", KnowledgeStubPlugin, origin="registry")
    registry.register("after_knowledge", AfterKnowledgePlugin, origin="registry")
    registry.register("post_marker", PostTaskMarkerPlugin, origin="registry")
    return registry


def _disabled_builtins() -> list[PluginConfig]:
    return [
        PluginConfig(name="tool", enabled=False),
        PluginConfig(name="skill", enabled=False),
        PluginConfig(name="memory", enabled=False),
    ]


@pytest.mark.unit
@pytest.mark.asyncio
class TestPreMainLoopShortCircuitE2E:
    """HybridAgent + KnowledgeStubPlugin end-to-end (§4.4, §12)."""

    async def test_short_circuit_skips_tool_loop_post_task_formats_outer_response(
        self,
    ) -> None:
        registry = _e2e_registry()
        config = AgentConfiguration(
            goal="Knowledge short-circuit E2E",
            llm_model="test-model",
            plugins=[
                *_disabled_builtins(),
                PluginConfig(name="knowledge_stub", enabled=True),
                PluginConfig(name="after_knowledge", enabled=True),
                PluginConfig(name="post_marker", enabled=True),
            ],
        )
        client = MockLLMClient()
        agent = HybridAgent(
            agent_id="knowledge-short-circuit-e2e",
            name="Knowledge Short Circuit E2E",
            llm_client=client,
            tools=[],
            config=config,
            max_iterations=3,
            plugin_registry=registry,
        )
        await agent.initialize()

        tool_loop_mock = AsyncMock(side_effect=AssertionError("_tool_loop_with_plugins must not run"))
        core_mock = AsyncMock(side_effect=AssertionError("_run_tool_loop_core must not run"))
        phases_run: list[PluginPhase] = []
        pre_main_plugins: list[str] = []
        post_task_ran = False

        original_run_phase = agent._plugin_manager.run_phase
        original_invoke = agent._plugin_manager._invoke_hook

        async def tracking_run_phase(phase: PluginPhase, **kwargs: Any) -> Any:
            phases_run.append(phase)
            return await original_run_phase(phase, **kwargs)

        async def tracking_invoke(
            plugin: BaseAgentPlugin,
            hook_name: str,
            phase: PluginPhase,
            ctx: AgentPluginContext,
            **hook_kwargs: Any,
        ) -> Any:
            nonlocal post_task_ran
            if phase == PluginPhase.PRE_MAIN_LOOP and hook_name == "on_pre_main_loop":
                pre_main_plugins.append(plugin.metadata.name)
            if phase == PluginPhase.POST_TASK and hook_name == "on_post_task":
                if plugin.metadata.name == "post_marker":
                    post_task_ran = True
            return await original_invoke(plugin, hook_name, phase, ctx, **hook_kwargs)

        agent._tool_loop_with_plugins = tool_loop_mock  # type: ignore[method-assign]

        with (
            patch.object(agent._plugin_manager, "run_phase", side_effect=tracking_run_phase),
            patch.object(agent._plugin_manager, "_invoke_hook", side_effect=tracking_invoke),
            patch.object(agent, "_run_tool_loop_core", new=core_mock),
        ):
            result = await agent.execute_task(
                {"description": "Query knowledge graph"},
                {},
            )

        tool_loop_mock.assert_not_called()
        core_mock.assert_not_called()
        assert client.call_count == 0

        assert PluginPhase.PRE_TASK in phases_run
        assert PluginPhase.PRE_MAIN_LOOP in phases_run
        assert PluginPhase.POST_TASK in phases_run
        assert PluginPhase.BUILD_MESSAGES not in phases_run

        assert pre_main_plugins == ["knowledge_stub"]
        assert post_task_ran is True

        assert result["success"] is True
        assert result["output"] == "Knowledge graph high-confidence answer"
        assert result["reasoning_steps"] == [
            {"type": "knowledge", "content": "matched entity graph", "iteration": 0}
        ]
        assert "execution_time" in result
        assert result["timestamp"]
