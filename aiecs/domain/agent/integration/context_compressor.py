"""
Context Compression

Smart context compression for token limits.
"""

import logging
from typing import List, Optional, Set
from enum import Enum

from aiecs.llm import LLMMessage

logger = logging.getLogger(__name__)


class CompressionStrategy(Enum):
    """Context compression strategies."""

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
    ):
        """
        Initialize context compressor.

        Args:
            max_tokens: Maximum token limit
            strategy: Compression strategy
            preserve_system: Always preserve system messages
        """
        self.max_tokens = max_tokens
        self.strategy = strategy
        self.preserve_system = preserve_system

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
        # Estimate tokens
        total_tokens = self._estimate_tokens(messages)

        if total_tokens <= self.max_tokens:
            return messages

        logger.debug(f"Compressing {len(messages)} messages from ~{total_tokens} to ~{self.max_tokens} tokens")

        # Apply compression strategy
        if self.strategy == CompressionStrategy.PRESERVE_RECENT:
            return self._compress_preserve_recent(messages, priority_indices)
        elif self.strategy == CompressionStrategy.TRUNCATE_MIDDLE:
            return self._compress_truncate_middle(messages, priority_indices)
        elif self.strategy == CompressionStrategy.TRUNCATE_START:
            return self._compress_truncate_start(messages)
        else:
            # Default: preserve recent
            return self._compress_preserve_recent(messages, priority_indices)

    def _compress_preserve_recent(self, messages: List[LLMMessage], priority_indices: Optional[List[int]]) -> List[LLMMessage]:
        """Preserve recent messages and priority messages."""
        priority_indices_set: Set[int] = set(priority_indices or [])
        compressed: List[LLMMessage] = []

        # Always include system messages if enabled
        if self.preserve_system:
            system_msgs = [msg for msg in messages if msg.role == "system"]
            compressed.extend(system_msgs)

        # Calculate remaining budget
        remaining_tokens = self.max_tokens - self._estimate_tokens(compressed)

        # Add priority messages
        for idx in priority_indices_set:
            if idx < len(messages) and messages[idx] not in compressed:
                msg_tokens = self._estimate_tokens([messages[idx]])
                if msg_tokens <= remaining_tokens:
                    compressed.append(messages[idx])
                    remaining_tokens -= msg_tokens

        # Add recent messages (from end)
        for msg in reversed(messages):
            if msg not in compressed:
                msg_tokens = self._estimate_tokens([msg])
                if msg_tokens <= remaining_tokens:
                    compressed.insert(len(compressed), msg)
                    remaining_tokens -= msg_tokens
                else:
                    break

        return compressed

    def _compress_truncate_middle(self, messages: List[LLMMessage], priority_indices: Optional[List[int]]) -> List[LLMMessage]:
        """Keep start and end messages, truncate middle."""
        if len(messages) <= 4:
            return messages

        # Keep first 2 and last 2 by default
        keep_start = 2
        keep_end = 2

        # Adjust based on token budget
        start_msgs = messages[:keep_start]
        end_msgs = messages[-keep_end:]

        compressed = (
            start_msgs
            + [
                LLMMessage(
                    role="system",
                    content="[... conversation history compressed ...]",
                )
            ]
            + end_msgs
        )

        return compressed

    def _compress_truncate_start(self, messages: List[LLMMessage]) -> List[LLMMessage]:
        """Keep recent messages, truncate start."""
        compressed: List[LLMMessage] = []
        remaining_tokens = self.max_tokens

        # Process from end
        for msg in reversed(messages):
            msg_tokens = self._estimate_tokens([msg])
            if msg_tokens <= remaining_tokens:
                compressed.insert(0, msg)
                remaining_tokens -= msg_tokens
            else:
                break

        return compressed

    def _estimate_tokens(self, messages: List[LLMMessage]) -> int:
        """
        Estimate token count for messages.

        Args:
            messages: List of messages

        Returns:
            Estimated token count
        """
        total_chars = sum(len(msg.content) for msg in messages)
        # Rough estimate: 4 chars ≈ 1 token
        return total_chars // 4

    def compress_text(self, text: str, max_tokens: int) -> str:
        """
        Compress text to fit within token limit.

        Args:
            text: Text to compress
            max_tokens: Maximum tokens

        Returns:
            Compressed text
        """
        estimated_tokens = len(text) // 4

        if estimated_tokens <= max_tokens:
            return text

        # Truncate to fit
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
