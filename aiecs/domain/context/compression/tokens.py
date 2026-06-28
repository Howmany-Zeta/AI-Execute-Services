# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""W8a: block-level token estimation and inline compress gate (A1)."""

from __future__ import annotations

import os
from typing import Any, Sequence

from aiecs.llm import LLMMessage

from aiecs.domain.context.compression.adapters.llm_message import llm_message_to_blocks
from aiecs.domain.context.compression.constants import (
    AUTOCOMPACT_BUFFER_TOKENS,
    DEFAULT_CONTEXT_WINDOW,
    DEFAULT_VISION_IMAGE_TOKEN_ESTIMATE,
    MAX_OUTPUT_TOKENS_FOR_SUMMARY,
    TOKEN_ESTIMATION_PADDING,
)
from aiecs.domain.context.compression.types import (
    ImageBlock,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
)


def estimate_tokens(text: str) -> int:
    """Estimate tokens from plain text using OpenHarness char heuristic."""
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)


def _vision_token_budget_per_image() -> int:
    raw = os.environ.get("AIECS_IMAGE_TOKEN_ESTIMATE", "").strip()
    if not raw:
        raw = os.environ.get("OPENHARNESS_IMAGE_TOKEN_ESTIMATE", "").strip()
    if raw:
        try:
            return max(64, int(raw))
        except ValueError:
            pass
    return DEFAULT_VISION_IMAGE_TOKEN_ESTIMATE


def estimate_message_tokens(messages: Sequence[LLMMessage]) -> int:
    """Estimate total tokens for messages, including 4/3 padding."""
    total = 0
    image_token_estimate = _vision_token_budget_per_image()
    for message in messages:
        for block in llm_message_to_blocks(message):
            if isinstance(block, TextBlock):
                total += estimate_tokens(block.text)
            elif isinstance(block, ToolResultBlock):
                total += estimate_tokens(block.content)
            elif isinstance(block, ToolUseBlock):
                total += estimate_tokens(block.name)
                total += estimate_tokens(str(block.input))
            elif isinstance(block, ImageBlock):
                total += image_token_estimate
    return int(total * TOKEN_ESTIMATION_PADDING)


def estimate_transcript_tokens(history: list[dict[str, Any]]) -> int:
    """Estimate tokens for formatted ``{role, content}`` transcript rows (F7 preview)."""
    from aiecs.llm import LLMMessage

    messages = [LLMMessage(role=str(row.get("role", "user")), content=row.get("content")) for row in history if isinstance(row, dict)]
    return estimate_message_tokens(messages)


def get_autocompact_threshold(
    *,
    context_window_tokens: int = DEFAULT_CONTEXT_WINDOW,
    buffer_tokens: int = AUTOCOMPACT_BUFFER_TOKENS,
    auto_compact_threshold_tokens: int | None = None,
) -> int:
    """Calculate token threshold at which auto-compact should fire."""
    if auto_compact_threshold_tokens is not None and auto_compact_threshold_tokens > 0:
        return int(auto_compact_threshold_tokens)
    reserved = min(MAX_OUTPUT_TOKENS_FOR_SUMMARY, 20_000)
    effective = context_window_tokens - reserved
    return effective - buffer_tokens


def should_compress_messages(
    messages: Sequence[LLMMessage],
    *,
    context_window_tokens: int = DEFAULT_CONTEXT_WINDOW,
    buffer_tokens: int = AUTOCOMPACT_BUFFER_TOKENS,
    auto_compact_threshold_tokens: int | None = None,
    force: bool = False,
    enabled: bool = True,
) -> bool:
    """Epic 1 inline gate; M3 delegates to CompressionPolicy + should_compress."""
    if not enabled:
        return False
    if force:
        return True
    threshold = get_autocompact_threshold(
        context_window_tokens=context_window_tokens,
        buffer_tokens=buffer_tokens,
        auto_compact_threshold_tokens=auto_compact_threshold_tokens,
    )
    return estimate_message_tokens(messages) >= threshold
