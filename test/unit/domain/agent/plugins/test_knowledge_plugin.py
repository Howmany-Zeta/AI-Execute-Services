"""
Unit tests for KnowledgePlugin scaffold (E-01, §4.3, §6.4).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from aiecs.domain.agent.base_agent import BaseAIAgent
from aiecs.domain.agent.hybrid_agent import HybridAgent
from aiecs.domain.agent.models import AgentConfiguration, AgentType
from aiecs.domain.agent.plugins.builtin.knowledge_plugin import (
    PLUGIN_STATE_AUGMENTED_TASK_KEY,
    KnowledgePlugin,
    augment_prompt_with_knowledge,
    effective_task_description,
)
from aiecs.domain.agent.plugins.context import AgentPluginContext
from aiecs.domain.agent.plugins.defaults import derive_default_plugins
from aiecs.domain.agent.plugins.manager import PluginManager
from aiecs.domain.agent.plugins.models import PluginConfig, PluginPhase
from aiecs.domain.agent.plugins.registry import PluginRegistry
from aiecs.domain.agent.plugins.testing.normalize import normalize_value
from aiecs.domain.agent.tool_loop_core import ToolLoopIterationOutcome
from aiecs.infrastructure.knowledge import NoOpGraphStore
from aiecs.llm import BaseLLMClient, LLMMessage, LLMResponse


class MockLLMClient(BaseLLMClient):
    def __init__(self) -> None:
        super().__init__(provider_name="openai")

    async def generate_text(self, messages: list[LLMMessage], **kwargs: Any) -> LLMResponse:
        return LLMResponse(content="ok", provider="openai", model="test", tokens_used=0)

    async def stream_text(self, *args: Any, **kwargs: Any):
        yield "ok"

    async def close(self) -> None:
        pass


class _GraphStoreStub:
    """Non-NoOp graph store for augment/retrieval tests."""

    def __init__(self) -> None:
        self.reason = AsyncMock()
        self.search = AsyncMock(return_value=[])


class KnowledgeTestAgent(BaseAIAgent):
    """Minimal agent for KnowledgePlugin load tests."""

    async def _initialize(self) -> None:
        pass

    async def _shutdown(self) -> None:
        pass

    async def execute_task(self, task: dict, context: dict) -> dict:
        return {"success": True, "output": "ok"}

    async def process_message(self, message: str, sender_id: str | None = None) -> dict:
        return {"response": "ok"}


@pytest.fixture
def mock_llm_client():
    client = AsyncMock(spec=BaseLLMClient)
    client.provider_name = "test_provider"
    client.generate = AsyncMock(
        return_value=LLMResponse(
            content="Test response",
            provider="test_provider",
            model="test-model",
        )
    )
    return client


@pytest.fixture
async def graph_store():
    store = NoOpGraphStore()
    await store.initialize()
    yield store
    await store.close()


def _make_hybrid_knowledge_agent(mock_llm_client, graph_store=None) -> HybridAgent:
    """HybridAgent with knowledge plugin (no initialize — tests wire plugin manager manually)."""
    agent = HybridAgent(
        agent_id="knowledge-plugin-test-agent",
        name="Knowledge Plugin Test Agent",
        llm_client=mock_llm_client,
        tools=[],
        config=AgentConfiguration(
            goal="Knowledge plugin augment test",
            plugins=[PluginConfig(name="knowledge", enabled=True)],
        ),
    )
    if graph_store is not None:
        agent.graph_store = graph_store
        agent.enable_graph_reasoning = True
    return agent


@pytest.fixture
def knowledge_test_agent() -> KnowledgeTestAgent:
    config = AgentConfiguration(goal="Knowledge plugin test")
    return KnowledgeTestAgent(
        agent_id="knowledge-plugin-test",
        name="Knowledge Plugin Test",
        agent_type=AgentType.DEVELOPER,
        config=config,
        tools=[],
    )


@pytest.mark.unit
class TestKnowledgePluginMetadata:
    def test_priority_is_40(self) -> None:
        assert KnowledgePlugin.metadata.priority == 40
        assert KnowledgePlugin.metadata.name == "knowledge"
        assert KnowledgePlugin.metadata.default_enabled is False


@pytest.mark.unit
class TestKnowledgePluginDerive:
    def test_legacy_fields_map_to_options(self, mock_agent) -> None:
        config = AgentConfiguration(
            goal="Knowledge derive test",
            retrieval_strategy="graph",
            enable_knowledge_caching=False,
            max_context_size=25,
            cache_ttl=600,
            entity_extraction_provider="ner",
        )
        mock_agent._tools_input = ["search"]

        by_name = {plugin.name: plugin for plugin in derive_default_plugins(config, mock_agent)}
        knowledge = by_name["knowledge"]

        assert knowledge.enabled is False
        assert knowledge.options["retrieval_strategy"] == "graph"
        assert knowledge.options["enable_knowledge_caching"] is False
        assert knowledge.options["max_context_size"] == 25
        assert knowledge.options["cache_ttl"] == 600
        assert knowledge.options["entity_extraction_provider"] == "ner"
        assert knowledge.options["enable_graph_reasoning"] is True

    def test_enabled_when_agent_has_graph_store(self, mock_agent) -> None:
        config = AgentConfiguration(goal="Knowledge derive test")
        mock_agent._tools_input = ["search"]
        mock_agent.graph_store = object()

        by_name = {plugin.name: plugin for plugin in derive_default_plugins(config, mock_agent)}
        assert by_name["knowledge"].enabled is True


@pytest.mark.unit
@pytest.mark.asyncio
class TestKnowledgePluginLoad:
    async def test_loads_when_enabled_in_config(self, knowledge_test_agent: KnowledgeTestAgent) -> None:
        registry = PluginRegistry.default()
        manager = PluginManager(
            knowledge_test_agent,
            [PluginConfig(name="knowledge", enabled=True)],
            registry=registry,
        )
        result = await manager.initialize()

        assert "knowledge@builtin" in result.enabled
        assert manager.is_enabled("knowledge")
        plugin = manager.get_plugin("knowledge")
        assert isinstance(plugin, KnowledgePlugin)

    async def test_disabled_by_default_not_loaded(self, knowledge_test_agent: KnowledgeTestAgent) -> None:
        registry = PluginRegistry.default()
        mock_agent = knowledge_test_agent
        mock_agent._tools_input = None
        configs = derive_default_plugins(knowledge_test_agent._config, mock_agent)
        manager = PluginManager(knowledge_test_agent, configs, registry=registry)
        result = await manager.initialize()

        assert "knowledge@builtin" not in result.enabled
        assert not manager.is_enabled("knowledge")

    async def test_no_op_hooks_return_none(self, knowledge_test_agent: KnowledgeTestAgent) -> None:
        from aiecs.domain.agent.plugins.context import AgentPluginContext
        from aiecs.llm import LLMMessage

        plugin = KnowledgePlugin(PluginConfig(name="knowledge", enabled=True), knowledge_test_agent)
        ctx = AgentPluginContext(
            agent=knowledge_test_agent,
            task={"description": "knowledge test"},
            context={},
            task_description="knowledge test",
        )

        assert await plugin.on_agent_init(ctx) is None
        assert await plugin.on_pre_main_loop(ctx) is None
        assert await plugin.on_post_task(ctx, {"success": True}) == {"success": True}
        assert await plugin.on_build_messages(ctx, [LLMMessage(role="user", content="hi")]) == [
            LLMMessage(role="user", content="hi")
        ]

        manager = PluginManager(
            knowledge_test_agent,
            [PluginConfig(name="knowledge", enabled=True, priority=40)],
            registry=PluginRegistry.default(),
        )
        await manager.initialize()
        pre_main = await manager.run_phase(PluginPhase.PRE_MAIN_LOOP, ctx=ctx)
        assert pre_main is None


def _seed_knowledge_context(agent: BaseAIAgent) -> None:
    agent.graph_store = _GraphStoreStub()
    agent.enable_graph_reasoning = True
    agent._knowledge_context = {
        "alice": {
            "answer": "Alice is a person",
            "confidence": 0.9,
            "evidence_count": 2,
            "timestamp": datetime.utcnow().isoformat(),
        },
    }


@pytest.mark.unit
@pytest.mark.asyncio
class TestKnowledgePluginAugment:
    async def test_on_pre_task_writes_augmented_task_to_plugin_state(
        self,
        mock_llm_client,
        graph_store,
    ) -> None:
        agent = _make_hybrid_knowledge_agent(mock_llm_client, graph_store)
        _seed_knowledge_context(agent)

        plugin = KnowledgePlugin(PluginConfig(name="knowledge", enabled=True), agent)
        ctx = AgentPluginContext(
            agent=agent,
            task={"description": "Tell me about alice"},
            context={},
            task_description="Tell me about alice",
        )

        await plugin.on_pre_task(ctx)

        assert PLUGIN_STATE_AUGMENTED_TASK_KEY in ctx.plugin_state
        assert "Alice is a person" in ctx.plugin_state[PLUGIN_STATE_AUGMENTED_TASK_KEY]
        assert effective_task_description(ctx, ctx.task_description) != ctx.task_description

    async def test_augment_includes_cached_graph_context(
        self,
        mock_llm_client,
        graph_store,
    ) -> None:
        agent = _make_hybrid_knowledge_agent(mock_llm_client, graph_store)
        _seed_knowledge_context(agent)

        task = "Tell me about alice"
        plugin_result = await augment_prompt_with_knowledge(agent, task)

        assert "RELEVANT KNOWLEDGE FROM GRAPH" in plugin_result
        assert "Alice is a person" in plugin_result
        assert "confidence: 0.90" in plugin_result

    async def test_no_augment_without_graph_store(self, knowledge_test_agent: KnowledgeTestAgent) -> None:
        plugin = KnowledgePlugin(PluginConfig(name="knowledge", enabled=True), knowledge_test_agent)
        ctx = AgentPluginContext(
            agent=knowledge_test_agent,
            task={"description": "plain task"},
            context={},
            task_description="plain task",
        )

        await plugin.on_pre_task(ctx)

        assert ctx.plugin_state[PLUGIN_STATE_AUGMENTED_TASK_KEY] == "plain task"

    async def test_hybrid_kernel_uses_augmented_task_before_build_messages(
        self,
        mock_llm_client,
        graph_store,
    ) -> None:
        agent = _make_hybrid_knowledge_agent(mock_llm_client, graph_store)
        _seed_knowledge_context(agent)

        registry = PluginRegistry()
        registry.register("knowledge", KnowledgePlugin, origin="builtin")
        agent._plugin_manager = PluginManager(
            agent,
            [PluginConfig(name="knowledge", enabled=True)],
            registry=registry,
        )
        await agent._plugin_manager.initialize()

        captured_tasks: list[str] = []

        async def fake_tool_loop(task_description, context, plugin_ctx):
            captured_tasks.append(task_description)
            return {
                "success": True,
                "final_response": "ok",
                "steps": [],
                "iterations": 0,
                "tool_calls_count": 0,
                "total_tokens": 0,
            }

        agent._tool_loop_with_plugins = fake_tool_loop  # type: ignore[method-assign]
        await agent._execute_task_with_plugins({"description": "Tell me about alice"}, {})

        assert captured_tasks
        assert "RELEVANT KNOWLEDGE FROM GRAPH" in captured_tasks[0]
        assert "Alice is a person" in captured_tasks[0]


class GraphReasoningAgent(BaseAIAgent):
    """BaseAIAgent stub for direct KnowledgePlugin hook tests."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.graph_store = _GraphStoreStub()
        self.enable_graph_reasoning = True
        self._knowledge_context: dict[str, Any] = {}

    async def _initialize(self) -> None:
        pass

    async def _shutdown(self) -> None:
        pass

    async def execute_task(self, task: dict, context: dict) -> dict:
        return {"success": True, "output": "ok"}

    async def process_message(self, message: str, sender_id: str | None = None) -> dict:
        return {"response": "ok"}


