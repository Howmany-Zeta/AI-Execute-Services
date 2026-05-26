# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Default plugin derivation from AgentConfiguration and agent state (§6.3.2, §6.4).

``derive_plugin_configs`` merge priority (high → low, §6.3.1):

1. ``policy_plugins`` — Phase 3 (skipped)
2. ``AgentConfiguration.plugins`` + partial derive fill
3. ``task["plugins"]`` then ``context["plugins"]`` (**context overrides task** for the same name)
4. ``derive_default_plugins()``
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from aiecs.domain.agent.plugins.models import PluginConfig

if TYPE_CHECKING:
    from aiecs.domain.agent.base_agent import BaseAIAgent
    from aiecs.domain.agent.models import AgentConfiguration

_DERIVE_FILL_NAMES = frozenset({"memory", "skill", "tool"})
_SORT_ORDER = {"tool": 0, "skill": 1, "memory": 2}


def derive_default_plugins(
    config: AgentConfiguration,
    agent: BaseAIAgent,
) -> list[PluginConfig]:
    """
    Derive builtin plugin configs from legacy ``AgentConfiguration`` fields.

    Returns memory, skill, tool, and custom_reasoning entries (§6.3.2).
    """
    return [
        _memory_plugin_config(config),
        _skill_plugin_config(config),
        _tool_plugin_config(config, agent),
        _custom_reasoning_plugin_config(),
    ]


def _memory_plugin_config(config: AgentConfiguration) -> PluginConfig:
    options: dict[str, Any] = {"capacity": config.memory_capacity}
    if config.memory_ttl_seconds is not None:
        options["ttl_seconds"] = config.memory_ttl_seconds
    return PluginConfig(
        name="memory",
        enabled=config.memory_enabled is True,
        options=options,
    )


def _skill_plugin_config(config: AgentConfiguration) -> PluginConfig:
    enabled = config.skills_enabled is True and len(config.skill_names) > 0
    options: dict[str, Any] = {
        "skill_names": list(config.skill_names),
        "auto_register_tools": config.skill_auto_register_tools,
        "inject_script_paths": config.skill_inject_script_paths,
        "context_max_skills": config.skill_context_max_skills,
    }
    return PluginConfig(name="skill", enabled=enabled, options=options)


def _tool_plugin_config(config: AgentConfiguration, agent: BaseAIAgent) -> PluginConfig:
    return PluginConfig(
        name="tool",
        enabled=_agent_has_tools(agent),
        options={
            "allowed_tools": list(config.allowed_tools),
            "tool_selection_strategy": config.tool_selection_strategy,
        },
    )


def _custom_reasoning_plugin_config() -> PluginConfig:
    return PluginConfig(name="custom_reasoning", enabled=False, options={})


def _agent_has_tools(agent: BaseAIAgent) -> bool:
    """True when the agent was constructed with a non-empty tools argument."""
    tools_input = getattr(agent, "_tools_input", None)
    if tools_input is None:
        return False
    if isinstance(tools_input, dict):
        return len(tools_input) > 0
    if isinstance(tools_input, (list, tuple)):
        return len(tools_input) > 0
    return False


def derive_plugin_configs(
    config: AgentConfiguration,
    agent: BaseAIAgent,
    task: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> tuple[list[PluginConfig], list[str]]:
    """
    Merge plugin configs from config, defaults, and per-request task/context (§6.3.1–§6.3.4).

    Priority 3 (task/context) applies after priority 2 (``config.plugins``). Within tier 3,
    ``context["plugins"]`` is applied after ``task["plugins"]`` so **context wins** on conflicts.
    Each overlay fully replaces the prior entry for the same ``name``; a higher tier
    ``enabled=False`` cannot be re-enabled by a lower tier.
    """
    merge_log: list[str] = []
    defaults = derive_default_plugins(config, agent)
    defaults_by_name = {plugin.name: plugin for plugin in defaults}

    merged = _merge_config_plugins(config, defaults_by_name, defaults, merge_log)
    merged = _apply_runtime_plugin_overlays(merged, task, context, merge_log)

    return _sort_plugin_configs(merged), merge_log


def _merge_config_plugins(
    config: AgentConfiguration,
    defaults_by_name: dict[str, PluginConfig],
    defaults: list[PluginConfig],
    merge_log: list[str],
) -> dict[str, PluginConfig]:
    """Priority 2 + 4: ``config.plugins`` with derive fill for missing builtin names."""
    if not config.plugins:
        merge_log.append("plugins=[]: using full derive_default_plugins()")
        return dict(defaults_by_name)

    merged: dict[str, PluginConfig] = {}
    for explicit in config.plugins:
        merged[explicit.name] = explicit
        merge_log.append(f"config.plugins: explicit {explicit.name!r} " f"(enabled={explicit.enabled}, priority={explicit.priority})")

    for name in _DERIVE_FILL_NAMES:
        if name not in merged:
            derived = defaults_by_name[name]
            merged[name] = derived
            merge_log.append(f"derive_default_plugins: filled missing {name!r} (enabled={derived.enabled})")
        elif merged[name].enabled is False:
            merge_log.append(f"config.plugins: explicit {name!r} disabled; derive skipped")
        else:
            merge_log.append(f"config.plugins: explicit {name!r} replaces derive_default_plugins entry")

    for plugin in defaults:
        if plugin.name not in _DERIVE_FILL_NAMES and plugin.name not in merged:
            merged[plugin.name] = plugin
            merge_log.append(f"derive_default_plugins: added {plugin.name!r} (enabled={plugin.enabled})")

    return merged


def _apply_runtime_plugin_overlays(
    merged: dict[str, PluginConfig],
    task: dict[str, Any] | None,
    context: dict[str, Any] | None,
    merge_log: list[str],
) -> dict[str, PluginConfig]:
    """Priority 3: task then context overlays (context wins over task)."""
    result = dict(merged)

    task_plugins = _coerce_plugin_configs((task or {}).get("plugins"))
    for overlay in task_plugins:
        result[overlay.name] = overlay
        merge_log.append(f"task.plugins: override {overlay.name!r} " f"(enabled={overlay.enabled}, priority={overlay.priority})")

    context_plugins = _coerce_plugin_configs((context or {}).get("plugins"))
    for overlay in context_plugins:
        result[overlay.name] = overlay
        merge_log.append(f"context.plugins: override {overlay.name!r} " f"(enabled={overlay.enabled}, priority={overlay.priority})")

    return result


def _coerce_plugin_configs(raw: Any) -> list[PluginConfig]:
    """Parse ``plugins`` entries from task/context as ``PluginConfig`` models."""
    if raw is None or not isinstance(raw, list):
        return []

    configs: list[PluginConfig] = []
    for item in raw:
        if isinstance(item, PluginConfig):
            configs.append(item)
        elif isinstance(item, dict) and item.get("name"):
            configs.append(PluginConfig.model_validate(item))
    return configs


def _sort_plugin_configs(merged: dict[str, PluginConfig]) -> list[PluginConfig]:
    """Stable sort: tool, skill, memory, then other names alphabetically."""

    def sort_key(plugin: PluginConfig) -> tuple[int, str]:
        if plugin.name in _SORT_ORDER:
            return (_SORT_ORDER[plugin.name], "")
        return (len(_SORT_ORDER), plugin.name)

    return sorted(merged.values(), key=sort_key)
