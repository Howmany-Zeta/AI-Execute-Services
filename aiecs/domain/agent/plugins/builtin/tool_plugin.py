# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
ToolPlugin — tool loading and schema preparation (§7.3).

Does not execute tools; HybridAgent._execute_tool remains responsible for execution.
"""

from __future__ import annotations

import copy
import logging
from typing import Any, ClassVar

from aiecs.domain.agent.plugins.base import BaseAgentPlugin
from aiecs.domain.agent.plugins.context import AgentPluginContext, PluginShortCircuitResult
from aiecs.domain.agent.plugins.models import PluginMetadata
from aiecs.domain.agent.tools.schema_generator import ToolSchemaGenerator

logger = logging.getLogger(__name__)

PLUGIN_STATE_SCHEMAS_KEY = "tool.schemas"
PLUGIN_STATE_ENABLE_CACHING_KEY = "tool.enable_caching"
PLUGIN_STATE_SELECTION_STRATEGY_KEY = "tool.selection_strategy"


def _schema_matches_allowed(schema_name: str, allowed: set[str]) -> bool:
    """Match function schema name to configured tool keys (supports ``tool_op`` names)."""
    if schema_name in allowed:
        return True
    return any(schema_name.startswith(f"{tool}_") for tool in allowed)


def filter_tool_schemas(
    schemas: list[dict[str, Any]],
    allowed_tools: list[str],
) -> list[dict[str, Any]]:
    """Keep schemas whose tool name is in ``allowed_tools``."""
    if not allowed_tools:
        return list(schemas)
    allowed = set(allowed_tools)
    return [schema for schema in schemas if _schema_matches_allowed(str(schema.get("name", "")), allowed)]


class ToolPlugin(BaseAgentPlugin):
    """Builtin tool plugin: load tools, generate schemas, optional allowed_tools filter."""

    metadata: ClassVar[PluginMetadata] = PluginMetadata(
        name="tool",
        version="1.0.0",
        description="Tool schema and filtering plugin",
        priority=100,
    )

    async def on_agent_init(self, ctx: AgentPluginContext) -> None:
        agent = self._agent
        tool_instances = agent._initialize_tools_from_config()
        agent._tool_instances = tool_instances

        schemas: list[dict[str, Any]] = []
        if tool_instances:
            schemas = ToolSchemaGenerator.generate_schemas_for_tool_instances(tool_instances)
            setattr(agent, "_tool_schemas", schemas)

        _validate_function_calling_support(agent)

        ctx.plugin_state[PLUGIN_STATE_SCHEMAS_KEY] = copy.deepcopy(schemas)
        ctx.plugin_state[PLUGIN_STATE_ENABLE_CACHING_KEY] = self._resolve_enable_caching()
        ctx.plugin_state[PLUGIN_STATE_SELECTION_STRATEGY_KEY] = self._resolve_tool_selection_strategy()

        logger.debug(
            "ToolPlugin initialized %s tool schema(s) for agent %s",
            len(schemas),
            agent.agent_id,
        )

    async def on_pre_main_loop(
        self,
        ctx: AgentPluginContext,
    ) -> None | PluginShortCircuitResult:
        allowed_tools = self._config.options.get("allowed_tools")
        if allowed_tools is None:
            return None
        if not list(allowed_tools):
            return None

        schemas = getattr(self._agent, "_tool_schemas", [])
        filtered = filter_tool_schemas(schemas, list(allowed_tools))
        setattr(self._agent, "_tool_schemas", filtered)
        ctx.plugin_state[PLUGIN_STATE_SCHEMAS_KEY] = copy.deepcopy(filtered)
        return None

    def _resolve_enable_caching(self) -> bool:
        if "enable_caching" in self._config.options:
            return bool(self._config.options["enable_caching"])
        return True

    def _resolve_tool_selection_strategy(self) -> str:
        if "tool_selection_strategy" in self._config.options:
            return str(self._config.options["tool_selection_strategy"])
        return str(getattr(self._agent._config, "tool_selection_strategy", "llm_based"))


def _validate_function_calling_support(agent: Any) -> None:
    """Align with HybridAgent: require FC when tools are configured."""
    tool_instances = getattr(agent, "_tool_instances", None) or {}
    if not tool_instances:
        return

    check = getattr(agent, "_check_function_calling_support", None)
    if check is None:
        return

    supported = check()
    if hasattr(agent, "_use_function_calling"):
        agent._use_function_calling = supported

    if not supported:
        llm_client = getattr(agent, "llm_client", None)
        provider = getattr(llm_client, "provider_name", "unknown")
        raise ValueError(
            "HybridAgent requires an LLM client with Function Calling support when tools are configured. "
            f"Current client ({provider}) does not support tools. "
            "Use OpenAI-compatible clients: OpenAI, xAI, Anthropic, or Google Vertex."
        )