@pytest.fixture
def graph_agent() -> GraphReasoningAgent:
    return GraphReasoningAgent(
        agent_id="graph-agent",
        name="Graph Agent",
        agent_type=AgentType.DEVELOPER,
        config=AgentConfiguration(goal="Knowledge plugin test"),
        tools=[],
    )


class KnowledgeHybridAgent(HybridAgent):
    """HybridAgent with graph store stub for KnowledgePlugin iteration tests."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.graph_store = _GraphStoreStub()
        self.enable_graph_reasoning = True
        self._knowledge_context = {}


@pytest.mark.unit
@pytest.mark.asyncio
class TestKnowledgePluginIterationRetrieval:
    async def test_on_iteration_start_writes_iteration_context(self, graph_agent: GraphReasoningAgent) -> None:
        alice = type("Entity", (), {"id": "alice", "entity_type": "Person", "properties": {}})()
        graph_agent.graph_store.search.return_value = [alice]

        plugin = KnowledgePlugin(
            PluginConfig(name="knowledge", enabled=True, options={"max_context_size": 5}),
            graph_agent,
        )
        ctx = AgentPluginContext(
            agent=graph_agent,
            task={"description": "Find Alice"},
            context={},
            task_description="Find Alice",
        )

        await plugin.on_iteration_start(ctx, 0)

        block = ctx.plugin_state["knowledge.iteration_context"]
        assert block["iteration"] == 0
        assert block["entity_count"] == 1
        assert "alice" in block["formatted"]

    async def test_second_iteration_receives_new_context_block(self) -> None:
        registry = PluginRegistry()
        registry.register("knowledge", KnowledgePlugin, origin="builtin")

        agent = KnowledgeHybridAgent(
            agent_id="knowledge-iteration-test",
            name="Knowledge Iteration Test",
            llm_client=MockLLMClient(),
            config=AgentConfiguration(goal="Knowledge iteration test"),
            tools=[],
            max_iterations=3,
        )
        agent._plugin_manager = PluginManager(
            agent,
            [PluginConfig(name="knowledge", enabled=True, options={"max_context_size": 10})],
            registry=registry,
        )
        await agent._plugin_manager.initialize()

        async def search_side_effect(task, limit=10, **kwargs):
            _ = task, limit, kwargs
            if not hasattr(search_side_effect, "calls"):
                search_side_effect.calls = 0
            search_side_effect.calls += 1
            if search_side_effect.calls == 1:
                return [type("Entity", (), {"id": "alice", "entity_type": "Person", "properties": {"name": "Alice"}})()]
            return [type("Entity", (), {"id": "bob", "entity_type": "Person", "properties": {"name": "Bob"}})()]

        agent.graph_store.search.side_effect = search_side_effect

        captured_messages: list[list[LLMMessage]] = []
        original_core = agent._run_tool_loop_core_iteration

        async def capture_core(messages, context, iteration, state):
            captured_messages.append(list(messages))
            if iteration == 0:
                return ToolLoopIterationOutcome(kind="continue")
            return ToolLoopIterationOutcome(
                kind="final",
                result={
                    "success": True,
                    "final_response": "done",
                    "steps": [],
                    "iterations": iteration + 1,
                    "tool_calls_count": 0,
                    "total_tokens": 0,
                },
            )

        plugin_ctx = AgentPluginContext(
            agent=agent,
            task={"description": "Find people"},
            context={},
            task_description="Find people",
        )
        base_messages = [LLMMessage(role="user", content="Find people")]

        with patch.object(agent, "_run_tool_loop_core_iteration", side_effect=capture_core):
            await agent._run_tool_loop_with_iteration_hooks(base_messages, {}, plugin_ctx=plugin_ctx)

        assert len(captured_messages) >= 2
        iter0_blocks = [
            msg.content
            for msg in captured_messages[0]
            if msg.content and "RETRIEVED KNOWLEDGE" in msg.content
        ]
        iter1_blocks = [
            msg.content
            for msg in captured_messages[1]
            if msg.content and "RETRIEVED KNOWLEDGE" in msg.content
        ]
        assert any("alice" in block for block in iter0_blocks)
        assert any("bob" in block for block in iter1_blocks)
        assert iter0_blocks != iter1_blocks

    async def test_hybrid_execute_task_uses_plugin_tool_loop(
        self,
        mock_llm_client,
        graph_store,
    ) -> None:
        """HybridAgent execute_task routes through the plugin-aware tool loop."""
        agent = _make_hybrid_knowledge_agent(mock_llm_client, graph_store)
        registry = PluginRegistry()
        registry.register("knowledge", KnowledgePlugin, origin="builtin")
        agent._plugin_manager = PluginManager(
            agent,
            [PluginConfig(name="knowledge", enabled=True)],
            registry=registry,
        )
        await agent._plugin_manager.initialize()
        await agent.initialize()

        with patch.object(
            agent,
            "_execute_task_with_plugins",
            new_callable=AsyncMock,
        ) as mock_execute:
            mock_execute.return_value = {"success": True, "output": "done"}
            await agent.execute_task({"description": "Find Alice"}, {})

        mock_execute.assert_called_once()
