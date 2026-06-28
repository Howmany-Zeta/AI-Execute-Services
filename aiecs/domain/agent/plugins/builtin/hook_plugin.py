# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
HookPlugin — declarative hooks.json consumer (§3, H0-03).

Priority 150 (PluginManager phase order). default_enabled=False for backward compatibility.
"""

from __future__ import annotations

import fnmatch
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from aiecs.domain.agent.plugins.base import BaseAgentPlugin
from aiecs.domain.agent.plugins.context import AgentPluginContext
from aiecs.domain.agent.plugins.hooks.dispatch import dispatch_agent_hook
from aiecs.domain.agent.plugins.hooks.events import AgentHookEvent
from aiecs.domain.agent.plugins.hooks.executor import AgentHookExecutionContext, AgentHookExecutor
from aiecs.domain.agent.plugins.hooks.prompt_client import resolve_hook_prompt_client
from aiecs.domain.agent.plugins.hooks.loader import HookLoadOptions, merge_hook_sources, resolve_manifest_hooks_path
from aiecs.domain.agent.plugins.hooks.payload import (
    build_iteration_end_payload,
    build_pre_main_loop_payload,
    build_session_end_payload,
    build_session_start_payload,
)
from aiecs.domain.agent.plugins.hooks.registry import AgentHookRegistry
from aiecs.domain.agent.plugins.hooks.types import AggregatedHookResult
from aiecs.domain.agent.plugins.models import PluginMetadata

if TYPE_CHECKING:
    from aiecs.domain.agent.base_agent import BaseAIAgent
    from aiecs.domain.agent.plugins.models import PluginConfig

logger = logging.getLogger(__name__)


class HookPlugin(BaseAgentPlugin):
    """Builtin hook plugin consuming hooks.json and manifest hook sources."""

    metadata: ClassVar[PluginMetadata] = PluginMetadata(
        name="hook",
        version="0.1.0",
        description="Declarative agent hooks (hooks.json subset)",
        priority=150,
        default_enabled=False,
    )

    def __init__(self, config: PluginConfig, agent: BaseAIAgent) -> None:
        super().__init__(config, agent)
        self._registry: AgentHookRegistry | None = None
        self._executor: AgentHookExecutor | None = None
        self._load_options = _load_options_from_config(config)
        self._fire_in_dawp_nested = bool(config.options.get("fire_in_dawp_nested", False))
        self._load_project_hooks = bool(config.options.get("load_project_hooks", False))

    @property
    def is_enabled(self) -> bool:
        return bool(self._config.enabled)

    @property
    def fire_in_dawp_nested(self) -> bool:
        return self._fire_in_dawp_nested

    @property
    def registry(self) -> AgentHookRegistry | None:
        return self._registry

    def confirm_tools_matcher(self) -> str | None:
        """Return ``confirm_tools`` glob matcher from plugin options, if configured."""
        matcher = self._config.options.get("confirm_tools")
        if isinstance(matcher, str) and matcher.strip():
            return matcher.strip()
        return None

    def tool_confirmation_reason(self, tool_name: str) -> str | None:
        """Return Host confirmation reason when ``tool_name`` matches ``confirm_tools``."""
        matcher = self.confirm_tools_matcher()
        if matcher and fnmatch.fnmatch(tool_name, matcher):
            return f"tool {tool_name!r} matches confirm_tools matcher"
        return None

    async def on_agent_init(self, ctx: AgentPluginContext) -> None:
        if not self.is_enabled:
            self._registry = None
            self._executor = None
            return
        self._registry = self._build_registry_from_static_sources()
        self._executor = self._create_executor()

        payload = build_session_start_payload(
            agent_id=getattr(self._agent, "agent_id", ""),
            session_id=ctx.context.get("session_id"),
            reason=ctx.context.get("session_start_reason") or ctx.context.get("session_reason"),
        )
        await dispatch_agent_hook(ctx, AgentHookEvent.SESSION_START, payload)

    async def on_agent_shutdown(self, ctx: AgentPluginContext) -> None:
        if self.is_enabled and self._executor is not None:
            payload = build_session_end_payload(
                agent_id=getattr(self._agent, "agent_id", ""),
                session_id=ctx.context.get("session_id"),
                reason=ctx.context.get("session_end_reason") or ctx.context.get("session_reason"),
            )
            await dispatch_agent_hook(ctx, AgentHookEvent.SESSION_END, payload)

        self._registry = None
        self._executor = None

    async def on_pre_main_loop(self, ctx: AgentPluginContext) -> None:
        """H11 — pre_main_loop hook before DAWP pre-loop drain (§7.1.6, H11-02)."""
        if not self.is_enabled:
            return None
        task = ctx.task or {}
        payload = build_pre_main_loop_payload(
            agent_id=getattr(self._agent, "agent_id", ""),
            task_id=task.get("task_id"),
        )
        result = await dispatch_agent_hook(ctx, AgentHookEvent.PRE_MAIN_LOOP, payload)
        if result.blocked:
            logger.warning("pre_main_loop hook blocked (block_on_failure); continuing main loop (v1 non-blocking)")
        return None

    async def on_iteration_end(
        self,
        ctx: AgentPluginContext,
        iteration: int,
        step: dict[str, Any],
    ) -> None:
        del step
        if not self.is_enabled:
            return
        pending = ctx.plugin_state.get("dawp.pending") or []
        pending_ids = [
            str(getattr(run, "workflow_id", run.get("workflow_id") if isinstance(run, dict) else ""))
            for run in pending
            if getattr(run, "workflow_id", None) or (isinstance(run, dict) and run.get("workflow_id"))
        ]
        payload = build_iteration_end_payload(
            agent_id=getattr(self._agent, "agent_id", ""),
            iteration=iteration,
            pending_count=len(pending) if isinstance(pending, list) else 0,
            pending_workflow_ids=pending_ids or None,
        )
        await dispatch_agent_hook(ctx, AgentHookEvent.ITERATION_END, payload)

    def rebuild_registry_for_task(self, ctx: AgentPluginContext) -> None:
        """Rebuild registry at task entry from static sources + hook_sources (§5.1.1)."""
        if not self.is_enabled:
            return
        sources = self._collect_static_sources()
        hook_sources = ctx.context.get("hook_sources")
        if isinstance(hook_sources, list):
            for index, source in enumerate(hook_sources):
                if isinstance(source, (str, Path)):
                    sources.append((f"hook_sources[{index}]", Path(source)))
                elif isinstance(source, dict):
                    sources.append((f"hook_sources[{index}]", source))

        self._registry = merge_hook_sources(sources, options=self._load_options)
        if self._executor is not None:
            self._executor.update_registry(self._registry)
        else:
            self._executor = self._create_executor()

    async def dispatch(self, event: AgentHookEvent, payload: dict[str, Any]) -> AggregatedHookResult:
        if not self.is_enabled or self._executor is None or self._registry is None:
            return AggregatedHookResult.empty()
        if not self._registry.get_hooks(event):
            return AggregatedHookResult.empty()
        return await self._executor.execute_event(event, payload)

    def _create_executor(self) -> AgentHookExecutor:
        options = self._config.options
        cwd = Path(str(options.get("workspace") or options.get("cwd") or Path.cwd()))
        allowed_hosts = options.get("hook_allowed_http_hosts") or []
        env_allowlist = options.get("hook_env_allowlist") or []
        hook_model = str(options.get("hook_model") or "")
        explicit_client = options.get("hook_api_client") or options.get("api_client")
        return AgentHookExecutor(
            self._registry or AgentHookRegistry(),
            AgentHookExecutionContext(
                cwd=cwd,
                default_model=hook_model,
                api_client=resolve_hook_prompt_client(
                    self._agent,
                    default_model=hook_model,
                    explicit_client=explicit_client,
                ),
                hook_allowed_http_hosts=frozenset(str(host) for host in allowed_hosts),
                hook_env_allowlist=frozenset(str(key) for key in env_allowlist),
                event_timeout_seconds=int(options.get("event_timeout_seconds", 60)),
            ),
        )

    def _build_registry_from_static_sources(self) -> AgentHookRegistry:
        return merge_hook_sources(self._collect_static_sources(), options=self._load_options)

    def _collect_static_sources(self) -> list[tuple[str, dict[str, Any] | Path]]:
        sources: list[tuple[str, dict[str, Any] | Path]] = []
        seen_paths: set[str] = set()

        for raw_path in self._config.options.get("paths") or []:
            path = Path(str(raw_path)).resolve()
            key = str(path)
            if key in seen_paths:
                continue
            seen_paths.add(key)
            sources.append((f"config:{path.name}", path))

        inline_hooks = self._config.options.get("inline_hooks")
        if isinstance(inline_hooks, dict):
            sources.append(("inline_hooks", {"hooks": inline_hooks}))

        manifests = getattr(self._agent, "_loaded_plugin_manifests", None) or []
        for manifest in manifests:
            hooks_value = getattr(manifest, "hooks", None)
            if hooks_value is None:
                continue
            manifest_dir = self._manifest_dir_for(manifest, hooks_value)
            resolved = resolve_manifest_hooks_path(hooks_value, manifest_dir)
            if isinstance(resolved, Path):
                key = str(resolved)
                if key not in seen_paths:
                    seen_paths.add(key)
                    sources.append((f"manifest:{manifest.name}", resolved))
            else:
                sources.append((f"manifest:{manifest.name}", resolved))

        if self._load_project_hooks:
            project_path = Path.cwd() / ".aiecs" / "hooks.json"
            key = str(project_path.resolve())
            if project_path.is_file() and key not in seen_paths:
                seen_paths.add(key)
                sources.append(("project", project_path))

        return sources

    def _manifest_dir_for(self, manifest: Any, hooks_value: str | dict[str, Any]) -> Path:
        """Resolve manifest directory for relative ``hooks`` paths (§9.1.1)."""
        agent_dirs = getattr(self._agent, "_manifest_dirs", None) or {}
        manifest_dir = agent_dirs.get(manifest.name)
        if manifest_dir is not None:
            return Path(manifest_dir)

        config_dirs = self._config.options.get("_manifest_dirs")
        if isinstance(config_dirs, dict) and isinstance(hooks_value, str):
            hooks_name = Path(hooks_value).name
            for path_str, dir_str in config_dirs.items():
                if Path(path_str).name == hooks_name:
                    return Path(dir_str)

        legacy_dir = self._config.options.get("_manifest_dir")
        if legacy_dir:
            return Path(str(legacy_dir))

        return Path.cwd()


def _load_options_from_config(config: PluginConfig) -> HookLoadOptions:
    options = config.options
    allow_command = bool(options.get("allow_command_hooks") or options.get("allow_shell_hooks"))
    return HookLoadOptions(
        allow_command_hooks=allow_command,
        strict_cc_hooks=bool(options.get("strict_cc_hooks", False)),
        enable_v2_hooks=bool(options.get("enable_v2_hooks", False)),
    )
