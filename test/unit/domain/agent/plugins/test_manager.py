"""
Unit tests for PluginManager (§5.6, T-08–T-12, T-11 POST_TASK chain).
"""

import pytest

from aiecs.domain.agent.plugins.base import BaseAgentPlugin
from aiecs.domain.agent.plugins.context import AgentPluginContext, PluginShortCircuitResult
from aiecs.domain.agent.plugins.errors import (
    PluginErrorException,
    PluginHookError,
    PluginInitError,
)
from aiecs.domain.agent.plugins.manager import PluginManager
from aiecs.domain.agent.plugins.models import PluginConfig, PluginMetadata, PluginPhase
from aiecs.domain.agent.plugins.registry import PluginRegistry


def _make_ctx(mock_agent, plugin_state: dict | None = None) -> AgentPluginContext:
    return AgentPluginContext(
        agent=mock_agent,
        task={"description": "test task"},
        context={},
        task_description="test task",
        plugin_state=plugin_state or {},
    )


class EarlyPlugin(BaseAgentPlugin):
    """Runs before LatePlugin (priority 50)."""

    metadata = PluginMetadata(name="early", version="1.0.0", description="early", priority=50)

    async def on_pre_task(self, ctx: AgentPluginContext) -> None:
        ctx.plugin_state.setdefault("pre_task_order", []).append("early")


class LatePlugin(BaseAgentPlugin):
    """Runs after EarlyPlugin (priority 200)."""

    metadata = PluginMetadata(name="late", version="1.0.0", description="late", priority=200)

    async def on_pre_task(self, ctx: AgentPluginContext) -> None:
        ctx.plugin_state.setdefault("pre_task_order", []).append("late")


class TrackingPlugin(BaseAgentPlugin):
    """Records hook invocations on ``agent._hook_order`` when present."""

    metadata = PluginMetadata(name="tracker", version="1.0.0", description="tracker", priority=10)

    def _record(self, ctx: AgentPluginContext, event: str) -> None:
        order = getattr(ctx.agent, "_hook_order", None)
        if order is not None:
            order.append((event, self._config.name))

    async def on_agent_init(self, ctx: AgentPluginContext) -> None:
        self._record(ctx, "init")

    async def on_agent_shutdown(self, ctx: AgentPluginContext) -> None:
        self._record(ctx, "shutdown")

    async def on_pre_task(self, ctx: AgentPluginContext) -> None:
        ctx.plugin_state.setdefault("pre_task_calls", []).append(self.metadata.name)


class AppendMessagePlugin(BaseAgentPlugin):
    """Appends a marker message."""

    metadata = PluginMetadata(name="append_a", version="1.0.0", description="append a", priority=10)

    async def on_build_messages(self, ctx, messages):
        return [*messages, {"role": "system", "content": "from-a"}]


class ReadMessagePlugin(BaseAgentPlugin):
    """Asserts prior plugin output is visible."""

    metadata = PluginMetadata(name="append_b", version="1.0.0", description="append b", priority=20)

    async def on_build_messages(self, ctx, messages):
        ctx.plugin_state["saw_a"] = any(msg.get("content") == "from-a" for msg in messages)
        return messages


class TagResultPlugin(BaseAgentPlugin):
    """Adds a marker to the task result dict."""

    metadata = PluginMetadata(name="tag_a", version="1.0.0", description="tag a", priority=10)

    async def on_post_task(self, ctx, result):
        return {**result, "tag": "from-a"}


class ReadResultPlugin(BaseAgentPlugin):
    """Asserts prior plugin output is visible in POST_TASK chain."""

    metadata = PluginMetadata(name="tag_b", version="1.0.0", description="tag b", priority=20)

    async def on_post_task(self, ctx, result):
        ctx.plugin_state["saw_tag"] = result.get("tag") == "from-a"
        return result


