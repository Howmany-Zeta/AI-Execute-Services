# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Load hooks from hooks.json and merge sources (§4.4, §5.1.1)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter, ValidationError

from aiecs.domain.agent.plugins.errors import PluginConfigErrorException, raise_plugin_config_error
from aiecs.domain.agent.plugins.hooks.events import AgentHookEvent
from aiecs.domain.agent.plugins.hooks.registry import AgentHookRegistry
from aiecs.domain.agent.plugins.hooks.schemas import (
    AgentHookDefinition,
    CommandHookDefinition,
    HookDefinition,
    HttpHookDefinition,
    PromptHookDefinition,
)

logger = logging.getLogger(__name__)

_HOOK_DEFINITION_ADAPTER: TypeAdapter[HookDefinition] = TypeAdapter(HookDefinition)

# §4.4 PascalCase alias map
_EVENT_ALIASES: dict[str, AgentHookEvent] = {
    "PreToolUse": AgentHookEvent.PRE_TOOL_USE,
    "PostToolUse": AgentHookEvent.POST_TOOL_USE,
    "PreCompact": AgentHookEvent.PRE_COMPACT,
    "PostCompact": AgentHookEvent.POST_COMPACT,
    "UserPromptSubmit": AgentHookEvent.USER_PROMPT_SUBMIT,
    "Stop": AgentHookEvent.STOP,
    "Notification": AgentHookEvent.NOTIFICATION,
    "SessionStart": AgentHookEvent.SESSION_START,
    "SessionEnd": AgentHookEvent.SESSION_END,
    "SubagentStop": AgentHookEvent.DAWP_RUN_END,
    "subagent_stop": AgentHookEvent.DAWP_RUN_END,
    "PermissionRequest": AgentHookEvent.PERMISSION_REQUEST,
    "permission_request": AgentHookEvent.PERMISSION_REQUEST,
    "PermissionDenied": AgentHookEvent.PERMISSION_DENIED,
    "permission_denied": AgentHookEvent.PERMISSION_DENIED,
    "PostToolUseFailure": AgentHookEvent.POST_TOOL_USE_FAILURE,
    "post_tool_use_failure": AgentHookEvent.POST_TOOL_USE_FAILURE,
    "UserPromptInHistory": AgentHookEvent.USER_PROMPT_IN_HISTORY,
    "user_prompt_in_history": AgentHookEvent.USER_PROMPT_IN_HISTORY,
    "SubagentStart": AgentHookEvent.SUBAGENT_START,
    "subagent_start": AgentHookEvent.SUBAGENT_START,
    "StopFailure": AgentHookEvent.STOP_FAILURE,
    "stop_failure": AgentHookEvent.STOP_FAILURE,
    "TaskCompleted": AgentHookEvent.TASK_COMPLETED,
    "task_completed": AgentHookEvent.TASK_COMPLETED,
}

# ADR-002 deferred CC events (warn, do not register; v2 P0/P1 events use _EVENT_ALIASES)
_CC_DEFERRED_ALIASES: frozenset[str] = frozenset(
    {
        "setup",
        "TeammateIdle",
        "teammate_idle",
        "TaskCreated",
        "task_created",
        "Setup",
        "elicitation",
        "ElicitationResult",
        "elicitation_result",
        "ConfigChange",
        "config_change",
        "WorktreeCreate",
        "worktree_create",
        "WorktreeRemove",
        "worktree_remove",
        "InstructionsLoaded",
        "instructions_loaded",
        "CwdChanged",
        "cwd_changed",
        "FileChanged",
        "file_changed",
    }
)


class HookLoadOptions:
    """Loader options from HookPlugin config (§12.1)."""

    def __init__(
        self,
        *,
        allow_command_hooks: bool = False,
        allow_shell_hooks: bool | None = None,
        strict_cc_hooks: bool = False,
        enable_v2_hooks: bool = False,
    ) -> None:
        self.allow_command_hooks = allow_command_hooks or bool(allow_shell_hooks)
        self.strict_cc_hooks = strict_cc_hooks
        self.enable_v2_hooks = enable_v2_hooks


def _notification_v2_enabled(options: HookLoadOptions) -> bool:
    return bool(options.enable_v2_hooks)


