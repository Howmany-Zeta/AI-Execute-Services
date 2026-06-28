# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Context Compression

Smart context compression for token limits.

.. note::
    This module delegates to ``aiecs.domain.context.compression`` kernel primitives.
    **Deprecated:** ``ContextCompressor`` emits :class:`DeprecationWarning` on
    construction; scheduled removal in **aiecs 2.2.0**. New code should use
    ``auto_compact_if_needed``, ``compact_formatted_transcript``, or
    ``maybe_compact_before_llm`` (see ``aiecs/docs/host/context_compression_integration.md``).
"""

import asyncio
import logging
import warnings
from typing import List, Optional, Any
from enum import Enum

from aiecs.llm import LLMMessage

logger = logging.getLogger(__name__)


class CompressionStrategy(Enum):
    """Context compression strategies (legacy integration API).

    Maps to kernel primitives in ``aiecs.domain.context.compression``:
    ``PRESERVE_RECENT`` / ``TRUNCATE_START`` → truncation helpers;
    ``TRUNCATE_MIDDLE`` → ``TruncationMode.TRUNCATE_MIDDLE``;
    ``SUMMARIZE`` → ``compact_conversation`` / orchestrator llm step.
    """

    TRUNCATE_MIDDLE = "truncate_middle"
    TRUNCATE_START = "truncate_start"
    PRESERVE_RECENT = "preserve_recent"
    SUMMARIZE = "summarize"


class ContextCompressor:
    """
    Smart context compression for managing token limits.

    Example:
        compressor = ContextCompressor(max_tokens=4000)
        compressed = compressor.compress_messages(messages)
    """

    def __init__(
        self,
        max_tokens: int = 4000,
        strategy: CompressionStrategy = CompressionStrategy.PRESERVE_RECENT,
        preserve_system: bool = True,
        llm_client: Any = None,
    ):
        """
        Initialize context compressor.

        Args:
            max_tokens: Maximum token limit
            strategy: Compression strategy
            preserve_system: Always preserve system messages
            llm_client: Optional LLM client for SUMMARIZE strategy (ADR-008)
        """
        warnings.warn(
            "ContextCompressor is deprecated and will be removed in aiecs 2.2.0. " "Use auto_compact_if_needed, compact_formatted_transcript, or " "maybe_compact_before_llm instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.max_tokens = max_tokens
        self.strategy = strategy
        self.preserve_system = preserve_system
        self.llm_client = llm_client

    def compress_messages(
        self,
        messages: List[LLMMessage],
        priority_indices: Optional[List[int]] = None,
    ) -> List[LLMMessage]:
        """
        Compress message list to fit within token limit.

        Args:
            messages: List of messages
            priority_indices: Optional indices of high-priority messages

        Returns:
            Compressed message list
        """
        total_tokens = self._estimate_tokens(messages)

        if total_tokens <= self.max_tokens:
            return messages

        logger.debug(
            "Compressing %d messages from ~%d to ~%d tokens",
            len(messages),
            total_tokens,
            self.max_tokens,
        )

        if self.strategy == CompressionStrategy.PRESERVE_RECENT:
            return self._compress_preserve_recent(messages, priority_indices)
        if self.strategy == CompressionStrategy.TRUNCATE_MIDDLE:
            return self._compress_truncate_middle(messages, priority_indices)
        if self.strategy == CompressionStrategy.TRUNCATE_START:
            return self._compress_truncate_start(messages)
        if self.strategy == CompressionStrategy.SUMMARIZE:
            return self._compress_summarize(messages, priority_indices)
        return self._compress_preserve_recent(messages, priority_indices)

    def _compress_preserve_recent(
        self,
        messages: List[LLMMessage],
        priority_indices: Optional[List[int]],
    ) -> List[LLMMessage]:
        from aiecs.domain.context.compression.truncation import compress_preserve_recent

        return compress_preserve_recent(
            messages,
            max_tokens=self.max_tokens,
            priority_indices=set(priority_indices or []),
            preserve_system=self.preserve_system,
        )

    def _compress_summarize(
        self,
        messages: List[LLMMessage],
        priority_indices: Optional[List[int]],
    ) -> List[LLMMessage]:
        """Delegate SUMMARIZE to the shared compression kernel (ADR-008)."""
        _ = priority_indices
        if self.llm_client is None:
            from aiecs.domain.context.compression.legacy import compact_messages

            preserve_recent = max(2, min(6, len(messages) // 3 or 2))
            return compact_messages(messages, preserve_recent=preserve_recent)

        from aiecs.domain.context.compression.llm_compact import compact_conversation
        from aiecs.domain.context.compression.result import build_post_compact_messages

        preserve_recent = max(2, min(6, len(messages) // 3 or 2))

        async def _run() -> List[LLMMessage]:
            result = await compact_conversation(
                messages,
                llm_client=self.llm_client,
                preserve_recent=preserve_recent,
            )
            return build_post_compact_messages(result)

        return asyncio.run(_run())

    def _compress_truncate_middle(
        self,
        messages: List[LLMMessage],
        priority_indices: Optional[List[int]],
    ) -> List[LLMMessage]:
        _ = priority_indices
        from aiecs.domain.context.compression.truncation import (
            compress_to_token_limit,
        )
        from aiecs.domain.context.compression.types import TruncationMode

        return compress_to_token_limit(
            messages,
            max_tokens=self.max_tokens,
            mode=TruncationMode.TRUNCATE_MIDDLE,
            preserve_system=self.preserve_system,
        )

    def _compress_truncate_start(self, messages: List[LLMMessage]) -> List[LLMMessage]:
        from aiecs.domain.context.compression.truncation import (
            compress_with_earlier_placeholder,
        )

        return compress_with_earlier_placeholder(
            messages,
            max_tokens=self.max_tokens,
            preserve_system=self.preserve_system,
        )

    def _estimate_tokens(self, messages: List[LLMMessage]) -> int:
        from aiecs.domain.context.compression.tokens import estimate_message_tokens

        return estimate_message_tokens(messages)

    def compress_text(self, text: str, max_tokens: int) -> str:
        from aiecs.domain.context.compression.tokens import estimate_tokens

        estimated_tokens = estimate_tokens(text)

        if estimated_tokens <= max_tokens:
            return text

        max_chars = max_tokens * 4
        if len(text) <= max_chars:
            return text

        return text[: max_chars - 20] + "... [truncated]"


def compress_messages(
    messages: List[LLMMessage],
    max_tokens: int = 4000,
    strategy: CompressionStrategy = CompressionStrategy.PRESERVE_RECENT,
) -> List[LLMMessage]:
    """
    Convenience function for compressing messages.

    Args:
        messages: List of messages
        max_tokens: Maximum token limit
        strategy: Compression strategy

    Returns:
        Compressed message list
    """
    compressor = ContextCompressor(max_tokens=max_tokens, strategy=strategy)
    return compressor.compress_messages(messages)