class ShortCircuitPlugin(BaseAgentPlugin):
    """Short-circuits PRE_MAIN_LOOP."""

    metadata = PluginMetadata(name="short", version="1.0.0", description="short", priority=10)

    async def on_pre_main_loop(self, ctx):
        return PluginShortCircuitResult(
            result={"final_response": "short"},
            source_plugin_id="short@registry",
        )


class NeverCalledPlugin(BaseAgentPlugin):
    """Must not run when short-circuit happens first."""

    metadata = PluginMetadata(name="never", version="1.0.0", description="never", priority=20)

    async def on_pre_main_loop(self, ctx):
        ctx.plugin_state["never_called"] = True
        return None


class FailingPlugin(BaseAgentPlugin):
    """Raises from hooks."""

    metadata = PluginMetadata(name="failing", version="1.0.0", description="failing", priority=10)

    async def on_pre_task(self, ctx):
        raise RuntimeError("hook boom")


@pytest.mark.unit
@pytest.mark.asyncio
class TestPluginManagerInitialize:
    """Initialize and shutdown ordering."""

    async def test_initialize_returns_load_result(self, mock_agent):
        registry = PluginRegistry.default()
        configs = [
            PluginConfig(name="tool", enabled=True),
            PluginConfig(name="skill", enabled=False),
            PluginConfig(name="memory", enabled=True),
        ]
        manager = PluginManager(mock_agent, configs, registry=registry)
        result = await manager.initialize()

        assert "tool@builtin" in result.enabled
        assert "memory@builtin" in result.enabled
        assert "skill@builtin" in result.disabled
        assert mock_agent._plugin_manager is manager

    async def test_builtin_init_order_tool_skill_memory(self, mock_agent):
        registry = PluginRegistry.default()
        configs = [
            PluginConfig(name="memory", enabled=True),
            PluginConfig(name="tool", enabled=True),
            PluginConfig(name="skill", enabled=True),
        ]
        manager = PluginManager(mock_agent, configs, registry=registry)
        await manager.initialize()

        assert manager._load_order == ["tool", "skill", "memory"]

    async def test_shutdown_reverse_of_init(self, mock_agent):
        registry = PluginRegistry()
        registry.register(
            "first",
            TrackingPlugin,
            metadata=PluginMetadata(name="first", version="1", description="", priority=10),
        )
        registry.register(
            "second",
            TrackingPlugin,
            metadata=PluginMetadata(name="second", version="1", description="", priority=20),
        )

        configs = [
            PluginConfig(name="first", enabled=True),
            PluginConfig(name="second", enabled=True),
        ]
        mock_agent._hook_order = []
        manager = PluginManager(mock_agent, configs, registry=registry)
        await manager.initialize()
        await manager.shutdown()

        assert mock_agent._hook_order == [
            ("init", "first"),
            ("init", "second"),
            ("shutdown", "second"),
            ("shutdown", "first"),
        ]


