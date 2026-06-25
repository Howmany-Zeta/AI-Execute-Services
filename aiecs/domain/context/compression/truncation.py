# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""W12: truncation modes A3 earlier-placeholder and A12 truncate_middle."""

from __future__ import annotations

from typing import Sequence

from aiecs.llm import LLMMessage

from aiecs.domain.context.compression.pairs import (
    sanitize_messages_for_compaction,
    split_preserving_tool_pairs,
)
from aiecs.domain.context.compression.tokens import estimate_message_tokens
from aiecs.domain.context.compression.types import TruncationMode

MIDDLE_PLACEHOLDER = "[... conversation history compressed ...]"


def earlier_placeholder_text(dropped_count: int) -> str:
    return f"[{dropped_count} earlier messages omitted for context limit]"


def compress_with_earlier_placeholder(
    messages: Sequence[LLMMessage],
    *,
    max_tokens: int,
    preserve_system: bool = True,
) -> list[LLMMessage]:
    """Drop oldest messages with a placeholder; always respects tool pairs (W1)."""
    message_list = list(messages)
    if estimate_message_tokens(message_list) <= max_tokens:
        return message_list

    system_msgs = [msg for msg in message_list if msg.role == "system"] if preserve_system else []
    working = [msg for msg in message_list if msg not in system_msgs]

    preserved: list[LLMMessage] = []
    budget = max_tokens - estimate_message_tokens(system_msgs)
    for message in reversed(working):
        message_tokens = estimate_message_tokens([message])
        if message_tokens <= budget:
            preserved.insert(0, message)
            budget -= message_tokens
        else:
            break

    if len(preserved) == len(working):
        return message_list

    split_index = split_preserving_tool_pairs(working, len(working) - len(preserved))
    dropped_count = split_index
    if dropped_count <= 0:
        return system_msgs + preserved

    placeholder = LLMMessage(
        role="system",
        content=earlier_placeholder_text(dropped_count),
    )
    return system_msgs + [placeholder] + working[split_index:]


def truncate_middle(
    messages: Sequence[LLMMessage],
    *,
    keep_start: int = 2,
    keep_end: int = 2,
    placeholder_role: str = "system",
    placeholder_text: str = MIDDLE_PLACEHOLDER,
) -> list[LLMMessage]:
    """Keep head/tail segments and replace the middle with a placeholder (A12)."""
    message_list = list(messages)
    if len(message_list) <= keep_start + keep_end:
        return message_list

    safe_start = split_preserving_tool_pairs(message_list, keep_start)
    safe_tail_start = split_preserving_tool_pairs(
        message_list,
        len(message_list) - keep_end,
    )
    safe_tail_start = _expand_tail_for_tool_pairs(
        message_list,
        safe_tail_start,
    )

    if safe_tail_start <= safe_start:
        return sanitize_messages_for_compaction(message_list)

    start_msgs = message_list[:safe_start]
    end_msgs = message_list[safe_tail_start:]
    combined = start_msgs + [
        LLMMessage(role=placeholder_role, content=placeholder_text),
        *end_msgs,
    ]
    return sanitize_messages_for_compaction(combined)


def _expand_tail_for_tool_pairs(
    messages: list[LLMMessage],
    tail_start: int,
) -> int:
    """Pull assistant/tool_use partners into the tail when tool results are kept."""
    safe_tail_start = tail_start
    changed = True
    while changed:
        changed = False
        for index in range(safe_tail_start, len(messages)):
            message = messages[index]
            if message.role != "tool" or not message.tool_call_id:
                continue
            tool_call_id = message.tool_call_id
            for assistant_index in range(index - 1, -1, -1):
                assistant = messages[assistant_index]
                if assistant.role != "assistant" or not assistant.tool_calls:
                    continue
                if not any(str(tool_call.get("id")) == tool_call_id for tool_call in assistant.tool_calls):
                    continue
                if assistant_index < safe_tail_start:
                    next_start = split_preserving_tool_pairs(messages, assistant_index)
                    if next_start < safe_tail_start:
                        safe_tail_start = next_start
                        changed = True
                break
    return safe_tail_start


def compress_to_token_limit(
    messages: Sequence[LLMMessage],
    *,
    max_tokens: int,
    mode: TruncationMode = TruncationMode.EARLIER_PLACEHOLDER,
    preserve_system: bool = True,
) -> list[LLMMessage]:
    """Route truncation by mode."""
    if mode == TruncationMode.TRUNCATE_MIDDLE:
        compressed = truncate_middle(messages)
        if estimate_message_tokens(compressed) <= max_tokens:
            return compressed
    return compress_with_earlier_placeholder(
        messages,
        max_tokens=max_tokens,
        preserve_system=preserve_system,
    )


def compress_preserve_recent(
    messages: Sequence[LLMMessage],
    *,
    max_tokens: int,
    priority_indices: set[int] | None = None,
    preserve_system: bool = True,
) -> list[LLMMessage]:
    """Preserve recent and optional priority messages within token budget."""
    message_list = list(messages)
    if estimate_message_tokens(message_list) <= max_tokens:
        return message_list

    priority_indices = priority_indices or set()
    system_indices = {index for index, message in enumerate(message_list) if message.role == "system"} if preserve_system else set()
    system_msgs = [message_list[index] for index in sorted(system_indices)]
    keep_indices: set[int] = set()
    budget = max_tokens - estimate_message_tokens(system_msgs)

    for index in sorted(priority_indices):
        if index >= len(message_list):
            continue
        block_indices = _expand_tool_pair_indices(message_list, index)
        block = [message_list[i] for i in sorted(block_indices)]
        block_tokens = estimate_message_tokens(block)
        if block_tokens <= budget:
            keep_indices |= block_indices
            budget -= block_tokens

    best_indices = set(keep_indices)
    for tail_count in range(len(message_list), 0, -1):
        split_at = split_preserving_tool_pairs(
            message_list,
            len(message_list) - tail_count,
        )
        candidate_indices = (keep_indices | set(range(split_at, len(message_list)))) - system_indices
        candidate = [message_list[i] for i in sorted(candidate_indices)]
        if estimate_message_tokens(system_msgs + candidate) <= max_tokens:
            best_indices = candidate_indices | system_indices
            break

    if not best_indices:
        return compress_with_earlier_placeholder(
            message_list,
            max_tokens=max_tokens,
            preserve_system=preserve_system,
        )

    compressed = list(system_msgs)
    for index, message in enumerate(message_list):
        if index in system_indices:
            continue
        if index in best_indices:
            compressed.append(message)

    if estimate_message_tokens(compressed) <= max_tokens:
        return compressed
    return compress_with_earlier_placeholder(
        message_list,
        max_tokens=max_tokens,
        preserve_system=preserve_system,
    )


def _expand_tool_pair_indices(messages: list[LLMMessage], index: int) -> set[int]:
    """Include paired assistant/tool_use messages for a priority index."""
    indices = {index}
    message = messages[index]
    if message.role == "tool" and message.tool_call_id:
        tool_call_id = message.tool_call_id
        for candidate_index, candidate in enumerate(messages):
            if candidate.role != "assistant" or not candidate.tool_calls:
                continue
            if any(str(tool_call.get("id")) == tool_call_id for tool_call in candidate.tool_calls):
                indices.add(candidate_index)
    if message.role == "assistant" and message.tool_calls:
        tool_ids = {str(tool_call.get("id")) for tool_call in message.tool_calls if tool_call.get("id")}
        for candidate_index, candidate in enumerate(messages):
            if candidate.role == "tool" and candidate.tool_call_id in tool_ids:
                indices.add(candidate_index)
    return indices
