# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""W5 / O9: compaction result assembly and public exports."""

from __future__ import annotations

from typing import Any

from aiecs.llm import LLMMessage

from aiecs.domain.context.compression.types import (
    CompactAttachment,
    CompactionKind,
    CompactionResult,
    CompactTrigger,
)

__all__ = [
    "CompactAttachment",
    "CompactionKind",
    "CompactionResult",
    "CompactTrigger",
    "build_post_compact_messages",
    "create_compact_boundary_message",
    "render_compact_attachment",
]


def render_compact_attachment(attachment: CompactAttachment) -> LLMMessage:
    header = f"[Compact attachment: {attachment.kind}] {attachment.title}".strip()
    text = f"{header}\n{attachment.body}".strip()
    return LLMMessage(role="user", content=text)


def create_compact_boundary_message(metadata: dict[str, Any]) -> LLMMessage:
    lines = [
        "[Compact boundary marker]",
        "Earlier conversation was compacted. Use the summary and preserved assets below as the continuity boundary.",
    ]
    trigger = str(metadata.get("trigger") or "").strip()
    compact_kind = str(metadata.get("compact_kind") or "").strip()
    pre_messages = metadata.get("pre_compact_message_count")
    pre_tokens = metadata.get("pre_compact_token_count")
    post_messages = metadata.get("post_compact_message_count")
    post_tokens = metadata.get("post_compact_token_count")
    if trigger:
        lines.append(f"Trigger: {trigger}")
    if compact_kind:
        lines.append(f"Compaction kind: {compact_kind}")
    if pre_messages is not None or pre_tokens is not None:
        lines.append("Pre-compact footprint: " f"messages={pre_messages if pre_messages is not None else 'unknown'}, " f"tokens={pre_tokens if pre_tokens is not None else 'unknown'}")
    if post_messages is not None or post_tokens is not None:
        lines.append("Post-compact footprint: " f"messages={post_messages if post_messages is not None else 'unknown'}, " f"tokens={post_tokens if post_tokens is not None else 'unknown'}")
    anchor = str(metadata.get("preserved_segment_anchor") or "").strip()
    if anchor:
        lines.append(f"Preserved segment anchor: {anchor}")
    return LLMMessage(role="user", content="\n".join(lines))


def build_post_compact_messages(result: CompactionResult) -> list[LLMMessage]:
    """Rebuild post-compact messages: boundary → summary → keep → attachments."""
    rebuilt: list[LLMMessage] = []
    if result.boundary_marker is not None:
        rebuilt.append(result.boundary_marker)
    rebuilt.extend(result.summary_messages)
    rebuilt.extend(result.messages_to_keep)
    rebuilt.extend(render_compact_attachment(item) for item in result.attachments)
    rebuilt.extend(render_compact_attachment(item) for item in result.hook_results)
    return rebuilt
