# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Default plugin derivation from AgentConfiguration and agent state (§6.3.2, §6.4).

``derive_plugin_configs`` merge priority (high → low, §6.3.1):

1. ``policy_plugins`` — enterprise policy; ``enabled=false`` / ``policy_locked`` block lower tiers
2. ``AgentConfiguration.plugins`` + partial derive fill
3. ``task["plugins"]`` then ``context["plugins"]`` (**context overrides task** for the same name)
4. ``derive_default_plugins()``

Policy is applied last so it wins on conflicts. Task/context overlays that violate an active
policy lock are rejected and recorded in ``merge_log``.
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

    Returns memory, skill, tool, knowledge, collaboration, and custom_reasoning entries (§6.3.2).
    """
    return [
        _memory_plugin_config(config),
        _skill_plugin_config(config),
        _tool_plugin_config(config, agent),
        _knowledge_plugin_config(config, agent),
        _collaboration_plugin_config(agent),
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


def _knowledge_plugin_config(config: AgentConfiguration, agent: BaseAIAgent) -> PluginConfig:
    graph_store = getattr(agent, "graph_store", None)
    enable_graph_reasoning = getattr(agent, "enable_graph_reasoning", True)
    options: dict[str, Any] = {
        "retrieval_strategy": config.retrieval_strategy,
        "enable_knowledge_caching": config.enable_knowledge_caching,
        "max_context_size": config.max_context_size,
        "cache_ttl": config.cache_ttl,
        "entity_extraction_provider": config.entity_extraction_provider,
        "enable_graph_reasoning": bool(enable_graph_reasoning),
    }
    graph_store_ref = _graph_store_ref(graph_store)
    if graph_store_ref is not None:
        options["graph_store_ref"] = graph_store_ref

    return PluginConfig(
        name="knowledge",
        enabled=_knowledge_plugin_enabled(graph_store, enable_graph_reasoning),
        options=options,
    )


def _knowledge_plugin_enabled(graph_store: Any, enable_graph_reasoning: Any) -> bool:
    """True when the agent has an active graph store (KnowledgeAwareAgent parity)."""
    return graph_store is not None and bool(enable_graph_reasoning)


def _graph_store_ref(graph_store: Any) -> str | None:
    """Serializable graph store reference for plugin options (§6.4, E-05)."""
    if graph_store is None:
        return None
    store_id = getattr(graph_store, "store_id", None) or getattr(graph_store, "id", None)
    if isinstance(store_id, str) and store_id:
        return store_id
    return type(graph_store).__name__


def _collaboration_plugin_config(agent: BaseAIAgent) -> PluginConfig:
    collaboration_enabled = getattr(agent, "_collaboration_enabled", False)
    options: dict[str, Any] = {
        "inject_system_hint": True,
    }
    return PluginConfig(
        name="collaboration",
        enabled=bool(collaboration_enabled),
        options=options,
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
    Merge plugin configs from policy, config, task/context, and defaults (§6.3.1–§6.3.4).

    Priority 1 (``policy_plugins``) is applied last so it wins on same-name conflicts.
    Within tier 3, ``context["plugins"]`` is applied after ``task["plugins"]`` so context wins.
    Each overlay fully replaces the prior entry for the same ``name`` unless policy rejects it.
    """
    merge_log: list[str] = []
    policy_by_name = _policy_plugins_by_name(config)

    defaults = derive_default_plugins(config, agent)
    defaults_by_name = {plugin.name: plugin for plugin in defaults}

    merged = _merge_config_plugins(config, defaults_by_name, defaults, merge_log)
    merged = _apply_runtime_plugin_overlays(merged, task, context, merge_log, policy_by_name=policy_by_name)
    merged = _apply_policy_plugins(merged, config.policy_plugins, merge_log)

    return _sort_plugin_configs(merged), merge_log


def _policy_plugins_by_name(config: AgentConfiguration) -> dict[str, PluginConfig]:
    return {plugin.name: plugin for plugin in config.policy_plugins}


def _policy_blocks_overlay(
    policy: PluginConfig | None,
    overlay: PluginConfig,
) -> bool:
    """True when task/context must not apply ``overlay`` due to policy lock (§6.3.1)."""
    if policy is None:
        return False
    if policy.policy_locked:
        return True
    if policy.enabled is False and overlay.enabled is not False:
        return True
    return False


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
    *,
    policy_by_name: dict[str, PluginConfig],
) -> dict[str, PluginConfig]:
    """Priority 3: task then context overlays (context wins over task)."""
    result = dict(merged)

    task_plugins = _coerce_plugin_configs((task or {}).get("plugins"))
    for overlay in task_plugins:
        policy = policy_by_name.get(overlay.name)
        if _policy_blocks_overlay(policy, overlay):
            reason = "locked" if policy and policy.policy_locked else "disabled"
            merge_log.append(f"task.plugins: rejected override {overlay.name!r} " f"(policy.plugins: {reason})")
            continue
        result[overlay.name] = overlay
        merge_log.append(f"task.plugins: override {overlay.name!r} " f"(enabled={overlay.enabled}, priority={overlay.priority})")

    context_plugins = _coerce_plugin_configs((context or {}).get("plugins"))
    for overlay in context_plugins:
        policy = policy_by_name.get(overlay.name)
        if _policy_blocks_overlay(policy, overlay):
            reason = "locked" if policy and policy.policy_locked else "disabled"
            merge_log.append(f"context.plugins: rejected override {overlay.name!r} " f"(policy.plugins: {reason})")
            continue
        result[overlay.name] = overlay
        merge_log.append(f"context.plugins: override {overlay.name!r} " f"(enabled={overlay.enabled}, priority={overlay.priority})")

    return result


def _apply_policy_plugins(
    merged: dict[str, PluginConfig],
    policy_plugins: list[PluginConfig],
    merge_log: list[str],
) -> dict[str, PluginConfig]:
    """Priority 1: policy_plugins applied last; wins on conflicts (§6.3.1)."""
    if not policy_plugins:
        return merged

    result = dict(merged)
    for policy in policy_plugins:
        existing = result.get(policy.name)
        if existing and policy.locked_options:
            merged_options = dict(existing.options)
            for key in policy.locked_options:
                if key in policy.options:
                    merged_options[key] = policy.options[key]
            result[policy.name] = policy.model_copy(update={"options": merged_options})
            merge_log.append(f"policy.plugins: locked options {policy.locked_options!r} " f"for {policy.name!r} (enabled={policy.enabled})")
        elif existing and not policy.policy_locked and not policy.locked_options:
            result[policy.name] = policy
            merge_log.append(f"policy.plugins: override {policy.name!r} " f"(enabled={policy.enabled}, priority={policy.priority})")
        else:
            result[policy.name] = policy
            merge_log.append(f"policy.plugins: override {policy.name!r} " f"(enabled={policy.enabled}, policy_locked={policy.policy_locked})")
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
