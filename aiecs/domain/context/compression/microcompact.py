# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""W2: microcompact — clear old compactable tool results (A7)."""

from __future__ import annotations

import os

from aiecs.llm import LLMMessage

from aiecs.domain.context.compression.constants import (
    COMPACTABLE_TOOLS,
    DEFAULT_KEEP_RECENT,
    TIME_BASED_MC_CLEARED_MESSAGE,
)
from aiecs.domain.context.compression.gvr_preserve import is_gvr_protected_tool_content

DEFAULT_MICROCOMPACT_TOOL_RESULT_CHARS = 4_000


def microcompact_tool_result_chars() -> int:
    raw = os.environ.get("AIECS_MICROCOMPACT_TOOL_RESULT_CHARS", "").strip()
    if not raw:
        return DEFAULT_MICROCOMPACT_TOOL_RESULT_CHARS
    try:
        return max(256, int(raw))
    except ValueError:
        return DEFAULT_MICROCOMPACT_TOOL_RESULT_CHARS


def is_microcompactable_tool_result(tool_name: str, content: str) -> bool:
    """Return True when a tool result is eligible for old-result clearing."""
    normalized = tool_name.strip()
    if normalized.startswith("mcp__"):
        return True
    return len(content) >= microcompact_tool_result_chars()


def microcompact_messages(
    messages: list[LLMMessage],
    *,
    keep_recent: int = DEFAULT_KEEP_RECENT,
) -> tuple[list[LLMMessage], int]:
    """Clear old compactable tool results, keeping the most recent *keep_recent*."""
    keep_recent = max(1, keep_recent)
    ordered_ids, tool_names, result_content = _collect_compactable_tool_ids(messages)

    if len(ordered_ids) <= keep_recent:
        return messages, 0

    keep_set = set(ordered_ids[-keep_recent:])
    clear_set = set(ordered_ids) - keep_set

    tokens_saved = 0
    compacted: list[LLMMessage] = []
    for message in messages:
        if message.role != "tool" or message.tool_call_id not in clear_set:
            compacted.append(message)
            continue
        if message.content == TIME_BASED_MC_CLEARED_MESSAGE:
            compacted.append(message)
            continue
        original = message.content or ""
        tokens_saved += max(1, len(original) // 4)
        compacted.append(
            LLMMessage(
                role="tool",
                content=TIME_BASED_MC_CLEARED_MESSAGE,
                tool_call_id=message.tool_call_id,
            )
        )

    return compacted, tokens_saved


def _collect_compactable_tool_ids(
    messages: list[LLMMessage],
) -> tuple[list[str], dict[str, str], dict[str, str]]:
    ordered_ids: list[str] = []
    tool_names: dict[str, str] = {}
    result_content: dict[str, str] = {}

    for message in messages:
        if message.role == "assistant":
            for tool_call in message.tool_calls or []:
                tool_id = str(tool_call.get("id") or "")
                if not tool_id:
                    continue
                ordered_ids.append(tool_id)
                fn = tool_call.get("function") or {}
                tool_names[tool_id] = str(fn.get("name") or tool_call.get("name") or "")
        elif message.role == "tool" and message.tool_call_id:
            result_content[message.tool_call_id] = message.content or ""

    compactable_ids = [
        tool_id
        for tool_id in ordered_ids
        if not is_gvr_protected_tool_content(result_content.get(tool_id, ""))
        and (
            tool_names.get(tool_id, "") in COMPACTABLE_TOOLS
            or is_microcompactable_tool_result(
                tool_names.get(tool_id, ""),
                result_content.get(tool_id, ""),
            )
        )
    ]
    return compactable_ids, tool_names, result_content
