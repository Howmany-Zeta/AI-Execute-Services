# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Agent plugin execution context and short-circuit results (§5.4, §4.4).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, cast

if TYPE_CHECKING:
    from aiecs.domain.agent.base_agent import BaseAIAgent
    from aiecs.domain.agent.plugins.protocols import AgentPlugin
    from aiecs.llm.clients.base_client import LLMMessage


@dataclass
class PluginShortCircuitResult:
    """Plugin requests terminating subsequent phases (including MAIN_LOOP)."""

    result: dict[str, Any]
    source_plugin_id: str
    reason: str | None = None


@dataclass
class AgentPluginContext:
    """
    Per-task plugin execution context.

    ``plugin_state`` is created fresh for each ``execute_task`` / streaming call.
    """

    agent: BaseAIAgent
    task: dict[str, Any]
    context: dict[str, Any]
    task_description: str
    plugin_state: dict[str, Any] = field(default_factory=dict)
    messages: list[LLMMessage] = field(default_factory=list)
    event_sink: Callable[..., Any] | None = None

    def get_plugin(self, name: str) -> AgentPlugin | None:
        """Delegate to ``agent._plugin_manager.get_plugin(name)``."""
        manager = getattr(self.agent, "_plugin_manager", None)
        if manager is None:
            return None
        return cast("AgentPlugin | None", manager.get_plugin(name))
