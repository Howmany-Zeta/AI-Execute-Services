# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Base agent plugin with default no-op lifecycle hooks (§5.3).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from aiecs.domain.agent.plugins.context import AgentPluginContext, PluginShortCircuitResult
from aiecs.domain.agent.plugins.models import PluginConfig, PluginMetadata

if TYPE_CHECKING:
    from aiecs.domain.agent.base_agent import BaseAIAgent
    from aiecs.llm.clients.base_client import LLMMessage


class BaseAgentPlugin:
    """Default empty hook implementations; subclasses override as needed."""

    metadata: ClassVar[PluginMetadata] = PluginMetadata(
        name="base",
        version="0.0.0",
        description="Base agent plugin",
    )

    def __init__(self, config: PluginConfig, agent: BaseAIAgent) -> None:
        self._config = config
        self._agent = agent

    async def on_agent_init(self, ctx: AgentPluginContext) -> None:
        return None

    async def on_agent_shutdown(self, ctx: AgentPluginContext) -> None:
        return None

    async def on_pre_task(self, ctx: AgentPluginContext) -> None:
        return None

    async def on_build_messages(
        self,
        ctx: AgentPluginContext,
        messages: list[LLMMessage],
    ) -> list[LLMMessage]:
        return messages

    async def on_pre_main_loop(
        self,
        ctx: AgentPluginContext,
    ) -> None | PluginShortCircuitResult:
        return None

    async def on_post_task(self, ctx: AgentPluginContext, result: dict[str, Any]) -> dict[str, Any]:
        return result

    async def on_iteration_start(self, ctx: AgentPluginContext, iteration: int) -> None:
        return None

    async def on_iteration_end(
        self,
        ctx: AgentPluginContext,
        iteration: int,
        step: dict[str, Any],
    ) -> None:
        return None

    async def on_tool_batch_end(
        self,
        ctx: AgentPluginContext,
        iteration: int,
        messages: list[LLMMessage],
    ) -> None:
        return None
