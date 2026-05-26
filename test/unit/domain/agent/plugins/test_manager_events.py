"""
Unit tests for PluginManager framework streaming events (§10.3, P2-12).
"""

from __future__ import annotations

from typing import Any

import pytest

from aiecs.domain.agent.plugins.base import BaseAgentPlugin
from aiecs.domain.agent.plugins.context import AgentPluginContext, PluginShortCircuitResult
from aiecs.domain.agent.plugins.errors import PluginErrorException
from aiecs.domain.agent.plugins.manager import PluginManager
from aiecs.domain.agent.plugins.models import PluginConfig, PluginMetadata, PluginPhase
from aiecs.domain.agent.plugins.registry import PluginRegistry


def _make_ctx(mock_agent, *, event_sink=None, plugin_state: dict | None = None) -> AgentPluginContext:
    return AgentPluginContext(
        agent=mock_agent,
        task={"description": "test task"},
        context={},
        task_description="test task",
        plugin_state=plugin_state or {},
        event_sink=event_sink,
    )


class EventCollector:
    """Collects framework events emitted via ``event_sink``."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    async def __call__(self, event: dict[str, Any]) -> None:
        self.events.append(event)


class EarlyPlugin(BaseAgentPlugin):
    metadata = PluginMetadata(name="early", version="1.0.0", description="early", priority=50)

    async def on_pre_task(self, ctx: AgentPluginContext) -> None:
        ctx.plugin_state.setdefault("pre_task_order", []).append("early")


class LatePlugin(BaseAgentPlugin):
    metadata = PluginMetadata(name="late", version="1.0.0", description="late", priority=200)

    async def on_pre_task(self, ctx: AgentPluginContext) -> None:
        ctx.plugin_state.setdefault("pre_task_order", []).append("late")


class AppendMessagePlugin(BaseAgentPlugin):
    metadata = PluginMetadata(name="append_a", version="1.0.0", description="append a", priority=10)

    async def on_build_messages(self, ctx, messages):
        return [*messages, {"role": "system", "content": "from-a"}]


class ShortCircuitPlugin(BaseAgentPlugin):
    metadata = PluginMetadata(name="short", version="1.0.0", description="short", priority=10)

    async def on_pre_main_loop(self, ctx):
        return PluginShortCircuitResult(
            result={"final_response": "short"},
            source_plugin_id="short@registry",
        )


class NeverCalledPlugin(BaseAgentPlugin):
    metadata = PluginMetadata(name="never", version="1.0.0", description="never", priority=20)

    async def on_pre_main_loop(self, ctx):
        ctx.plugin_state["never_called"] = True
        return None


class FailingPlugin(BaseAgentPlugin):
    metadata = PluginMetadata(name="failing", version="1.0.0", description="failing", priority=10)

    async def on_pre_task(self, ctx):
        raise RuntimeError("hook boom")


def _event_types(events: list[dict[str, Any]]) -> list[str]:
    return [e["type"] for e in events]


@pytest.mark.unit
@pytest.mark.asyncio
class TestPluginManagerFrameworkEvents:
    """Framework events via ``ctx.event_sink`` (§10.3)."""

    async def test_no_events_without_event_sink(self, mock_agent) -> None:
        registry = PluginRegistry()
        registry.register("early", EarlyPlugin)
        manager = PluginManager(
            mock_agent,
            [PluginConfig(name="early", enabled=True)],
            registry=registry,
        )
        await manager.initialize()

        ctx = _make_ctx(mock_agent, event_sink=None)
        await manager.run_phase(PluginPhase.PRE_TASK, ctx=ctx)

        assert ctx.plugin_state["pre_task_order"] == ["early"]

    async def test_pre_task_emits_phase_then_hook_events_in_order(self, mock_agent) -> None:
        registry = PluginRegistry()
        registry.register("early", EarlyPlugin)
        registry.register("late", LatePlugin)
        collector = EventCollector()
        manager = PluginManager(
            mock_agent,
            [
                PluginConfig(name="late", enabled=True),
                PluginConfig(name="early", enabled=True),
            ],
            registry=registry,
        )
        await manager.initialize()

        ctx = _make_ctx(mock_agent, event_sink=collector)
        await manager.run_phase(PluginPhase.PRE_TASK, ctx=ctx)

        types = _event_types(collector.events)
        assert types[0] == "plugin_phase_started"
        assert types[1:6] == [
            "plugin_hook_started",
            "plugin_hook_completed",
            "plugin_hook_started",
            "plugin_hook_completed",
        ]
        assert collector.events[0]["phase"] == PluginPhase.PRE_TASK.value
        assert collector.events[0]["plugin_count"] == 2
        assert collector.events[1]["plugin_name"] == "early"
        assert collector.events[2]["plugin_name"] == "early"
        assert "duration_ms" in collector.events[2]
        assert collector.events[3]["plugin_name"] == "late"

    async def test_build_messages_hook_chain_after_phase_started(self, mock_agent) -> None:
        registry = PluginRegistry()
        registry.register("append_a", AppendMessagePlugin)
        collector = EventCollector()
        manager = PluginManager(
            mock_agent,
            [PluginConfig(name="append_a", enabled=True)],
            registry=registry,
        )
        await manager.initialize()

        ctx = _make_ctx(mock_agent, event_sink=collector)
        await manager.run_phase(
            PluginPhase.BUILD_MESSAGES,
            ctx=ctx,
            messages=[{"role": "user", "content": "hi"}],
        )

        types = _event_types(collector.events)
        assert types == [
            "plugin_phase_started",
            "plugin_hook_started",
            "plugin_hook_completed",
        ]
        assert collector.events[0]["phase"] == PluginPhase.BUILD_MESSAGES.value
        assert collector.events[0]["plugin_count"] == 1

    async def test_pre_main_loop_short_circuit_emits_only_first_plugin_hooks(
        self, mock_agent
    ) -> None:
        registry = PluginRegistry()
        registry.register("short", ShortCircuitPlugin)
        registry.register("never", NeverCalledPlugin)
        collector = EventCollector()
        manager = PluginManager(
            mock_agent,
            [
                PluginConfig(name="short", enabled=True),
                PluginConfig(name="never", enabled=True),
            ],
            registry=registry,
        )
        await manager.initialize()

        ctx = _make_ctx(mock_agent, event_sink=collector)
        short = await manager.run_phase(PluginPhase.PRE_MAIN_LOOP, ctx=ctx)

        assert isinstance(short, PluginShortCircuitResult)
        hook_names = [
            e["plugin_name"]
            for e in collector.events
            if e["type"] in ("plugin_hook_started", "plugin_hook_completed")
        ]
        assert hook_names == ["short", "short"]
        assert "never" not in hook_names
        assert collector.events[0]["plugin_count"] == 2

    async def test_hook_failure_emits_plugin_hook_failed_with_error_type(
        self, mock_agent
    ) -> None:
        registry = PluginRegistry()
        registry.register("failing", FailingPlugin)
        collector = EventCollector()
        manager = PluginManager(
            mock_agent,
            [PluginConfig(name="failing", enabled=True)],
            registry=registry,
        )
        await manager.initialize()

        ctx = _make_ctx(mock_agent, event_sink=collector)
        with pytest.raises(PluginErrorException):
            await manager.run_phase(PluginPhase.PRE_TASK, ctx=ctx)

        failed = [e for e in collector.events if e["type"] == "plugin_hook_failed"]
        assert len(failed) == 1
        assert failed[0]["phase"] == PluginPhase.PRE_TASK.value
        assert failed[0]["plugin_name"] == "failing"
        assert failed[0]["error"]["type"] == "plugin_hook_error"
        assert failed[0]["error"]["phase"] == PluginPhase.PRE_TASK.value

    async def test_all_events_include_timestamp(self, mock_agent) -> None:
        registry = PluginRegistry()
        registry.register("early", EarlyPlugin)
        collector = EventCollector()
        manager = PluginManager(
            mock_agent,
            [PluginConfig(name="early", enabled=True)],
            registry=registry,
        )
        await manager.initialize()

        ctx = _make_ctx(mock_agent, event_sink=collector)
        await manager.run_phase(PluginPhase.PRE_TASK, ctx=ctx)

        assert collector.events
        assert all("timestamp" in e for e in collector.events)
