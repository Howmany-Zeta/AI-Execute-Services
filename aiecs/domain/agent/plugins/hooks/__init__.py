# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Agent hook plugin public exports."""

from aiecs.domain.agent.plugins.hooks.dispatch import dispatch_agent_hook, has_registered_hooks
from aiecs.domain.agent.plugins.hooks.events import AgentHookEvent
from aiecs.domain.agent.plugins.hooks.executor import AgentHookExecutor, AgentHookExecutionContext
from aiecs.domain.agent.plugins.hooks.loader import (
    HookLoadOptions,
    load_hooks_from_json,
    load_hooks_from_path,
    merge_hook_sources,
)
from aiecs.domain.agent.plugins.hooks.permission import (
    PermissionDecision,
    PermissionOutcome,
    is_mcp_tool,
    parse_permission_decision,
    resolve_permission_decision,
)
from aiecs.domain.agent.plugins.hooks.registry import AgentHookRegistry
from aiecs.domain.agent.plugins.hooks.schemas import (
    AgentHookDefinition,
    CommandHookDefinition,
    HookDefinition,
    HttpHookDefinition,
    PromptHookDefinition,
)
from aiecs.domain.agent.plugins.hooks.tool_dispatch import (
    ToolConfirmationNeed,
    ToolHookDispatchResult,
    dispatch_tool_with_hooks,
    resolve_tool_confirmation,
)
from aiecs.domain.agent.plugins.hooks.types import AggregatedHookResult, HookDispatchContext, HookResult

__all__ = [
    "AgentHookDefinition",
    "AgentHookEvent",
    "AgentHookExecutionContext",
    "AgentHookExecutor",
    "AgentHookRegistry",
    "AggregatedHookResult",
    "CommandHookDefinition",
    "HookDefinition",
    "HookDispatchContext",
    "HookLoadOptions",
    "HookResult",
    "HttpHookDefinition",
    "PromptHookDefinition",
    "ToolConfirmationNeed",
    "ToolHookDispatchResult",
    "dispatch_agent_hook",
    "dispatch_host_notification",
    "dispatch_tool_with_hooks",
    "has_registered_hooks",
    "is_mcp_tool",
    "load_hooks_from_json",
    "load_hooks_from_path",
    "merge_hook_sources",
    "parse_permission_decision",
    "PermissionDecision",
    "PermissionOutcome",
    "resolve_permission_decision",
    "resolve_tool_confirmation",
]
