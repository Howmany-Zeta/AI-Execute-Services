"""
KnowledgePlugin PRE_MAIN_LOOP graph short-circuit tests (E-03, §4.4).
"""

from __future__ import annotations

from typing import Any, ClassVar
from unittest.mock import AsyncMock, patch

import pytest

from aiecs.domain.agent.base_agent import BaseAIAgent
from aiecs.domain.agent.hybrid_agent import HybridAgent
from aiecs.domain.agent.models import AgentConfiguration, AgentType
from aiecs.domain.agent.plugins.base import BaseAgentPlugin
from aiecs.domain.agent.plugins.builtin.knowledge_plugin import (
    KnowledgePlugin,
    PLUGIN_ID,
)
from aiecs.domain.agent.plugins.builtin.memory_plugin import MemoryPlugin
from aiecs.domain.agent.plugins.context import AgentPluginContext, PluginShortCircuitResult
from aiecs.domain.agent.plugins.manager import PluginManager
from aiecs.domain.agent.plugins.models import PluginConfig, PluginMetadata, PluginPhase
from aiecs.domain.agent.plugins.registry import PluginRegistry
from aiecs.llm import BaseLLMClient, LLMMessage, LLMResponse


class GraphReasoningHybridAgent(HybridAgent):
    """HybridAgent with graph reasoning hooks attached for KnowledgePlugin tests."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.graph_store = object()
        self.enable_graph_reasoning = True
        self._knowledge_context: dict[str, Any] = {}
        self._reason_with_graph = AsyncMock()


class GraphReasoningAgent(BaseAIAgent):
    """BaseAIAgent stub for direct KnowledgePlugin hook tests."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.graph_store = object()
        self.enable_graph_reasoning = True
        self._knowledge_context: dict[str, Any] = {}
        self._reason_with_graph = AsyncMock()

    async def _initialize(self) -> None:
        pass

    async def _shutdown(self) -> None:
        pass

    async def execute_task(self, task: dict, context: dict) -> dict:
        return {"success": True, "output": "ok"}

    async def process_message(self, message: str, sender_id: str | None = None) -> dict:
        return {"response": "ok"}


class ToolPreMainLoopSpy(BaseAgentPlugin):
    """Runs after KnowledgePlugin (priority 100) in PRE_MAIN_LOOP."""

    metadata: ClassVar[PluginMetadata] = PluginMetadata(
        name="tool_spy",
        version="1.0.0",
        description="PRE_MAIN_LOOP ordering spy",
        priority=100,
    )

    async def on_pre_main_loop(self, ctx: AgentPluginContext) -> None:
        ctx.plugin_state["tool_spy_called"] = True
        return None


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


def _make_ctx(agent: BaseAIAgent, task_description: str) -> AgentPluginContext:
    return AgentPluginContext(
        agent=agent,
        task={"description": task_description},
        context={},
        task_description=task_description,
    )


@pytest.fixture
def graph_hybrid_agent() -> GraphReasoningHybridAgent:
    return GraphReasoningHybridAgent(
        agent_id="graph-short-circuit-agent",
        name="Graph Short Circuit Agent",
        llm_client=MockLLMClient(),
        config=AgentConfiguration(goal="Knowledge short-circuit test"),
        tools=[],
        max_iterations=3,
    )


@pytest.fixture
def graph_agent() -> GraphReasoningAgent:
    return GraphReasoningAgent(
        agent_id="graph-short-circuit-agent",
        name="Graph Short Circuit Agent",
        agent_type=AgentType.DEVELOPER,
        config=AgentConfiguration(goal="Knowledge short-circuit test"),
        tools=[],
    )


