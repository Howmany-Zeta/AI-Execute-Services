# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""W7: deterministic legacy summarization without LLM (A14)."""

from __future__ import annotations

from aiecs.llm import LLMMessage

from aiecs.domain.context.compression.pairs import (
    sanitize_messages_for_compaction,
    split_messages_preserving_tool_pairs,
)

CONVERSATION_SUMMARY_PREFIX = "[conversation summary]"


def summarize_messages(
    messages: list[LLMMessage],
    *,
    max_messages: int = 8,
) -> str:
    """Produce a compact textual summary of recent messages (legacy)."""
    selected = messages[-max_messages:]
    lines: list[str] = []
    for message in selected:
        text = (message.content or "").strip()
        if not text:
            if message.tool_calls:
                names = [str((tc.get("function") or {}).get("name") or tc.get("name") or "") for tc in message.tool_calls]
                lines.append(f"{message.role}: tool calls -> {', '.join(n for n in names if n)}")
            continue
        lines.append(f"{message.role}: {text[:300]}")
    return "\n".join(lines)


def compact_messages(
    messages: list[LLMMessage],
    *,
    preserve_recent: int = 6,
) -> list[LLMMessage]:
    """Replace older conversation history with a synthetic summary (legacy)."""
    if len(messages) <= preserve_recent:
        return sanitize_messages_for_compaction(list(messages))

    older, newer = split_messages_preserving_tool_pairs(
        messages,
        preserve_recent=preserve_recent,
    )
    summary = summarize_messages(older)
    if not summary:
        return list(newer)

    return sanitize_messages_for_compaction(
        [
            LLMMessage(
                role="user",
                content=f"{CONVERSATION_SUMMARY_PREFIX}\n{summary}",
            ),
            *newer,
        ]
    )
