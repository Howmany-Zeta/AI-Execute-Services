# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
AgentPlugin protocol (§5.3).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from aiecs.domain.agent.plugins.models import PluginMetadata

if TYPE_CHECKING:
    from aiecs.domain.agent.plugins.context import AgentPluginContext, PluginShortCircuitResult
    from aiecs.llm.clients.base_client import LLMMessage


class AgentPlugin(Protocol):
    """Lifecycle hooks for agent plugins."""

    metadata: PluginMetadata

    async def on_agent_init(self, ctx: AgentPluginContext) -> None:
        """Called during agent initialization (AGENT_INIT)."""
        ...

    async def on_agent_shutdown(self, ctx: AgentPluginContext) -> None:
        """Called during agent shutdown (AGENT_SHUTDOWN)."""
        ...

    async def on_pre_task(self, ctx: AgentPluginContext) -> None:
        """Called before task execution (PRE_TASK)."""
        ...

    async def on_build_messages(
        self,
        ctx: AgentPluginContext,
        messages: list[LLMMessage],
    ) -> list[LLMMessage]:
        """Build or augment initial LLM messages (BUILD_MESSAGES)."""
        ...

    async def on_pre_main_loop(
        self,
        ctx: AgentPluginContext,
    ) -> None | PluginShortCircuitResult:
        """Called before the main tool loop (PRE_MAIN_LOOP)."""
        ...

    async def on_post_task(self, ctx: AgentPluginContext, result: dict[str, Any]) -> dict[str, Any]:
        """Post-process task result (POST_TASK)."""
        ...

    async def on_iteration_start(self, ctx: AgentPluginContext, iteration: int) -> None:
        """Called at the start of a tool-loop iteration."""
        ...

    async def on_iteration_end(
        self,
        ctx: AgentPluginContext,
        iteration: int,
        step: dict[str, Any],
    ) -> None:
        """Called at the end of a tool-loop iteration."""
        ...
