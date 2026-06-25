# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Bidirectional adapter between ConversationMessage and ContentBlock lists."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Sequence

from aiecs.llm import LLMMessage

from aiecs.domain.context.compression.adapters.llm_message import (
    blocks_to_llm_message,
    llm_message_to_blocks,
)
from aiecs.domain.context.compression.types import (
    ContentBlock,
    ImageBlock,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
)
from aiecs.domain.context.context_engine import ConversationMessage

_METADATA_BLOCKS_KEY = "compression_blocks"


def conversation_message_to_blocks(message: ConversationMessage) -> list[ContentBlock]:
    """Convert ContextEngine ConversationMessage into content blocks."""
    metadata = message.metadata or {}
    serialized = metadata.get(_METADATA_BLOCKS_KEY)
    blocks: list[ContentBlock] = []
    if message.content:
        blocks.append(TextBlock(text=message.content))
    if isinstance(serialized, list) and serialized:
        blocks.extend(_dict_to_block(item) for item in serialized if isinstance(item, dict))
    return blocks


def conversation_messages_to_blocks(
    messages: Sequence[ConversationMessage],
) -> list[list[ContentBlock]]:
    return [conversation_message_to_blocks(message) for message in messages]


def blocks_to_conversation_message(
    blocks: Sequence[ContentBlock],
    *,
    role: str,
    timestamp: datetime,
    metadata: dict[str, Any] | None = None,
) -> ConversationMessage:
    """Convert content blocks back into ConversationMessage."""
    base_metadata = dict(metadata or {})
    text_parts: list[str] = []
    structured_blocks: list[dict[str, Any]] = []

    for block in blocks:
        if isinstance(block, TextBlock):
            text_parts.append(block.text)
        else:
            structured_blocks.append(_block_to_dict(block))

    content = "\n".join(part for part in text_parts if part)
    if structured_blocks:
        base_metadata[_METADATA_BLOCKS_KEY] = structured_blocks

    return ConversationMessage(
        role=role,
        content=content,
        timestamp=timestamp,
        metadata=base_metadata or None,
    )


def blocks_to_conversation_messages(
    messages: Sequence[tuple[str, Sequence[ContentBlock], datetime]],
    *,
    metadata_by_message: Sequence[dict[str, Any] | None] | None = None,
) -> list[ConversationMessage]:
    meta_list = metadata_by_message or [None] * len(messages)
    if len(meta_list) != len(messages):
        raise ValueError("metadata_by_message must match messages length")
    return [
        blocks_to_conversation_message(
            blocks,
            role=role,
            timestamp=timestamp,
            metadata=metadata,
        )
        for (role, blocks, timestamp), metadata in zip(messages, meta_list, strict=True)
    ]


def _block_to_dict(block: ContentBlock) -> dict[str, Any]:
    if isinstance(block, TextBlock):
        return {"type": "text", "text": block.text}
    if isinstance(block, ToolUseBlock):
        return {
            "type": "tool_use",
            "id": block.id,
            "name": block.name,
            "input": block.input,
        }
    if isinstance(block, ToolResultBlock):
        return {
            "type": "tool_result",
            "tool_use_id": block.tool_use_id,
            "content": block.content,
            "is_error": block.is_error,
        }
    if isinstance(block, ImageBlock):
        return {
            "type": "image",
            "source": block.source,
            "media_type": block.media_type,
            "source_path": block.source_path,
        }
    raise TypeError(f"Unsupported block type: {type(block)!r}")


def _dict_to_block(data: dict[str, Any]) -> ContentBlock:
    block_type = data.get("type")
    if block_type == "text":
        return TextBlock(text=str(data.get("text", "")))
    if block_type == "tool_use":
        raw_input = data.get("input", {})
        if isinstance(raw_input, str):
            raw_input = json.loads(raw_input)
        return ToolUseBlock(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            input=dict(raw_input),
        )
    if block_type == "tool_result":
        return ToolResultBlock(
            tool_use_id=str(data.get("tool_use_id", "")),
            content=str(data.get("content", "")),
            is_error=bool(data.get("is_error", False)),
        )
    if block_type == "image":
        return ImageBlock(
            source=str(data.get("source", "")),
            media_type=data.get("media_type"),
            source_path=str(data.get("source_path", "")),
        )
    raise ValueError(f"Unknown block type in metadata: {block_type!r}")


def conversation_message_to_llm_message(message: ConversationMessage) -> LLMMessage:
    blocks = conversation_message_to_blocks(message)
    return blocks_to_llm_message(message.role, blocks)


def conversation_messages_to_llm_messages(
    messages: Sequence[ConversationMessage],
) -> list[LLMMessage]:
    return [conversation_message_to_llm_message(message) for message in messages]


def llm_message_to_conversation_message(
    message: LLMMessage,
    *,
    timestamp: datetime | None = None,
) -> ConversationMessage:
    blocks = llm_message_to_blocks(message)
    return blocks_to_conversation_message(
        blocks,
        role=message.role,
        timestamp=timestamp or datetime.now(timezone.utc),
    )


def llm_messages_to_conversation_messages(
    messages: Sequence[LLMMessage],
    *,
    timestamp: datetime | None = None,
) -> list[ConversationMessage]:
    ts = timestamp or datetime.now(timezone.utc)
    return [llm_message_to_conversation_message(message, timestamp=ts) for message in messages]
