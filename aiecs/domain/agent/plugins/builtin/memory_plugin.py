# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
MemoryPlugin — conversation memory and Hybrid context.history expansion (§7.2).

Does not import HybridAgent; history expansion mirrors ``_build_initial_messages`` (~1126–1159).
"""

from __future__ import annotations

import logging
from typing import Any, ClassVar

from aiecs.domain.agent.memory.conversation import ConversationMemory
from aiecs.domain.agent.plugins.base import BaseAgentPlugin
from aiecs.domain.agent.plugins.context import AgentPluginContext
from aiecs.domain.agent.plugins.models import PluginMetadata
from aiecs.llm import LLMMessage

logger = logging.getLogger(__name__)

PLUGIN_STATE_SESSION_KEY = "memory.session_id"
PLUGIN_STATE_TTL_KEY = "memory.ttl_seconds"
DEFAULT_SESSION_KEY = "session_id"


def expand_context_history_entries(history: list[Any]) -> list[LLMMessage]:
    """
    Expand ``context["history"]`` to ``LLMMessage`` list (HybridAgent parity, §7.2).

    Matches ``hybrid_agent._build_initial_messages`` history handling.
    """
    expanded: list[LLMMessage] = []
    for msg in history:
        if isinstance(msg, dict) and "role" in msg and ("content" in msg or "tool_calls" in msg):
            raw_images = msg.get("images")
            if isinstance(raw_images, list):
                msg_images: list[Any] = [img for img in raw_images if img is not None]
            elif raw_images is not None:
                msg_images = [raw_images]
            else:
                msg_images = []
            expanded.append(
                LLMMessage(
                    role=msg["role"],
                    content=msg.get("content"),
                    images=msg_images,
                    tool_calls=msg.get("tool_calls"),
                    tool_call_id=msg.get("tool_call_id"),
                )
            )
        elif isinstance(msg, LLMMessage):
            expanded.append(msg)
    return expanded


def _history_messages_to_context_dicts(messages: list[LLMMessage]) -> list[dict[str, Any]]:
    """Serialize LLMMessage history for ``context["history"]``."""
    return [
        {
            "role": msg.role,
            "content": msg.content,
            **({"images": msg.images} if msg.images else {}),
            **({"tool_calls": msg.tool_calls} if msg.tool_calls else {}),
            **({"tool_call_id": msg.tool_call_id} if msg.tool_call_id else {}),
        }
        for msg in messages
    ]


class MemoryPlugin(BaseAgentPlugin):
    """Builtin memory plugin: Hybrid context.history + ConversationMemory fallback."""

    metadata: ClassVar[PluginMetadata] = PluginMetadata(
        name="memory",
        version="1.0.0",
        description="Conversation memory plugin",
        priority=80,
    )

    def __init__(self, config, agent) -> None:
        super().__init__(config, agent)
        self._memory: ConversationMemory | None = None
        self._active_session_id: str | None = None

    async def on_agent_init(self, ctx: AgentPluginContext) -> None:
        capacity = int(self._config.options.get("capacity", 1000))
        ttl = self._config.options.get("ttl_seconds")
        if ttl is not None:
            ctx.plugin_state[PLUGIN_STATE_TTL_KEY] = ttl

        context_engine = getattr(self._agent, "_context_engine", None)
        persist = bool(self._config.options.get("persist", True))
        if persist and context_engine is None:
            persist = False

        self._memory = ConversationMemory(
            agent_id=self._agent.agent_id,
            max_sessions=max(capacity, 1),
            context_engine=context_engine if persist else None,
        )
        return None

    async def on_pre_task(self, ctx: AgentPluginContext) -> None:
        if _context_has_history(ctx.context):
            return None

        session_id = self._resolve_session_id(ctx)
        if not session_id or self._memory is None:
            return None

        self._active_session_id = session_id
        ctx.plugin_state[PLUGIN_STATE_SESSION_KEY] = session_id

        loaded = await self._load_session_history(session_id)
        if loaded:
            ctx.context["history"] = _history_messages_to_context_dicts(loaded)
        return None

    async def on_build_messages(
        self,
        ctx: AgentPluginContext,
        messages: list[LLMMessage],
    ) -> list[LLMMessage]:
        history = ctx.context.get("history")
        if isinstance(history, list) and len(history) > 0:
            return [*messages, *expand_context_history_entries(history)]

        memory_messages = await self._messages_from_conversation_memory(ctx)
        if memory_messages:
            return [*messages, *memory_messages]
        return messages

    async def on_post_task(self, ctx: AgentPluginContext, result: dict[str, Any]) -> dict[str, Any]:
        session_id = self._resolve_session_id(ctx)
        if not session_id or self._memory is None:
            return result

        user_content = str(ctx.task_description)
        assistant_content = str(result.get("final_response") or result.get("output") or "")
        await self.append_turn("user", user_content, session_id=session_id)
        if assistant_content:
            await self.append_turn("assistant", assistant_content, session_id=session_id)

        return result

    async def on_agent_shutdown(self, ctx: AgentPluginContext) -> None:
        self._memory = None
        self._active_session_id = None
        return None

    async def get_history(self, session_id: str | None = None) -> list[LLMMessage]:
        """Return conversation history for the active or given session."""
        if self._memory is None:
            return []
        sid = session_id or self._active_session_id
        if not sid:
            return []
        if self._memory.context_engine:
            return await self._memory.aget_conversation_history(sid)
        return self._memory.get_history(sid)

    async def append_turn(
        self,
        role: str,
        content: str,
        session_id: str | None = None,
    ) -> None:
        """Append a single message to the conversation memory session."""
        if self._memory is None:
            return
        sid = session_id or self._active_session_id
        if not sid:
            sid = self._memory.create_session()
            self._active_session_id = sid

        if self._memory.context_engine:
            await self._memory.aadd_conversation_message(sid, role, content)
        else:
            self._memory.add_message(sid, role, content)

    def _resolve_session_id(self, ctx: AgentPluginContext) -> str | None:
        session_key = str(self._config.options.get("session_key", DEFAULT_SESSION_KEY))
        session_id = ctx.context.get(session_key) or ctx.plugin_state.get(PLUGIN_STATE_SESSION_KEY)
        if session_id:
            return str(session_id)
        return self._active_session_id

    async def _load_session_history(self, session_id: str) -> list[LLMMessage]:
        if self._memory is None:
            return []
        if self._memory.context_engine:
            return await self._memory.aget_conversation_history(session_id)
        if session_id not in self._memory._sessions:
            self._memory.create_session(session_id)
        return self._memory.get_history(session_id)

    async def _messages_from_conversation_memory(
        self,
        ctx: AgentPluginContext,
    ) -> list[LLMMessage]:
        """LLMAgent-style path when ``context["history"]`` is absent."""
        if self._memory is None:
            return []

        agent_history = getattr(self._agent, "_conversation_history", None)
        if agent_history:
            return list(agent_history)

        session_id = self._resolve_session_id(ctx)
        if not session_id:
            return []

        return await self._load_session_history(session_id)


def _context_has_history(context: dict[str, Any]) -> bool:
    history = context.get("history")
    return isinstance(history, list) and len(history) > 0