@pytest.mark.unit
@pytest.mark.asyncio
class TestKnowledgeGraphShortCircuitPlugin:
    async def test_high_confidence_returns_short_circuit(self, graph_agent: GraphReasoningAgent) -> None:
        graph_agent._reason_with_graph.return_value = {
            "answer": "Alice knows Bob",
            "confidence": 0.95,
            "evidence_count": 2,
            "reasoning_trace": ["hop1"],
        }
        plugin = KnowledgePlugin(PluginConfig(name="knowledge", enabled=True), graph_agent)
        ctx = _make_ctx(graph_agent, "How is Alice connected to Bob?")

        short = await plugin.on_pre_main_loop(ctx)

        assert isinstance(short, PluginShortCircuitResult)
        assert short.source_plugin_id == PLUGIN_ID
        assert short.reason == "knowledge_graph_short_circuit"
        assert short.result["output"] == "Alice knows Bob"
        assert short.result["source"] == "knowledge_graph"
        graph_agent._reason_with_graph.assert_awaited_once()

    async def test_low_confidence_does_not_short_circuit(self, graph_agent: GraphReasoningAgent) -> None:
        graph_agent._reason_with_graph.return_value = {
            "answer": "Maybe connected",
            "confidence": 0.5,
        }
        plugin = KnowledgePlugin(PluginConfig(name="knowledge", enabled=True), graph_agent)

        short = await plugin.on_pre_main_loop(
            _make_ctx(graph_agent, "How is Alice connected to Bob?"),
        )

        assert short is None

    async def test_non_graph_query_skips_reasoning(self, graph_agent: GraphReasoningAgent) -> None:
        plugin = KnowledgePlugin(PluginConfig(name="knowledge", enabled=True), graph_agent)

        short = await plugin.on_pre_main_loop(_make_ctx(graph_agent, "Summarize this document"))

        assert short is None
        graph_agent._reason_with_graph.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
class TestKnowledgeGraphShortCircuitHybrid:
    async def test_short_circuit_skips_tool_loop_and_core(
        self,
        graph_hybrid_agent: GraphReasoningHybridAgent,
    ) -> None:
        graph_hybrid_agent._reason_with_graph.return_value = {
            "answer": "Direct graph answer",
            "confidence": 0.91,
            "evidence_count": 1,
            "reasoning_trace": [],
        }

        registry = PluginRegistry()
        registry.register("knowledge", KnowledgePlugin, origin="builtin")
        graph_hybrid_agent._plugin_manager = PluginManager(
            graph_hybrid_agent,
            [PluginConfig(name="knowledge", enabled=True, priority=40)],
            registry=registry,
        )
        await graph_hybrid_agent._plugin_manager.initialize()

        tool_loop_mock = AsyncMock(side_effect=AssertionError("_tool_loop_with_plugins must not run"))
        core_mock = AsyncMock(side_effect=AssertionError("_run_tool_loop_core must not run"))
        graph_hybrid_agent._tool_loop_with_plugins = tool_loop_mock  # type: ignore[method-assign]

        with patch.object(graph_hybrid_agent, "_run_tool_loop_core", new=core_mock):
            result = await graph_hybrid_agent._execute_task_with_plugins(
                {"description": "How is Alice connected to Bob?"},
                {},
            )

        tool_loop_mock.assert_not_called()
        core_mock.assert_not_called()
        assert result["output"] == "Direct graph answer"
        assert result["source"] == "knowledge_graph"

    async def test_post_task_memory_still_runs_on_short_circuit(
        self,
        graph_hybrid_agent: GraphReasoningHybridAgent,
    ) -> None:
        graph_hybrid_agent._reason_with_graph.return_value = {
            "answer": "Graph memory answer",
            "confidence": 0.88,
            "evidence_count": 1,
            "reasoning_trace": [],
        }

        registry = PluginRegistry()
        registry.register("knowledge", KnowledgePlugin, origin="builtin")
        registry.register("memory", MemoryPlugin, origin="builtin")
        graph_hybrid_agent._plugin_manager = PluginManager(
            graph_hybrid_agent,
            [
                PluginConfig(name="knowledge", enabled=True, priority=40),
                PluginConfig(name="memory", enabled=True),
            ],
            registry=registry,
        )
        await graph_hybrid_agent._plugin_manager.initialize()

        post_task_phases: list[PluginPhase] = []
        original_run_phase = graph_hybrid_agent._plugin_manager.run_phase

        async def tracking_run_phase(phase: PluginPhase, **kwargs: Any) -> Any:
            post_task_phases.append(phase)
            return await original_run_phase(phase, **kwargs)

        graph_hybrid_agent._tool_loop_with_plugins = AsyncMock(  # type: ignore[method-assign]
            side_effect=AssertionError("_tool_loop_with_plugins must not run"),
        )

        with patch.object(graph_hybrid_agent._plugin_manager, "run_phase", side_effect=tracking_run_phase):
            result = await graph_hybrid_agent._execute_task_with_plugins(
                {"description": "What is the relationship between Alice and Bob?"},
                {},
            )

        assert PluginPhase.POST_TASK in post_task_phases
        assert result["output"] == "Graph memory answer"

    async def test_execute_task_outer_shell_passthrough_output(
        self,
        graph_hybrid_agent: GraphReasoningHybridAgent,
    ) -> None:
        graph_hybrid_agent._reason_with_graph.return_value = {
            "answer": "Outer shell answer",
            "confidence": 0.99,
            "evidence_count": 4,
            "reasoning_trace": ["a", "b"],
        }

        registry = PluginRegistry()
        registry.register("knowledge", KnowledgePlugin, origin="builtin")
        graph_hybrid_agent._plugin_manager = PluginManager(
            graph_hybrid_agent,
            [PluginConfig(name="knowledge", enabled=True, priority=40)],
            registry=registry,
        )
        await graph_hybrid_agent._plugin_manager.initialize()
        graph_hybrid_agent._tool_loop_with_plugins = AsyncMock(  # type: ignore[method-assign]
            side_effect=AssertionError("_tool_loop_with_plugins must not run"),
        )

        inner = await graph_hybrid_agent._execute_task_with_plugins(
            {"description": "How is Alice connected to Bob?"},
            {},
        )
        result = graph_hybrid_agent._format_execute_task_response(inner, execution_time=0.25)

        assert result["output"] == "Outer shell answer"
        assert result["source"] == "knowledge_graph"
        assert result["confidence"] == 0.99
        assert result["execution_time"] == 0.25
        assert "final_response" not in result


