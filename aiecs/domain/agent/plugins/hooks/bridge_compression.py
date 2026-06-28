# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Compression hook bridge — merges legacy HookExecutor with hooks.json H3/H4 (§6.7, D-10)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from aiecs.domain.agent.plugins.hooks.dispatch import dispatch_agent_hook
from aiecs.domain.agent.plugins.hooks.events import AgentHookEvent
from aiecs.domain.agent.plugins.hooks.payload import (
    build_post_compact_payload,
    build_pre_compact_payload,
)
from aiecs.domain.context.compression.hooks import HookExecutor, HookRegistry
from aiecs.domain.context.compression.types import (
    PostCompactContext,
    PreCompactContext,
    PreCompactResult,
)

if TYPE_CHECKING:
    from aiecs.domain.agent.plugins.context import AgentPluginContext


def resolve_bridged_compression_hooks(
    compression_hooks: HookExecutor | None,
    plugin_ctx: AgentPluginContext | None,
) -> HookExecutor | None:
    """Return bridged HookExecutor when HookPlugin is enabled; else legacy hooks only."""
    if plugin_ctx is None or not _hook_plugin_enabled(plugin_ctx):
        return compression_hooks
    bridged = BridgedCompactHookExecutor(compression_hooks, plugin_ctx)
    if not bridged.registry.pre_hooks and not bridged.registry.post_hooks:
        return compression_hooks
    return bridged


def _hook_plugin_enabled(plugin_ctx: AgentPluginContext) -> bool:
    from aiecs.domain.agent.plugins.builtin.hook_plugin import HookPlugin

    plugin = plugin_ctx.get_plugin("hook")
    return isinstance(plugin, HookPlugin) and plugin.is_enabled


def _agent_id(plugin_ctx: AgentPluginContext) -> str:
    return str(getattr(plugin_ctx.agent, "agent_id", ""))


def _agent_has_hooks(plugin_ctx: AgentPluginContext, event: AgentHookEvent) -> bool:
    from aiecs.domain.agent.plugins.builtin.hook_plugin import HookPlugin

    plugin = plugin_ctx.get_plugin("hook")
    if not isinstance(plugin, HookPlugin) or plugin.registry is None:
        return False
    return bool(plugin.registry.get_hooks(event))


class BridgedCompactHookExecutor(HookExecutor):
    """HookExecutor-compatible adapter with D-10 ordering."""

    def __init__(
        self,
        compression_hooks: HookExecutor | None,
        plugin_ctx: AgentPluginContext,
    ) -> None:
        self._compression = compression_hooks
        self._plugin_ctx = plugin_ctx
        super().__init__(HookRegistry())

        if self._has_pre_source():
            self.registry.register_pre(self._execute_pre_compact)
        if self._has_post_source():
            self.registry.register_post(self._execute_post_compact)

    def _has_pre_source(self) -> bool:
        if self._compression and self._compression.registry.pre_hooks:
            return True
        return _agent_has_hooks(self._plugin_ctx, AgentHookEvent.PRE_COMPACT)

    def _has_post_source(self) -> bool:
        if self._compression and self._compression.registry.post_hooks:
            return True
        return _agent_has_hooks(self._plugin_ctx, AgentHookEvent.POST_COMPACT)

    async def execute_pre_compact(self, ctx: PreCompactContext) -> PreCompactResult:
        return await self._execute_pre_compact(ctx)

    async def execute_post_compact(self, ctx: PostCompactContext) -> None:
        await self._execute_post_compact(ctx)

    async def _execute_pre_compact(self, ctx: PreCompactContext) -> PreCompactResult:
        merged = PreCompactResult()
        if self._compression and self._compression.registry.pre_hooks:
            compression_result = await self._compression.execute_pre_compact(ctx)
            merged.block = compression_result.block
            merged.append_instructions = compression_result.append_instructions

        if _agent_has_hooks(self._plugin_ctx, AgentHookEvent.PRE_COMPACT):
            agent_result = await dispatch_agent_hook(
                self._plugin_ctx,
                AgentHookEvent.PRE_COMPACT,
                build_pre_compact_payload(
                    agent_id=_agent_id(self._plugin_ctx),
                    trigger=str(ctx.trigger),
                    message_count=len(ctx.messages),
                    metadata=ctx.metadata,
                ),
            )
            if agent_result.blocked:
                merged.block = True
            agent_instructions = agent_result.modified_output
            if agent_instructions:
                if merged.append_instructions:
                    merged.append_instructions = f"{merged.append_instructions}\n{agent_instructions}"
                else:
                    merged.append_instructions = agent_instructions
        return merged

    async def _execute_post_compact(self, ctx: PostCompactContext) -> None:
        trigger = "auto"
        compact_kind = None
        if ctx.result is not None:
            trigger = str(getattr(ctx.result, "trigger", "auto"))
            compact_kind = getattr(ctx.result, "compact_kind", None)

        if _agent_has_hooks(self._plugin_ctx, AgentHookEvent.POST_COMPACT):
            post_metadata = dict(ctx.metadata)
            if ctx.result is not None:
                compact_meta = getattr(ctx.result, "compact_metadata", None) or {}
                checkpoint = compact_meta.get("checkpoint")
                if checkpoint:
                    post_metadata.setdefault("checkpoint", checkpoint)
            await dispatch_agent_hook(
                self._plugin_ctx,
                AgentHookEvent.POST_COMPACT,
                build_post_compact_payload(
                    agent_id=_agent_id(self._plugin_ctx),
                    trigger=trigger,
                    summary_preview=ctx.summary_text,
                    compact_kind=str(compact_kind) if compact_kind is not None else None,
                    metadata=post_metadata or None,
                ),
            )

        if self._compression and self._compression.registry.post_hooks:
            await self._compression.execute_post_compact(ctx)
