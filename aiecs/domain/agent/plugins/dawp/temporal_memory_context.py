# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Read-only temporal memory facts injection for DAWP runs (D3-04, §11).

Reads ``plugin_state["temporal_memory.facts"]`` when present (set by
``TemporalMemoryPlugin.on_pre_task``).  Does **not** merge into KnowledgePlugin
or invoke temporal memory search from nested DAWP loops.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aiecs.domain.temporal_memory.constants import PLUGIN_STATE_FACTS_KEY
from aiecs.llm import LLMMessage

if TYPE_CHECKING:
    from aiecs.domain.agent.plugins.context import AgentPluginContext


def inject_temporal_memory_facts_into_messages(
    messages: list[LLMMessage],
    plugin_ctx: AgentPluginContext,
    *,
    max_items: int = 10,
) -> list[LLMMessage]:
    """Append formatted L1 facts to *messages* when available (read-only, D3-04)."""
    facts = plugin_ctx.plugin_state.get(PLUGIN_STATE_FACTS_KEY)
    if not isinstance(facts, list) or not facts:
        return messages

    from aiecs.domain.agent.plugins.builtin.temporal_memory_plugin import format_facts_for_prompt

    block = format_facts_for_prompt(facts, max_items=max_items)
    if not block:
        return messages

    updated = list(messages)
    updated.append(LLMMessage(role="user", content=f"\n\n{block}"))
    return updated
