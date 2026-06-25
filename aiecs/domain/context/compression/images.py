# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""W10: replace image payloads with compaction placeholders (A19)."""

from __future__ import annotations

from aiecs.llm import LLMMessage

from aiecs.domain.context.compression.adapters.llm_message import (
    blocks_to_llm_message,
    llm_message_to_blocks,
)
from aiecs.domain.context.compression.types import ContentBlock, ImageBlock, TextBlock


def _replace_images_with_compaction_placeholders(
    messages: list[LLMMessage],
) -> list[LLMMessage]:
    """Strip image payloads from summarizer-only compact requests."""
    replaced: list[LLMMessage] = []
    for message in messages:
        blocks = llm_message_to_blocks(message)
        next_blocks: list[ContentBlock] = []
        changed = False
        for block in blocks:
            if isinstance(block, ImageBlock):
                changed = True
                label = block.source_path.strip() or block.source.strip() or "inline"
                next_blocks.append(TextBlock(text=(f"[Image omitted from compaction summarization; " f"source: {label}.]\n")))
            else:
                next_blocks.append(block)
        if changed:
            replaced.append(blocks_to_llm_message(message.role, next_blocks))
        else:
            replaced.append(message)
    return replaced


def replace_images_for_compaction(messages: list[LLMMessage]) -> list[LLMMessage]:
    """Public alias for image placeholder replacement before LLM compact."""
    return _replace_images_with_compaction_placeholders(messages)
