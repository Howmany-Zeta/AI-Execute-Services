# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
SkillPlugin — skill attachment and context injection (§7.1).

Delegates to SkillCapableMixin on the agent; does not import HybridAgent.

This plugin is the **only** supported attach/inject path for HybridAgent: do not call
``attach_skills`` or ``get_skill_context`` from ``HybridAgent`` lifecycle methods.
"""

from __future__ import annotations

import logging
from typing import ClassVar

from aiecs.domain.agent.plugins.base import BaseAgentPlugin
from aiecs.domain.agent.plugins.context import AgentPluginContext
from aiecs.domain.agent.plugins.errors import PluginErrorException, PluginInitError
from aiecs.domain.agent.plugins.identifier import format_plugin_id
from aiecs.domain.agent.plugins.models import PluginMetadata
from aiecs.llm import LLMMessage

logger = logging.getLogger(__name__)

SKILL_SYSTEM_MESSAGE_PREFIX = "Relevant Skills for this Task:\n"
PLUGIN_STATE_CONTEXT_MAX_SKILLS_KEY = "skill.context_max_skills"
PLUGIN_ID = format_plugin_id("skill", "builtin")


class SkillPlugin(BaseAgentPlugin):
    """Builtin skill plugin: attach skills, inject context, detach on shutdown."""

    metadata: ClassVar[PluginMetadata] = PluginMetadata(
        name="skill",
        version="1.0.0",
        description="Skill context and attachment plugin",
        priority=90,
    )

    async def on_agent_init(self, ctx: AgentPluginContext) -> None:
        skill_names = list(self._config.options.get("skill_names") or [])
        if not skill_names:
            return None

        auto_register = bool(self._config.options.get("auto_register_tools", False))
        inject_paths = bool(self._config.options.get("inject_script_paths", True))
        if "context_max_skills" in self._config.options:
            ctx.plugin_state[PLUGIN_STATE_CONTEXT_MAX_SKILLS_KEY] = self._config.options["context_max_skills"]

        agent = self._agent
        try:
            attached = agent.attach_skills(
                skill_names,
                auto_register_tools=auto_register,
                inject_script_paths=inject_paths,
            )
        except ValueError as exc:
            raise PluginErrorException(
                PluginInitError(
                    message=str(exc),
                    plugin_id=PLUGIN_ID,
                    details={"skill_names": skill_names},
                )
            ) from exc

        if not attached:
            raise PluginErrorException(
                PluginInitError(
                    message=f"No skills attached for names: {skill_names!r}",
                    plugin_id=PLUGIN_ID,
                    details={"skill_names": skill_names},
                )
            )

        logger.debug(
            "SkillPlugin attached %s skill(s) for agent %s",
            len(attached),
            agent.agent_id,
        )
        return None

    async def on_build_messages(
        self,
        ctx: AgentPluginContext,
        messages: list[LLMMessage],
    ) -> list[LLMMessage]:
        attached = getattr(self._agent, "_attached_skills", None) or []
        if not attached:
            return messages

        task_description = str(ctx.task_description)
        skill_context = self._agent.get_skill_context(
            request=task_description,
            include_all_skills=False,
        )
        if not skill_context:
            return messages

        return [
            *messages,
            LLMMessage(
                role="system",
                content=f"{SKILL_SYSTEM_MESSAGE_PREFIX}{skill_context}",
            ),
        ]

    async def on_agent_shutdown(self, ctx: AgentPluginContext) -> None:
        if getattr(self._agent, "_attached_skills", None):
            self._agent.detach_all_skills()
        return None
