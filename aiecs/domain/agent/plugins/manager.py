# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
PluginManager orchestrates plugin lifecycle hooks (§5.6, §4.4, §6.3.6).
"""

from __future__ import annotations

import inspect
import time
from datetime import datetime
from typing import TYPE_CHECKING, Any

from aiecs.domain.agent.plugins.context import AgentPluginContext, PluginShortCircuitResult
from aiecs.domain.agent.plugins.errors import (
    PluginErrorException,
    PluginHookError,
    PluginInitError,
)
from aiecs.domain.agent.plugins.identifier import PluginOrigin, format_plugin_id
from aiecs.domain.agent.plugins.models import PluginConfig, PluginLoadResult, PluginPhase
from aiecs.domain.agent.plugins.registry import PluginRegistry

if TYPE_CHECKING:
    from aiecs.domain.agent.base_agent import BaseAIAgent
    from aiecs.domain.agent.plugins.base import BaseAgentPlugin

_BUILTIN_INIT_ORDER = ("tool", "skill", "memory")
_BUILTIN_NAMES = frozenset(_BUILTIN_INIT_ORDER)


class PluginManager:
    """
    Orchestrates in-process agent plugins across lifecycle phases.

    Builtin plugins (``origin=builtin``) initialize in fixed order: tool → skill → memory (§6.3.6).
    Other registered plugins follow, sorted by effective priority ascending.
    """

    def __init__(
        self,
        agent: BaseAIAgent,
        plugin_configs: list[PluginConfig],
        registry: PluginRegistry | None = None,
        *,
        continue_on_error: bool = False,
    ) -> None:
        self._agent = agent
        self._plugin_configs = list(plugin_configs)
        self._registry = registry or PluginRegistry.default()
        self._continue_on_error = continue_on_error
        self._plugins: dict[str, BaseAgentPlugin] = {}
        self._load_order: list[str] = []
        self._enabled_names: set[str] = set()
        self.last_load_result: PluginLoadResult = PluginLoadResult()
        self._agent._plugin_manager = self

    async def initialize(self, cache_only: bool = True) -> PluginLoadResult:
        """
        Create enabled plugins and run ``on_agent_init``.

        Args:
            cache_only: Accepted for API compatibility with §9.4. Phase 1 performs no
                remote or filesystem loading regardless of this flag (cache-only equivalent).

        Returns:
            Summary of enabled, disabled, and failed plugin IDs.

        Raises:
            PluginErrorException: Fail-fast when plugin creation or ``on_agent_init`` fails.
        """
        del cache_only

        self._plugins.clear()
        self._load_order.clear()
        self._enabled_names.clear()

        result = PluginLoadResult()
        init_ctx = AgentPluginContext(
            agent=self._agent,
            task={},
            context={},
            task_description="",
        )

        for config in self._plugin_configs:
            if not config.enabled:
                result.disabled.append(self._plugin_id(config.name))

        for config in self._enabled_init_order():
            plugin = self._registry.create(config, self._agent)
            plugin_id = self._plugin_id(config.name)

            try:
                await plugin.on_agent_init(init_ctx)
            except Exception as exc:
                raise PluginErrorException(
                    PluginInitError(
                        message=f"on_agent_init failed for {config.name!r}: {exc}",
                        plugin_id=plugin_id,
                        details={"error_type": type(exc).__name__},
                    )
                ) from exc

            self._plugins[config.name] = plugin
            self._load_order.append(config.name)
            self._enabled_names.add(config.name)
            result.enabled.append(plugin_id)

        self.last_load_result = result
        return result

    async def shutdown(self) -> None:
        """Run ``on_agent_shutdown`` in reverse initialization order."""
        if not self._load_order:
            return

        ctx = AgentPluginContext(
            agent=self._agent,
            task={},
            context={},
            task_description="",
        )
        for name in reversed(self._load_order):
            plugin = self._plugins.get(name)
            if plugin is None:
                continue
            await self._invoke_hook(
                plugin,
                "on_agent_shutdown",
                PluginPhase.AGENT_SHUTDOWN,
                ctx,
            )

    async def run_phase(self, phase: PluginPhase, **kwargs: Any) -> Any:
        """
        Execute a lifecycle phase across enabled, loaded plugins.

        See §5.6 for chaining (``BUILD_MESSAGES``, ``POST_TASK``) and short-circuit
        (``PRE_MAIN_LOOP``) semantics.
        """
        ctx = kwargs.get("ctx")
        if not isinstance(ctx, AgentPluginContext):
            raise ValueError("run_phase requires ctx=AgentPluginContext")

        plugins = self._plugins_for_phase(phase)
        await self._emit_plugin_framework_event(
            ctx,
            {
                "type": "plugin_phase_started",
                "phase": phase.value,
                "plugin_count": len(plugins),
            },
        )

        if phase == PluginPhase.BUILD_MESSAGES:
            messages = list(kwargs["messages"])
            for plugin in plugins:
                messages = await self._invoke_hook(
                    plugin,
                    "on_build_messages",
                    phase,
                    ctx,
                    messages=messages,
                )
            return messages

        if phase == PluginPhase.POST_TASK:
            result = dict(kwargs["result"])
            for plugin in plugins:
                result = await self._invoke_hook(
                    plugin,
                    "on_post_task",
                    phase,
                    ctx,
                    result=result,
                )
            return result

        if phase == PluginPhase.PRE_MAIN_LOOP:
            for plugin in plugins:
                short = await self._invoke_hook(
                    plugin,
                    "on_pre_main_loop",
                    phase,
                    ctx,
                )
                if isinstance(short, PluginShortCircuitResult):
                    return short
            return None

        hook_map = {
            PluginPhase.AGENT_INIT: "on_agent_init",
            PluginPhase.AGENT_SHUTDOWN: "on_agent_shutdown",
            PluginPhase.PRE_TASK: "on_pre_task",
            PluginPhase.ON_ITERATION_START: "on_iteration_start",
            PluginPhase.ON_ITERATION_END: "on_iteration_end",
        }
        hook_name = hook_map.get(phase)
        if hook_name is None:
            raise ValueError(f"unsupported phase: {phase}")

        extra = {key: value for key, value in kwargs.items() if key != "ctx"}
        for plugin in plugins:
            await self._invoke_hook(plugin, hook_name, phase, ctx, **extra)
        return None

    def get_plugin(self, name: str) -> BaseAgentPlugin | None:
        """Return a loaded plugin instance by short name."""
        return self._plugins.get(name)

    def is_enabled(self, name: str) -> bool:
        """Whether ``name`` is enabled in the resolved configuration."""
        return name in self._enabled_names

    def plugin_ids(self) -> list[str]:
        """Canonical plugin IDs for loaded plugins in initialization order."""
        return [self._plugin_id(name) for name in self._load_order]

    def _plugins_for_phase(self, phase: PluginPhase) -> list[BaseAgentPlugin]:
        if phase == PluginPhase.AGENT_SHUTDOWN:
            return [self._plugins[name] for name in reversed(self._load_order) if name in self._plugins]

        configs = [config for config in self._plugin_configs if config.enabled and config.name in self._plugins]
        configs.sort(key=self._effective_priority)
        return [self._plugins[config.name] for config in configs]

    def _enabled_init_order(self) -> list[PluginConfig]:
        """Order enabled configs: builtin fixed order, then others by priority (§6.3.6)."""
        enabled = [config for config in self._plugin_configs if config.enabled]
        builtin: list[PluginConfig] = []
        other: list[PluginConfig] = []

        for config in enabled:
            entry = self._registry.get_entry(config.name)
            if config.name in _BUILTIN_NAMES and entry is not None and entry.origin == PluginOrigin.BUILTIN:
                builtin.append(config)
            else:
                other.append(config)

        builtin.sort(key=lambda cfg: _BUILTIN_INIT_ORDER.index(cfg.name))
        other.sort(key=self._effective_priority)
        return builtin + other

    def _effective_priority(self, config: PluginConfig) -> int:
        if config.priority is not None:
            return config.priority
        entry = self._registry.get_entry(config.name)
        if entry is not None:
            return entry.metadata.priority
        return 100

    def _plugin_id(self, name: str) -> str:
        entry = self._registry.get_entry(name)
        origin = entry.origin if entry is not None else PluginOrigin.REGISTRY
        return format_plugin_id(name, origin)

    async def _emit_plugin_framework_event(
        self,
        ctx: AgentPluginContext,
        event: dict[str, Any],
    ) -> None:
        """Forward framework streaming events to ``ctx.event_sink`` when set (§10.3)."""
        sink = ctx.event_sink
        if sink is None:
            return
        payload = dict(event)
        payload.setdefault("timestamp", datetime.utcnow().isoformat())
        result = sink(payload)
        if inspect.isawaitable(result):
            await result

    async def _invoke_hook(
        self,
        plugin: BaseAgentPlugin,
        hook_name: str,
        phase: PluginPhase,
        ctx: AgentPluginContext,
        **hook_kwargs: Any,
    ) -> Any:
        await self._emit_plugin_framework_event(
            ctx,
            {
                "type": "plugin_hook_started",
                "phase": phase.value,
                "plugin_name": plugin.metadata.name,
            },
        )
        started = time.perf_counter()
        try:
            hook = getattr(plugin, hook_name)
            if hook_kwargs:
                result = await hook(ctx, **hook_kwargs)
            else:
                result = await hook(ctx)
            await self._emit_plugin_framework_event(
                ctx,
                {
                    "type": "plugin_hook_completed",
                    "phase": phase.value,
                    "plugin_name": plugin.metadata.name,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 3),
                },
            )
            return result
        except Exception as exc:
            plugin_id = self._plugin_id(plugin.metadata.name)
            error = PluginHookError(
                message=f"{hook_name} failed for {plugin.metadata.name!r}: {exc}",
                plugin_id=plugin_id,
                phase=phase,
                details={"error_type": type(exc).__name__},
            )
            await self._emit_plugin_framework_event(
                ctx,
                {
                    "type": "plugin_hook_failed",
                    "phase": phase.value,
                    "plugin_name": plugin.metadata.name,
                    "error": error.model_dump(mode="json"),
                },
            )
            if self._continue_on_error:
                self.last_load_result.errors.append(error)
                return hook_kwargs.get("messages") or hook_kwargs.get("result")
            raise PluginErrorException(error) from exc