def normalize_event_key(raw_key: str, *, options: HookLoadOptions) -> AgentHookEvent | None:
    """Map hooks.json event key to AgentHookEvent; warn on deferred CC events."""
    if raw_key in _EVENT_ALIASES:
        event = _EVENT_ALIASES[raw_key]
        if event == AgentHookEvent.NOTIFICATION and not _notification_v2_enabled(options):
            logger.warning("hooks.json notification entries are not executable in v1; " "use dispatch_host_notification() Host callback instead (§5.3)")
            return None
        if event == AgentHookEvent.DAWP_RUN_END and raw_key in {"SubagentStop", "subagent_stop"}:
            logger.warning("subagent_stop is a deprecated alias for dawp_run_end (§4.3)")
        return event
    if raw_key in _CC_DEFERRED_ALIASES:
        message = f"hooks.json event {raw_key!r} is not implemented in v1 (ADR-002)"
        if options.strict_cc_hooks:
            raise_plugin_config_error(message, plugin_id="hook@builtin")
        logger.warning(message)
        return None
    try:
        event = AgentHookEvent(raw_key)
    except ValueError:
        message = f"unknown hooks.json event key: {raw_key!r}"
        if options.strict_cc_hooks:
            raise_plugin_config_error(message, plugin_id="hook@builtin")
        logger.warning(message)
        return None

    if event == AgentHookEvent.NOTIFICATION and not _notification_v2_enabled(options):
        logger.warning("hooks.json notification entries are not executable in v1; " "use dispatch_host_notification() Host callback instead (§5.3)")
        return None
    if event == AgentHookEvent.SUBAGENT_STOP:
        logger.warning("subagent_stop is a deprecated alias for dawp_run_end (§4.3)")
        return AgentHookEvent.DAWP_RUN_END
    return event


def hook_fingerprint(hook: HookDefinition) -> tuple[str, str, str | None]:
    """Stable dedupe key (§5.1.1)."""
    if isinstance(hook, CommandHookDefinition):
        command = hook.command if isinstance(hook.command, str) else " ".join(hook.command)
        return (hook.type, command, hook.matcher)
    if isinstance(hook, HttpHookDefinition):
        return (hook.type, hook.url, hook.matcher)
    if isinstance(hook, (PromptHookDefinition, AgentHookDefinition)):
        return (hook.type, hook.prompt, hook.matcher)
    return (getattr(hook, "type", "unknown"), "", hook.matcher)


def parse_hook_definition(raw: dict[str, Any]) -> HookDefinition:
    """Parse one hook definition; fail-fast on invalid type."""
    hook_type = raw.get("type")
    if hook_type not in {"command", "http", "prompt", "agent"}:
        raise_plugin_config_error(
            f"invalid hook type: {hook_type!r}",
            plugin_id="hook@builtin",
        )
    try:
        return _HOOK_DEFINITION_ADAPTER.validate_python(raw)
    except ValidationError as exc:
        raise PluginConfigErrorException(
            f"invalid hook definition: {exc}",
            plugin_id="hook@builtin",
        ) from exc


def _validate_command_hook_allowed(hook: HookDefinition, options: HookLoadOptions) -> None:
    if isinstance(hook, CommandHookDefinition) and not options.allow_command_hooks:
        raise_plugin_config_error(
            "command hooks require allow_command_hooks=true (§12.1)",
            plugin_id="hook@builtin",
        )


def _apply_wrapper_matcher(raw_hook: dict[str, Any], outer_matcher: Any) -> dict[str, Any]:
    """Apply CC wrapper ``matcher`` when a nested hook has no explicit matcher."""
    if not isinstance(outer_matcher, str) or not outer_matcher.strip():
        return raw_hook
    merged = dict(raw_hook)
    if not merged.get("matcher"):
        merged["matcher"] = outer_matcher.strip()
    return merged


