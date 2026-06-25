# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""W3: deterministic context collapse for oversized text blocks (A10)."""

from __future__ import annotations

from aiecs.llm import LLMMessage

from aiecs.domain.context.compression.constants import (
    CONTEXT_COLLAPSE_HEAD_CHARS,
    CONTEXT_COLLAPSE_TAIL_CHARS,
    CONTEXT_COLLAPSE_TEXT_CHAR_LIMIT,
)
from aiecs.domain.context.compression.pairs import split_messages_preserving_tool_pairs
from aiecs.domain.context.compression.tokens import estimate_message_tokens


def _collapse_text(text: str) -> str:
    if len(text) <= CONTEXT_COLLAPSE_TEXT_CHAR_LIMIT:
        return text
    omitted = len(text) - CONTEXT_COLLAPSE_HEAD_CHARS - CONTEXT_COLLAPSE_TAIL_CHARS
    head = text[:CONTEXT_COLLAPSE_HEAD_CHARS].rstrip()
    tail = text[-CONTEXT_COLLAPSE_TAIL_CHARS:].lstrip()
    return f"{head}\n...[collapsed {omitted} chars]...\n{tail}"


def try_context_collapse(
    messages: list[LLMMessage],
    *,
    preserve_recent: int,
) -> list[LLMMessage] | None:
    """Deterministically shrink oversized text blocks before full compact."""
    if len(messages) <= preserve_recent + 2:
        return None

    older, newer = split_messages_preserving_tool_pairs(
        messages,
        preserve_recent=preserve_recent,
    )
    changed = False
    collapsed_older: list[LLMMessage] = []

    for message in older:
        if message.role == "tool":
            collapsed = _collapse_text(message.content or "")
            if collapsed != (message.content or ""):
                changed = True
            collapsed_older.append(
                LLMMessage(
                    role="tool",
                    content=collapsed,
                    tool_call_id=message.tool_call_id,
                )
            )
            continue

        if message.content:
            collapsed = _collapse_text(message.content)
            if collapsed != message.content:
                changed = True
            collapsed_older.append(
                LLMMessage(
                    role=message.role,
                    content=collapsed,
                    images=list(message.images),
                    tool_calls=message.tool_calls,
                    tool_call_id=message.tool_call_id,
                    cache_control=message.cache_control,
                )
            )
            continue

        collapsed_older.append(message)

    if not changed:
        return None

    result = [*collapsed_older, *newer]
    if estimate_message_tokens(result) >= estimate_message_tokens(messages):
        return None
    return result
