# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""W4: prompt-too-long retry head truncation (A11) and shared PTL detection."""

from __future__ import annotations

from aiecs.llm import LLMMessage

from aiecs.domain.context.compression.constants import PTL_RETRY_MARKER
from aiecs.domain.context.compression.pairs import (
    sanitize_messages_for_compaction,
    split_preserving_tool_pairs,
)

PROMPT_TOO_LONG_NEEDLES: tuple[str, ...] = (
    "prompt too long",
    "context_length_exceeded",
    "context length",
    "maximum context",
    "context window",
    "input tokens exceed",
    "messages resulted in",
    "reduce the length of the messages",
    "configured limit",
    "too many tokens",
    "too large for the model",
    "maximum context length",
    "exceed_context",
    "exceeds the available context size",
    "available context size",
)


def is_prompt_too_long_error(exc: Exception) -> bool:
    """Shared detector for provider context overflow errors (O5 / W5 PTL retry)."""
    text = str(exc).lower()
    return any(needle in text for needle in PROMPT_TOO_LONG_NEEDLES)


def _group_messages_by_prompt_round(
    messages: list[LLMMessage],
) -> list[list[LLMMessage]]:
    groups: list[list[LLMMessage]] = []
    current: list[LLMMessage] = []
    for message in messages:
        starts_new_round = message.role == "user" and bool((message.content or "").strip())
        if starts_new_round and current:
            groups.append(current)
            current = []
        current.append(message)
    if current:
        groups.append(current)
    return groups


def truncate_head_for_ptl_retry(
    messages: list[LLMMessage],
) -> list[LLMMessage] | None:
    """Drop the oldest prompt rounds when the compact request itself is too large."""
    groups = _group_messages_by_prompt_round(messages)
    if len(groups) < 2:
        return None

    drop_count = max(1, len(groups) // 5)
    drop_count = min(drop_count, len(groups) - 1)
    flat_drop_end = sum(len(group) for group in groups[:drop_count])
    safe_split = split_preserving_tool_pairs(messages, flat_drop_end)
    if safe_split <= 0:
        return None

    retained = sanitize_messages_for_compaction(messages[safe_split:])
    if not retained:
        return None
    if retained[0].role == "assistant":
        return [
            LLMMessage(role="user", content=PTL_RETRY_MARKER),
            *retained,
        ]
    return retained
