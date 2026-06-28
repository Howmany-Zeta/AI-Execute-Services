# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Unified agent hook dispatch entry (§6.5, D-08)."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

from aiecs.domain.agent.plugins.hooks.events import AgentHookEvent
from aiecs.domain.agent.plugins.hooks.types import AggregatedHookResult

if TYPE_CHECKING:
    from aiecs.domain.agent.plugins.builtin.hook_plugin import HookPlugin
    from aiecs.domain.agent.plugins.context import AgentPluginContext

logger = logging.getLogger(__name__)


async def dispatch_agent_hook(
    ctx: AgentPluginContext,
    event: AgentHookEvent,
    payload: dict[str, Any],
    *,
    nested: bool = False,
) -> AggregatedHookResult:
    """
    Dispatch hooks for a hot-path event.

    Returns empty result when HookPlugin is disabled, missing, or nested hooks are off.
    """
    plugin = _get_hook_plugin(ctx)
    if plugin is None:
        return AggregatedHookResult.empty()

    if nested and not plugin.fire_in_dawp_nested:
        return AggregatedHookResult.empty()

    start = time.perf_counter()
    result = await plugin.dispatch(event, payload)
    duration_ms = (time.perf_counter() - start) * 1000.0
    await _emit_agent_hook_event(ctx, event, result, duration_ms)
    return result


def _get_hook_plugin(ctx: AgentPluginContext) -> HookPlugin | None:
    from aiecs.domain.agent.plugins.builtin.hook_plugin import HookPlugin

    plugin = ctx.get_plugin("hook")
    if plugin is None or not isinstance(plugin, HookPlugin):
        return None
    if not plugin.is_enabled:
        return None
    return plugin


def has_registered_hooks(ctx: AgentPluginContext, event: AgentHookEvent) -> bool:
    """Return True when HookPlugin has hooks registered for ``event``."""
    plugin = _get_hook_plugin(ctx)
    if plugin is None or plugin.registry is None:
        return False
    return bool(plugin.registry.get_hooks(event))


async def _emit_agent_hook_event(
    ctx: AgentPluginContext,
    event: AgentHookEvent,
    result: AggregatedHookResult,
    duration_ms: float,
) -> None:
    sink = ctx.event_sink
    if sink is None:
        return
    event_payload = {
        "type": "agent_hook",
        "event": event.value,
        "blocked": result.blocked,
        "hook_count": len(result.results),
        "duration_ms": round(duration_ms, 2),
    }
    try:
        emitted = sink(event_payload)
        if hasattr(emitted, "__await__"):
            await emitted
    except Exception:
        logger.debug("failed to emit agent_hook event", exc_info=True)
