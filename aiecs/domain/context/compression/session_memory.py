# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""W6: session-memory compaction before LLM summarization (A15)."""

from __future__ import annotations

from typing import Any

from aiecs.llm import LLMMessage

from aiecs.domain.context.compression.constants import (
    SESSION_MEMORY_KEEP_RECENT,
    SESSION_MEMORY_MAX_CHARS,
    SESSION_MEMORY_MAX_LINES,
)
from aiecs.domain.context.compression.pairs import split_messages_preserving_tool_pairs
from aiecs.domain.context.compression.result import (
    build_post_compact_messages,
    create_compact_boundary_message,
)
from aiecs.domain.context.compression.tokens import estimate_message_tokens
from aiecs.domain.context.compression.types import (
    CompactionResult,
    NoOpSessionMemoryPort,
    SessionMemoryPort,
)


async def persist_turn_summary(
    session_memory: SessionMemoryPort | None,
    *,
    session_id: str,
    summary_text: str,
) -> None:
    """Write compact summary for the next A15 cycle (Claude/OpenHarness parity)."""
    if not session_id or not summary_text.strip():
        return
    if session_memory is None or isinstance(session_memory, NoOpSessionMemoryPort):
        return
    await session_memory.write_turn_summary(
        session_id=session_id,
        text=summary_text.strip(),
    )


def _summarize_message_for_memory(message: LLMMessage) -> str:
    text = " ".join((message.content or "").split())
    if text:
        return f"{message.role}: {text[:160]}"
    if message.tool_calls:
        names = [str((tool_call.get("function") or {}).get("name") or tool_call.get("name") or "") for tool_call in message.tool_calls]
        return f"{message.role}: tool calls -> {', '.join(name for name in names if name)}"
    if message.role == "tool":
        return f"{message.role}: tool results returned"
    return f"{message.role}: [non-text content]"


def _build_session_memory_message(messages: list[LLMMessage]) -> LLMMessage | None:
    lines: list[str] = []
    total_chars = 0
    for message in messages:
        line = _summarize_message_for_memory(message)
        if not line:
            continue
        projected = total_chars + len(line) + 1
        if lines and (len(lines) >= SESSION_MEMORY_MAX_LINES or projected >= SESSION_MEMORY_MAX_CHARS):
            lines.append("... earlier context condensed ...")
            break
        lines.append(line)
        total_chars = projected
    if not lines:
        return None
    body = "\n".join(lines)
    return LLMMessage(
        role="user",
        content="Session memory summary from earlier in this conversation:\n" + body,
    )


async def try_session_memory_compaction(
    messages: list[LLMMessage],
    *,
    preserve_recent: int = SESSION_MEMORY_KEEP_RECENT,
    trigger: str = "auto",
    session_memory: SessionMemoryPort | None = None,
    metadata: dict[str, Any] | None = None,
) -> CompactionResult | None:
    """Cheap deterministic compaction for long chats before full LLM compaction."""
    if len(messages) <= preserve_recent + 4:
        return None

    port = session_memory or NoOpSessionMemoryPort()
    if isinstance(port, NoOpSessionMemoryPort):
        return None

    session_id = str((metadata or {}).get("session_id") or "")
    file_summary: LLMMessage | None = None
    if session_id:
        compact_text = await port.read_compact_text(session_id=session_id)
        if compact_text and compact_text.strip():
            file_summary = LLMMessage(role="user", content=compact_text.strip())

    older, newer = split_messages_preserving_tool_pairs(
        messages,
        preserve_recent=preserve_recent,
    )
    summary_message = file_summary or _build_session_memory_message(older)
    if summary_message is None:
        return None

    provisional = [summary_message, *newer]
    if estimate_message_tokens(provisional) >= estimate_message_tokens(messages) and len(provisional) >= len(messages):
        return None

    compact_metadata = {
        "trigger": trigger,
        "compact_kind": "session_memory",
        "pre_compact_message_count": len(messages),
        "pre_compact_token_count": estimate_message_tokens(messages),
        "preserve_recent": preserve_recent,
        "used_session_memory": True,
        "used_file_session_memory": file_summary is not None,
    }
    result = CompactionResult(
        trigger=trigger,  # type: ignore[arg-type]
        compact_kind="session_memory",
        boundary_marker=create_compact_boundary_message(compact_metadata),
        summary_messages=[summary_message],
        messages_to_keep=list(newer),
        attachments=[],
        hook_results=[],
        compact_metadata=compact_metadata,
    )
    post_compact = build_post_compact_messages(result)
    result.compact_metadata["post_compact_message_count"] = len(post_compact)
    result.compact_metadata["post_compact_token_count"] = estimate_message_tokens(post_compact)
    result.boundary_marker = create_compact_boundary_message(result.compact_metadata)
    if session_id:
        await persist_turn_summary(
            port,
            session_id=session_id,
            summary_text=summary_message.content or "",
        )
    return result
