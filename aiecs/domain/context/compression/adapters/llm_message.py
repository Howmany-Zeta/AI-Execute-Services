# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Bidirectional adapter between LLMMessage and ContentBlock lists (ADR-011)."""

from __future__ import annotations

import json
from typing import Any, Sequence

from aiecs.llm import LLMMessage

from aiecs.domain.context.compression.types import (
    ContentBlock,
    ImageBlock,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
)


def llm_message_to_blocks(message: LLMMessage) -> list[ContentBlock]:
    """Convert one LLMMessage into ordered content blocks."""
    if message.role == "tool":
        return [
            ToolResultBlock(
                tool_use_id=message.tool_call_id or "",
                content=message.content or "",
            )
        ]

    blocks: list[ContentBlock] = []

    if message.content:
        blocks.append(TextBlock(text=message.content))

    for image in message.images or []:
        blocks.append(_image_to_block(image))

    for tool_call in message.tool_calls or []:
        blocks.append(_tool_call_to_block(tool_call))

    return blocks


def llm_messages_to_blocks(messages: Sequence[LLMMessage]) -> list[list[ContentBlock]]:
    return [llm_message_to_blocks(message) for message in messages]


def blocks_to_llm_message(role: str, blocks: Sequence[ContentBlock]) -> LLMMessage:
    """Convert content blocks back into a single LLMMessage."""
    text_parts: list[str] = []
    images: list[Any] = []
    tool_calls: list[dict[str, Any]] = []
    tool_call_id: str | None = None
    content: str | None = None

    for block in blocks:
        if isinstance(block, TextBlock):
            text_parts.append(block.text)
        elif isinstance(block, ImageBlock):
            images.append(
                {
                    "source": block.source,
                    "media_type": block.media_type,
                    "source_path": block.source_path,
                }
            )
        elif isinstance(block, ToolUseBlock):
            tool_calls.append(
                {
                    "id": block.id,
                    "type": "function",
                    "function": {
                        "name": block.name,
                        "arguments": json.dumps(block.input),
                    },
                }
            )
        elif isinstance(block, ToolResultBlock):
            tool_call_id = block.tool_use_id
            content = block.content

    if role == "tool":
        return LLMMessage(
            role="tool",
            content=content or "",
            tool_call_id=tool_call_id,
        )

    merged_text = "\n".join(part for part in text_parts if part)
    return LLMMessage(
        role=role,
        content=merged_text or None,
        images=images,
        tool_calls=tool_calls or None,
    )


def blocks_to_llm_messages(
    roles: Sequence[str],
    blocks_by_message: Sequence[Sequence[ContentBlock]],
) -> list[LLMMessage]:
    if len(roles) != len(blocks_by_message):
        raise ValueError("roles and blocks_by_message must have the same length")
    return [blocks_to_llm_message(role, blocks) for role, blocks in zip(roles, blocks_by_message, strict=True)]


def _tool_call_to_block(tool_call: dict[str, Any]) -> ToolUseBlock:
    fn = tool_call.get("function") or {}
    name = fn.get("name") or tool_call.get("name") or ""
    raw_input = fn.get("arguments", tool_call.get("input", {}))
    if isinstance(raw_input, str):
        try:
            parsed_input = json.loads(raw_input)
        except json.JSONDecodeError:
            parsed_input = {"raw": raw_input}
    elif isinstance(raw_input, dict):
        parsed_input = raw_input
    else:
        parsed_input = {"value": raw_input}
    return ToolUseBlock(
        id=str(tool_call.get("id") or ""),
        name=str(name),
        input=parsed_input,
    )


def _image_to_block(image: Any) -> ImageBlock:
    if isinstance(image, str):
        return ImageBlock(source=image, source_path=image)
    if isinstance(image, dict):
        source = str(image.get("source") or image.get("url") or "")
        return ImageBlock(
            source=source,
            media_type=image.get("media_type"),
            source_path=str(image.get("source_path") or source),
        )
    return ImageBlock(source=str(image), source_path=str(image))