def _coerce_hooks_list(raw_hooks: Any, event_key: str) -> list[Any]:
    """Accept flat array or CC-style {matcher, hooks:[]} wrapper."""
    if isinstance(raw_hooks, list):
        return raw_hooks
    if isinstance(raw_hooks, dict) and "hooks" in raw_hooks:
        nested = raw_hooks.get("hooks")
        if not isinstance(nested, list):
            return []
        outer_matcher = raw_hooks.get("matcher")
        return [_apply_wrapper_matcher(item, outer_matcher) for item in nested if isinstance(item, dict)]
    raise_plugin_config_error(
        f"hooks for event {event_key!r} must be a list",
        plugin_id="hook@builtin",
    )


def load_hooks_from_json(
    data: dict[str, Any],
    registry: AgentHookRegistry,
    *,
    options: HookLoadOptions | None = None,
    seen_fingerprints: set[tuple[str, str, str | None]] | None = None,
) -> None:
    """Parse hooks.json content and append into registry (§5.1.1)."""
    opts = options or HookLoadOptions()
    fingerprints = seen_fingerprints if seen_fingerprints is not None else set()
    hooks_section = data.get("hooks", data)
    if not isinstance(hooks_section, dict):
        raise_plugin_config_error(
            "hooks.json root must contain a hooks mapping",
            plugin_id="hook@builtin",
        )

    for raw_event, raw_hooks in hooks_section.items():
        event = normalize_event_key(str(raw_event), options=opts)
        if event is None:
            continue
        if event not in AgentHookEvent.executable_in_hooks_json():
            logger.warning("event %s is not executable from hooks.json in v1", event.value)
            continue

        for raw_hook in _coerce_hooks_list(raw_hooks, str(raw_event)):
            if not isinstance(raw_hook, dict):
                raise_plugin_config_error(
                    f"hook entry for {raw_event!r} must be an object",
                    plugin_id="hook@builtin",
                )
            hook = parse_hook_definition(raw_hook)
            _validate_command_hook_allowed(hook, opts)
            fingerprint = hook_fingerprint(hook)
            if fingerprint in fingerprints:
                logger.debug("skipping duplicate hook fingerprint: %s", fingerprint)
                continue
            fingerprints.add(fingerprint)
            registry.register(event, hook)


def load_hooks_from_path(
    path: Path | str,
    registry: AgentHookRegistry,
    *,
    options: HookLoadOptions | None = None,
    seen_fingerprints: set[tuple[str, str, str | None]] | None = None,
) -> None:
    """Load hooks from a JSON file path."""
    file_path = Path(path)
    if not file_path.is_file():
        raise_plugin_config_error(
            f"hooks file not found: {file_path}",
            plugin_id="hook@builtin",
        )
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PluginConfigErrorException(
            f"invalid hooks JSON at {file_path}: {exc}",
            plugin_id="hook@builtin",
        ) from exc
    if not isinstance(data, dict):
        raise_plugin_config_error(
            f"hooks file root must be an object: {file_path}",
            plugin_id="hook@builtin",
        )
    load_hooks_from_json(data, registry, options=options, seen_fingerprints=seen_fingerprints)


def merge_hook_sources(
    sources: list[tuple[str, dict[str, Any] | Path]],
    *,
    options: HookLoadOptions | None = None,
) -> AgentHookRegistry:
    """
    Merge multiple hook sources in order (§5.1.1).

    Each source is ``(label, inline_dict | file_path)``.
    """
    registry = AgentHookRegistry()
    fingerprints: set[tuple[str, str, str | None]] = set()
    opts = options or HookLoadOptions()

    for _label, source in sources:
        if isinstance(source, Path):
            load_hooks_from_path(source, registry, options=opts, seen_fingerprints=fingerprints)
        elif isinstance(source, dict):
            load_hooks_from_json(source, registry, options=opts, seen_fingerprints=fingerprints)
        else:
            raise_plugin_config_error(
                f"invalid hook source type: {type(source)!r}",
                plugin_id="hook@builtin",
            )
    return registry


def resolve_manifest_hooks_path(hooks_value: str | dict[str, Any], manifest_dir: Path) -> Path | dict[str, Any]:
    """Resolve manifest hooks field to inline dict or absolute file path (§9.1.1-E)."""
    if isinstance(hooks_value, dict):
        return {"hooks": hooks_value}
    relative = Path(hooks_value)
    if relative.is_absolute():
        return relative
    return (manifest_dir / relative).resolve()
