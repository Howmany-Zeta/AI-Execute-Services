"""
D2-10 — KnowledgePlugin (priority 40) vs DAWP (priority 45) ordering (§9, §14).

Product decision (resolved):
  When KnowledgePlugin PRE_MAIN_LOOP short-circuits, pre_main_loop DAWP does NOT run.
  Knowledge (40) runs before DAWP (45); PluginManager returns immediately on
  PluginShortCircuitResult, so DawpPlugin.on_pre_main_loop is never invoked and
  dawp.pending stays empty.  The main tool loop is also skipped.

  When Knowledge does NOT short-circuit, DAWP pre_main_loop activations enqueue
  normally and HybridAgent drains them before the main loop (D2-08 parity).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar
from unittest.mock import AsyncMock, patch

import pytest

from aiecs.domain.agent.hybrid_agent import HybridAgent
from aiecs.domain.agent.models import AgentConfiguration
from aiecs.domain.agent.plugins.base import BaseAgentPlugin
from aiecs.domain.agent.plugins.builtin.dawp_plugin import DawpPlugin
from aiecs.domain.agent.plugins.context import AgentPluginContext, PluginShortCircuitResult
from aiecs.domain.agent.plugins.manager import PluginManager
from aiecs.domain.agent.plugins.models import PluginConfig, PluginMetadata, PluginPhase
from aiecs.domain.agent.plugins.registry import PluginRegistry
from aiecs.llm import BaseLLMClient, LLMMessage, LLMResponse

_WORKFLOWS_DIR = (
    Path(__file__).parents[5]
    / "issue_report"
    / "new_function_request"
    / "agent_system_design"
    / "workflows"
)
_DAWP_EXAMPLE = _WORKFLOWS_DIR / "dawp-example.dawp.md"

_GRAPH_SHORT_CIRCUIT_TASK = "How is Alice connected to Bob?"
_GRAPH_NO_SHORT_CIRCUIT_TASK = "Summarize the quarterly sales report."


# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------


class _GraphStoreStub:
    def __init__(self, *, short_circuit: bool) -> None:
        self.reason = AsyncMock(
            return_value={
                "answer": "Alice works at Acme Corp with Bob.",
                "confidence": 0.95,
                "evidence_count": 2,
                "reasoning_trace": ["edge: works_at"],
            }
            if short_circuit
            else {"answer": "low confidence", "confidence": 0.3}
        )
        self.search = AsyncMock(return_value=[])


class _GraphHybridAgent(HybridAgent):
    def __init__(self, *, short_circuit: bool, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.graph_store = _GraphStoreStub(short_circuit=short_circuit)
        self.enable_graph_reasoning = True
        self._knowledge_context: dict[str, Any] = {}


class MockLLMClient(BaseLLMClient):
    def __init__(self) -> None:
        super().__init__(provider_name="openai")
        self.call_count = 0

    async def generate_text(self, messages: list[LLMMessage], **kwargs: Any) -> LLMResponse:
        self.call_count += 1
        return LLMResponse(content="main loop answer", provider="openai", model="test", tokens_used=1)

    async def stream_text(self, *args: Any, **kwargs: Any):
        yield "main loop answer"

    async def close(self) -> None:
        pass


class DawpPreMainSpy(BaseAgentPlugin):
    """Spy that records whether DawpPlugin-equivalent PRE_MAIN_LOOP ran."""

    metadata: ClassVar[PluginMetadata] = PluginMetadata(
        name="dawp_spy",
        version="1.0.0",
        description="DAWP PRE_MAIN_LOOP spy",
        priority=45,
    )

    async def on_pre_main_loop(self, ctx: AgentPluginContext) -> None:
        ctx.plugin_state["dawp_spy_called"] = True
        return None


def _make_ctx(agent: HybridAgent, task_description: str) -> AgentPluginContext:
    return AgentPluginContext(
        agent=agent,
        task={"description": task_description},
        context={},
        task_description=task_description,
    )


async def _make_manager(
    agent: HybridAgent,
    *,
    include_dawp: bool = True,
    include_dawp_spy: bool = False,
) -> PluginManager:
    configs: list[PluginConfig] = [
        PluginConfig(name="knowledge", enabled=True, priority=40),
        PluginConfig(name="memory", enabled=False),
        PluginConfig(name="skill", enabled=False),
    ]
    if include_dawp:
        configs.append(
            PluginConfig(
                name="dawp",
                enabled=True,
                priority=45,
                options={"document_path": str(_DAWP_EXAMPLE)},
            )
        )
    if include_dawp_spy:
        configs.append(PluginConfig(name="dawp_spy", enabled=True, priority=45))

    registry = PluginRegistry.default()
    if include_dawp_spy:
        registry.register("dawp_spy", DawpPreMainSpy, origin="registry")

    manager = PluginManager(agent, configs, registry=registry)
    await manager.initialize()
    return manager


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDawpKnowledgePriorityMetadata:
    """Registry metadata: knowledge 40 < dawp 45."""

    def test_knowledge_priority_40_before_dawp_45(self) -> None:
        registry = PluginRegistry.default()
        knowledge = registry.get_entry("knowledge")
        dawp = registry.get_entry("dawp")

        assert knowledge is not None
        assert dawp is not None
        assert knowledge.metadata.priority == 40
        assert DawpPlugin.metadata.priority == 45
        assert dawp.metadata.priority == 45
        assert knowledge.metadata.priority < dawp.metadata.priority


@pytest.mark.unit
@pytest.mark.asyncio
class TestPreMainLoopOrdering:
    """PRE_MAIN_LOOP hook order: knowledge before dawp."""

    async def test_pre_main_loop_order_knowledge_before_dawp(self) -> None:
        agent = _GraphHybridAgent(
            short_circuit=False,
            agent_id="order-test",
            name="Order Test",
            llm_client=MockLLMClient(),
            tools=[],
            config=AgentConfiguration(goal="test", llm_model="test"),
        )
        manager = await _make_manager(agent, include_dawp=True)

        pre_main_order: list[str] = []
        original_invoke = manager._invoke_hook

        async def tracking_invoke(
            plugin: BaseAgentPlugin,
            hook_name: str,
            phase: PluginPhase,
            ctx: AgentPluginContext,
            **hook_kwargs: Any,
        ) -> Any:
            if phase == PluginPhase.PRE_MAIN_LOOP and hook_name == "on_pre_main_loop":
                pre_main_order.append(plugin.metadata.name)
            return await original_invoke(plugin, hook_name, phase, ctx, **hook_kwargs)

        ctx = _make_ctx(agent, _GRAPH_NO_SHORT_CIRCUIT_TASK)
        await manager.run_phase(PluginPhase.PRE_TASK, ctx=ctx)

        with patch.object(manager, "_invoke_hook", side_effect=tracking_invoke):
            short = await manager.run_phase(PluginPhase.PRE_MAIN_LOOP, ctx=ctx)

        assert short is None
        assert pre_main_order == ["knowledge", "dawp"], (
            f"Expected knowledge(40) then dawp(45); got {pre_main_order}"
        )


@pytest.mark.unit
@pytest.mark.asyncio
class TestKnowledgeShortCircuitSkipsDawp:
    """Product decision: knowledge short-circuit → pre_main DAWP does NOT run."""

    async def test_knowledge_short_circuit_skips_dawp_pre_main_enqueue(self) -> None:
        agent = _GraphHybridAgent(
            short_circuit=True,
            agent_id="sc-test",
            name="SC Test",
            llm_client=MockLLMClient(),
            tools=[],
            config=AgentConfiguration(goal="test", llm_model="test"),
        )
        manager = await _make_manager(agent, include_dawp=True)

        pre_main_order: list[str] = []
        original_invoke = manager._invoke_hook

        async def tracking_invoke(
            plugin: BaseAgentPlugin,
            hook_name: str,
            phase: PluginPhase,
            ctx: AgentPluginContext,
            **hook_kwargs: Any,
        ) -> Any:
            if phase == PluginPhase.PRE_MAIN_LOOP and hook_name == "on_pre_main_loop":
                pre_main_order.append(plugin.metadata.name)
            return await original_invoke(plugin, hook_name, phase, ctx, **hook_kwargs)

        ctx = _make_ctx(agent, _GRAPH_SHORT_CIRCUIT_TASK)
        await manager.run_phase(PluginPhase.PRE_TASK, ctx=ctx)

        with patch.object(manager, "_invoke_hook", side_effect=tracking_invoke):
            short = await manager.run_phase(PluginPhase.PRE_MAIN_LOOP, ctx=ctx)

        assert isinstance(short, PluginShortCircuitResult)
        assert short.reason == "knowledge_graph_short_circuit"
        assert pre_main_order == ["knowledge"], (
            "DAWP must not run PRE_MAIN_LOOP after knowledge short-circuit"
        )
        assert ctx.plugin_state.get("dawp.pending", []) == [], (
            "pre_main_loop DAWP must not be enqueued when knowledge short-circuits"
        )

    async def test_knowledge_short_circuit_skips_dawp_spy(self) -> None:
        """DawpPlugin-equivalent spy at priority 45 never invoked on short-circuit."""
        agent = _GraphHybridAgent(
            short_circuit=True,
            agent_id="spy-test",
            name="Spy Test",
            llm_client=MockLLMClient(),
            tools=[],
            config=AgentConfiguration(goal="test", llm_model="test"),
        )
        manager = await _make_manager(agent, include_dawp=False, include_dawp_spy=True)

        ctx = _make_ctx(agent, _GRAPH_SHORT_CIRCUIT_TASK)
        await manager.run_phase(PluginPhase.PRE_TASK, ctx=ctx)
        short = await manager.run_phase(PluginPhase.PRE_MAIN_LOOP, ctx=ctx)

        assert isinstance(short, PluginShortCircuitResult)
        assert "dawp_spy_called" not in ctx.plugin_state


@pytest.mark.unit
@pytest.mark.asyncio
class TestKnowledgeNoShortCircuitAllowsDawp:
    """When knowledge does not short-circuit, DAWP pre_main_loop enqueues normally."""

    async def test_knowledge_no_short_circuit_dawp_pre_main_enqueued(self) -> None:
        agent = _GraphHybridAgent(
            short_circuit=False,
            agent_id="no-sc-test",
            name="No SC Test",
            llm_client=MockLLMClient(),
            tools=[],
            config=AgentConfiguration(goal="test", llm_model="test"),
        )
        manager = await _make_manager(agent, include_dawp=True)

        ctx = _make_ctx(agent, _GRAPH_NO_SHORT_CIRCUIT_TASK)
        await manager.run_phase(PluginPhase.PRE_TASK, ctx=ctx)
        short = await manager.run_phase(PluginPhase.PRE_MAIN_LOOP, ctx=ctx)

        assert short is None
        pending = ctx.plugin_state.get("dawp.pending", [])
        assert len(pending) == 1, f"Expected 1 pre_main_loop pending run; got {pending}"
        assert pending[0].drain_mode == "on_iteration_end"
        assert pending[0].workflow_id == "First Principles Intent Analysis"


@pytest.mark.unit
@pytest.mark.asyncio
class TestExecuteTaskShortCircuitSkipsDawpDrain:
    """execute_task: knowledge short-circuit → no LLM, no DAWP drain."""

    async def test_execute_task_short_circuit_skips_main_loop_and_dawp(self) -> None:
        llm = MockLLMClient()
        drain_called = False

        agent = _GraphHybridAgent(
            short_circuit=True,
            agent_id="e2e-sc",
            name="E2E SC",
            llm_client=llm,
            tools=[],
            config=AgentConfiguration(
                goal="test",
                llm_model="test",
                plugins=[
                    PluginConfig(name="knowledge", enabled=True, priority=40),
                    PluginConfig(
                        name="dawp",
                        enabled=True,
                        priority=45,
                        options={"document_path": str(_DAWP_EXAMPLE)},
                    ),
                    PluginConfig(name="memory", enabled=False),
                    PluginConfig(name="skill", enabled=False),
                ],
            ),
        )
        await agent.initialize()

        original_drain = agent._drain_pending_dawp_runs

        async def _tracking_drain(*args: Any, **kwargs: Any):
            nonlocal drain_called
            drain_called = True
            async for event in original_drain(*args, **kwargs):
                yield event

        with patch.object(agent, "_drain_pending_dawp_runs", side_effect=_tracking_drain):
            result = await agent.execute_task(
                {"description": _GRAPH_SHORT_CIRCUIT_TASK},
                {},
            )

        assert result.get("source") == "knowledge_graph"
        assert result.get("success") is True
        assert llm.call_count == 0, "Main loop LLM must not run after knowledge short-circuit"
        assert drain_called is False, "DAWP drain must not run when knowledge short-circuits"
