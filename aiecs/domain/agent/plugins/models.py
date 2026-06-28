# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Agent plugin data models.

Defines PluginMetadata, PluginPhase, PluginConfig, PluginLoadResult, and manifest stubs.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class PluginPhase(str, Enum):
    """Lifecycle phases for AgentPlugin hooks (§5.2)."""

    AGENT_INIT = "agent_init"
    AGENT_SHUTDOWN = "agent_shutdown"
    PRE_TASK = "pre_task"
    BUILD_MESSAGES = "build_messages"
    PRE_MAIN_LOOP = "pre_main_loop"
    ON_ITERATION_START = "on_iteration_start"
    ON_ITERATION_END = "on_iteration_end"
    ON_TOOL_BATCH_END = "on_tool_batch_end"
    POST_TASK = "post_task"


@dataclass(frozen=True)
class PluginMetadata:
    """Static descriptor for a registered plugin (§5.1)."""

    name: str
    version: str
    description: str
    priority: int = 100
    default_enabled: bool = True


class PluginConfig(BaseModel):
    """Per-plugin enablement and options (§6.1)."""

    name: str
    enabled: bool = True
    priority: int | None = None
    options: dict[str, Any] = Field(default_factory=dict)
    policy_locked: bool = Field(
        default=False,
        description=("When set in policy_plugins, lower-priority layers cannot override " "this plugin entry (§6.3.1)."),
    )
    locked_options: list[str] = Field(
        default_factory=list,
        description=("Option keys enforced by policy_plugins; lower tiers cannot override " "these keys (§6.3.1)."),
    )

    @field_validator("name")
    @classmethod
    def name_must_be_non_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("name must be non-empty")
        return value


from aiecs.domain.agent.plugins.errors import PluginError  # noqa: E402


class PluginLoadResult(BaseModel):
    """Summary of plugin initialization (§9.5, assemblePluginLoadResult)."""

    enabled: list[str] = Field(default_factory=list)
    disabled: list[str] = Field(default_factory=list)
    errors: list[PluginError] = Field(default_factory=list)


from aiecs.domain.agent.plugins.schema.manifest import PluginManifest  # noqa: E402, F401

from aiecs.domain.agent.plugins.errors import PluginHookError  # noqa: E402

PluginHookError.model_rebuild(_types_namespace={"PluginPhase": PluginPhase})