@pytest.mark.unit
@pytest.mark.asyncio
class TestKnowledgePluginPreMainLoopOrdering:
    async def test_knowledge_runs_before_tool_plugin_on_short_circuit(self) -> None:
        registry = PluginRegistry()
        registry.register("knowledge", KnowledgePlugin, origin="builtin")
        registry.register("tool_spy", ToolPreMainLoopSpy, origin="registry")

        agent = GraphReasoningAgent(
            agent_id="ordering-agent",
            name="Ordering Agent",
            agent_type=AgentType.DEVELOPER,
            config=AgentConfiguration(goal="Ordering test"),
            tools=[],
        )
        agent._reason_with_graph.return_value = {
            "answer": "Ordered short-circuit",
            "confidence": 0.92,
        }

        manager = PluginManager(
            agent,
            [
                PluginConfig(name="tool_spy", enabled=True, priority=100),
                PluginConfig(name="knowledge", enabled=True, priority=40),
            ],
            registry=registry,
        )
        await manager.initialize()

        pre_main_plugins: list[str] = []
        original_invoke = manager._invoke_hook

        async def tracking_invoke(
            plugin: BaseAgentPlugin,
            hook_name: str,
            phase: PluginPhase,
            ctx: AgentPluginContext,
            **hook_kwargs: Any,
        ) -> Any:
            if phase == PluginPhase.PRE_MAIN_LOOP and hook_name == "on_pre_main_loop":
                pre_main_plugins.append(plugin.metadata.name)
            return await original_invoke(plugin, hook_name, phase, ctx, **hook_kwargs)

        ctx = _make_ctx(agent, "How is Alice connected to Bob?")
        with patch.object(manager, "_invoke_hook", side_effect=tracking_invoke):
            short = await manager.run_phase(PluginPhase.PRE_MAIN_LOOP, ctx=ctx)

        assert isinstance(short, PluginShortCircuitResult)
        assert pre_main_plugins == ["knowledge"]
        assert "tool_spy_called" not in ctx.plugin_state

    async def test_knowledge_priority_40_before_tool_plugin_metadata(self) -> None:
        registry = PluginRegistry.default()
        knowledge_entry = registry.get_entry("knowledge")
        tool_entry = registry.get_entry("tool")

        assert knowledge_entry is not None
        assert tool_entry is not None
        assert knowledge_entry.metadata.priority == 40
        assert tool_entry.metadata.priority == 100
        assert knowledge_entry.metadata.priority < tool_entry.metadata.priority
