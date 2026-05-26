# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Agent Plugin System

Unified lifecycle hooks and registry for Skill, Memory, Tool, and extension plugins.
Phase 1 scaffolding; full implementation follows PLUGIN_SYSTEM_PHASE1_TASKS.md.
"""

from typing import Any

from aiecs.domain.agent.plugins.models import (
    PluginConfig,
    PluginLoadResult,
    PluginMetadata,
    PluginPhase,
)
from aiecs.domain.agent.plugins.errors import (
    PluginConfigError,
    PluginDependencyError,
    PluginError,
    PluginErrorException,
    PluginHookError,
    PluginInitError,
    PluginReloadError,
    PluginReloadErrorException,
    get_plugin_error_message,
)
from aiecs.domain.agent.plugins.base import BaseAgentPlugin
from aiecs.domain.agent.plugins.context import (
    AgentPluginContext,
    PluginShortCircuitResult,
)
from aiecs.domain.agent.plugins.defaults import derive_default_plugins, derive_plugin_configs
from aiecs.domain.agent.plugins.identifier import (
    PluginIdentifier,
    format_plugin_id,
    parse_plugin_identifier,
)
from aiecs.domain.agent.plugins.manager import PluginManager
from aiecs.domain.agent.plugins.registry import PluginRegistry

__all__ = [
    "AgentPluginContext",
    "BaseAgentPlugin",
    "PluginConfig",
    "PluginConfigError",
    "PluginDependencyError",
    "PluginError",
    "PluginErrorException",
    "PluginHookError",
    "PluginIdentifier",
    "PluginInitError",
    "PluginReloadError",
    "PluginReloadErrorException",
    "PluginLoadResult",
    "PluginMetadata",
    "PluginPhase",
    "PluginShortCircuitResult",
    "PluginManager",
    "PluginRegistry",
    "derive_default_plugins",
    "derive_plugin_configs",
    "format_plugin_id",
    "get_plugin_error_message",
    "parse_plugin_identifier",
]
