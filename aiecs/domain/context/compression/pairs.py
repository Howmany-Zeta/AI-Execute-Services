# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""W1: tool_use/tool_result pair preservation and message sanitization (A22)."""

from __future__ import annotations

from aiecs.llm import LLMMessage


def split_preserving_tool_pairs(messages: list[LLMMessage], index: int) -> int:
    """Return a split index that does not cut through a tool_use/tool_result pair."""
    index = max(0, min(index, len(messages)))
    if index >= len(messages):
        return index
    while index > 0 and _boundary_crosses_tool_pair(messages[index - 1], messages[index]):
        index -= 1
    return index


def split_messages_preserving_tool_pairs(
    messages: list[LLMMessage],
    *,
    preserve_recent: int,
) -> tuple[list[LLMMessage], list[LLMMessage]]:
    """Split older/newer segments without breaking tool pairs."""
    if len(messages) <= preserve_recent:
        return [], sanitize_messages_for_compaction(list(messages))

    split_index = split_preserving_tool_pairs(messages, len(messages) - preserve_recent)
    older = list(messages[:split_index])
    newer = sanitize_messages_for_compaction(list(messages[split_index:]))
    return older, newer


def sanitize_messages_for_compaction(messages: list[LLMMessage]) -> list[LLMMessage]:
    """Normalize messages into a provider-safe sequence for compaction."""
    sanitized: list[LLMMessage] = []
    pending_tool_use_ids: set[str] = set()
    pending_tool_use_index: int | None = None

    for message in messages:
        if message.role == "assistant" and _is_effectively_empty(message):
            continue

        tool_calls = message.tool_calls if message.role == "assistant" else None
        is_tool_result = message.role == "tool"

        matched_pending_tool_results = False
        if pending_tool_use_ids:
            if not is_tool_result or message.tool_call_id not in pending_tool_use_ids:
                if pending_tool_use_index is not None and pending_tool_use_index < len(sanitized):
                    sanitized.pop(pending_tool_use_index)
                pending_tool_use_ids = set()
                pending_tool_use_index = None
            else:
                matched_pending_tool_results = True
                pending_tool_use_ids = set()
                pending_tool_use_index = None

        if is_tool_result and not matched_pending_tool_results:
            known_ids = {tc.get("id") for prior in sanitized for tc in (prior.tool_calls or []) if tc.get("id")}
            if message.tool_call_id not in known_ids:
                continue

        sanitized.append(message)

        if tool_calls:
            pending_tool_use_ids = {str(tool_call.get("id")) for tool_call in tool_calls if tool_call.get("id")}
            pending_tool_use_index = len(sanitized) - 1

    if pending_tool_use_ids and pending_tool_use_index is not None and pending_tool_use_index < len(sanitized):
        sanitized.pop(pending_tool_use_index)

    return sanitized


def _boundary_crosses_tool_pair(previous: LLMMessage, current: LLMMessage) -> bool:
    if previous.role != "assistant" or current.role != "tool":
        return False
    pending_tool_ids = {str(tool_call.get("id")) for tool_call in (previous.tool_calls or []) if tool_call.get("id")}
    if not pending_tool_ids:
        return False
    return current.tool_call_id in pending_tool_ids


def _is_effectively_empty(message: LLMMessage) -> bool:
    if message.tool_calls:
        return False
    if message.images:
        return False
    return not (message.content or "").strip()