@pytest.mark.unit
@pytest.mark.asyncio
class TestPluginManagerRunPhase:
    """run_phase behavior."""

    async def test_priority_order_on_pre_task(self, mock_agent):
        registry = PluginRegistry()
        registry.register("early", EarlyPlugin)
        registry.register("late", LatePlugin)

        manager = PluginManager(
            mock_agent,
            [
                PluginConfig(name="late", enabled=True),
                PluginConfig(name="early", enabled=True),
            ],
            registry=registry,
        )
        await manager.initialize()

        ctx = _make_ctx(mock_agent)
        await manager.run_phase(PluginPhase.PRE_TASK, ctx=ctx)

        assert ctx.plugin_state["pre_task_order"] == ["early", "late"]

    async def test_disabled_plugin_skips_hooks(self, mock_agent):
        registry = PluginRegistry()
        registry.register("tracker", TrackingPlugin)

        manager = PluginManager(
            mock_agent,
            [
                PluginConfig(name="tracker", enabled=True),
                PluginConfig(name="ghost", enabled=False),
            ],
            registry=registry,
        )
        await manager.initialize()

        ctx = _make_ctx(mock_agent)
        await manager.run_phase(PluginPhase.PRE_TASK, ctx=ctx)

        assert ctx.plugin_state["pre_task_calls"] == ["tracker"]
        assert manager.get_plugin("ghost") is None
        assert manager.is_enabled("ghost") is False

    async def test_build_messages_chaining(self, mock_agent):
        registry = PluginRegistry()
        registry.register("append_a", AppendMessagePlugin)
        registry.register("append_b", ReadMessagePlugin)

        manager = PluginManager(
            mock_agent,
            [
                PluginConfig(name="append_a", enabled=True),
                PluginConfig(name="append_b", enabled=True),
            ],
            registry=registry,
        )
        await manager.initialize()

        ctx = _make_ctx(mock_agent)
        messages = [{"role": "user", "content": "hi"}]
        result = await manager.run_phase(
            PluginPhase.BUILD_MESSAGES,
            ctx=ctx,
            messages=messages,
        )

        assert result[-1]["content"] == "from-a"
        assert ctx.plugin_state["saw_a"] is True

    async def test_post_task_chaining(self, mock_agent):
        registry = PluginRegistry()
        registry.register("tag_a", TagResultPlugin)
        registry.register("tag_b", ReadResultPlugin)

        manager = PluginManager(
            mock_agent,
            [
                PluginConfig(name="tag_a", enabled=True),
                PluginConfig(name="tag_b", enabled=True),
            ],
            registry=registry,
        )
        await manager.initialize()

        ctx = _make_ctx(mock_agent)
        result = await manager.run_phase(
            PluginPhase.POST_TASK,
            ctx=ctx,
            result={"status": "ok"},
        )

        assert result["tag"] == "from-a"
        assert ctx.plugin_state["saw_tag"] is True

    async def test_pre_main_loop_short_circuit(self, mock_agent):
        registry = PluginRegistry()
        registry.register("short", ShortCircuitPlugin)
        registry.register("never", NeverCalledPlugin)

        manager = PluginManager(
            mock_agent,
            [
                PluginConfig(name="short", enabled=True),
                PluginConfig(name="never", enabled=True),
            ],
            registry=registry,
        )
        await manager.initialize()

        ctx = _make_ctx(mock_agent)
        short = await manager.run_phase(PluginPhase.PRE_MAIN_LOOP, ctx=ctx)

        assert isinstance(short, PluginShortCircuitResult)
        assert short.result["final_response"] == "short"
        assert "never_called" not in ctx.plugin_state

    async def test_hook_failure_raises_plugin_hook_error(self, mock_agent):
        registry = PluginRegistry()
        registry.register("failing", FailingPlugin)

        manager = PluginManager(
            mock_agent,
            [PluginConfig(name="failing", enabled=True)],
            registry=registry,
        )
        await manager.initialize()

        ctx = _make_ctx(mock_agent)
        with pytest.raises(PluginErrorException) as exc_info:
            await manager.run_phase(PluginPhase.PRE_TASK, ctx=ctx)

        assert isinstance(exc_info.value.error, PluginHookError)
        assert exc_info.value.error.phase == PluginPhase.PRE_TASK
        assert exc_info.value.error.type == "plugin_hook_error"

    async def test_init_failure_raises_plugin_init_error(self, mock_agent):
        class BrokenInitPlugin(BaseAgentPlugin):
            metadata = PluginMetadata(name="broken", version="1", description="broken")

            def __init__(self, config, agent):
                raise RuntimeError("init failed")

        registry = PluginRegistry()
        registry.register("broken", BrokenInitPlugin)

        manager = PluginManager(
            mock_agent,
            [PluginConfig(name="broken", enabled=True)],
            registry=registry,
        )

        with pytest.raises(PluginErrorException) as exc_info:
            await manager.initialize()

        assert isinstance(exc_info.value.error, PluginInitError)
