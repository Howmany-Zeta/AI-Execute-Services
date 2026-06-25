"""ConversationMessage ↔ ContentBlock adapter tests."""

from __future__ import annotations

from datetime import datetime, timezone

from aiecs.domain.context.compression.adapters.conversation_message import (
    blocks_to_conversation_message,
    conversation_message_to_blocks,
    conversation_messages_to_blocks,
)
from aiecs.domain.context.compression.types import ImageBlock, TextBlock, ToolResultBlock, ToolUseBlock
from aiecs.domain.context.context_engine import ConversationMessage


def test_text_message_round_trip() -> None:
    timestamp = datetime(2026, 6, 25, 12, 0, tzinfo=timezone.utc)
    original = ConversationMessage(
        role="assistant",
        content="hello from scholar",
        timestamp=timestamp,
        metadata={"source": "test"},
    )
    blocks = conversation_message_to_blocks(original)
    assert blocks == [TextBlock(text="hello from scholar")]

    restored = blocks_to_conversation_message(
        blocks,
        role=original.role,
        timestamp=timestamp,
        metadata={"source": "test"},
    )
    assert restored.role == "assistant"
    assert restored.content == "hello from scholar"
    assert restored.timestamp == timestamp
    assert restored.metadata == {"source": "test"}


def test_structured_blocks_persist_in_metadata() -> None:
    timestamp = datetime(2026, 6, 25, 12, 0, tzinfo=timezone.utc)
    blocks = [
        TextBlock(text="running grep"),
        ToolUseBlock(id="call_9", name="grep", input={"pattern": "foo"}),
        ToolResultBlock(tool_use_id="call_9", content="line 42"),
    ]
    message = blocks_to_conversation_message(
        blocks,
        role="assistant",
        timestamp=timestamp,
    )
    round_blocks = conversation_message_to_blocks(message)
    assert isinstance(round_blocks[0], TextBlock)
    assert isinstance(round_blocks[1], ToolUseBlock)
    assert round_blocks[1].id == "call_9"
    assert isinstance(round_blocks[2], ToolResultBlock)
    assert round_blocks[2].content == "line 42"


def test_conversation_messages_to_blocks_batch() -> None:
    ts = datetime(2026, 6, 25, tzinfo=timezone.utc)
    messages = [
        ConversationMessage(role="user", content="q1", timestamp=ts),
        ConversationMessage(role="assistant", content="a1", timestamp=ts),
    ]
    blocks = conversation_messages_to_blocks(messages)
    assert len(blocks) == 2
    assert blocks[0][0].text == "q1"
    assert blocks[1][0].text == "a1"


def test_image_block_round_trip_via_metadata() -> None:
    timestamp = datetime(2026, 6, 25, tzinfo=timezone.utc)
    blocks = [
        TextBlock(text="see image"),
        ImageBlock(source="https://example.com/x.png", media_type="image/png"),
    ]
    message = blocks_to_conversation_message(
        blocks,
        role="user",
        timestamp=timestamp,
    )
    restored_blocks = conversation_message_to_blocks(message)
    assert any(isinstance(block, ImageBlock) for block in restored_blocks)
