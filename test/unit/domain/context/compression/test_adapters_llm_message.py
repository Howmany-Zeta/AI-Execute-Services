"""LLMMessage ↔ ContentBlock adapter tests."""

from __future__ import annotations

from aiecs.domain.context.compression.adapters.llm_message import (
    blocks_to_llm_message,
    blocks_to_llm_messages,
    llm_message_to_blocks,
    llm_messages_to_blocks,
)
from aiecs.domain.context.compression.types import ImageBlock, TextBlock, ToolResultBlock, ToolUseBlock

from .conftest import make_multimodal_message, make_n_turn_history, make_tool_pair_messages


def test_round_trip_simple_user_message() -> None:
    messages = make_n_turn_history(2)
    blocks = llm_messages_to_blocks(messages)
    roles = [message.role for message in messages]
    restored = blocks_to_llm_messages(roles, blocks)
    assert len(restored) == 2
    assert restored[0].role == "user"
    assert restored[0].content == "turn-1-user"
    assert restored[1].content == "turn-2-assistant"


def test_tool_pair_preserves_ids() -> None:
    messages = make_tool_pair_messages(tool_call_id="call_pair_1")
    blocks = llm_messages_to_blocks(messages)
    assert isinstance(blocks[0][0], ToolUseBlock)
    assert blocks[0][0].id == "call_pair_1"
    assert isinstance(blocks[1][0], ToolResultBlock)
    assert blocks[1][0].tool_use_id == "call_pair_1"

    restored = blocks_to_llm_messages(
        [message.role for message in messages],
        blocks,
    )
    assert restored[0].tool_calls is not None
    assert restored[0].tool_calls[0]["id"] == "call_pair_1"
    assert restored[1].role == "tool"
    assert restored[1].tool_call_id == "call_pair_1"
    assert restored[1].content == "file contents here"


def test_multimodal_round_trip() -> None:
    message = make_multimodal_message()
    blocks = llm_message_to_blocks(message)
    assert any(isinstance(block, TextBlock) for block in blocks)
    assert any(isinstance(block, ImageBlock) for block in blocks)

    restored = blocks_to_llm_message("user", blocks)
    assert restored.content == "Describe this image"
    assert len(restored.images) == 1


def test_blocks_to_llm_messages_length_guard() -> None:
    try:
        blocks_to_llm_messages(["user"], [[TextBlock(text="hi")], [TextBlock(text="bye")]])
    except ValueError as exc:
        assert "same length" in str(exc)
    else:
        raise AssertionError("expected ValueError for mismatched lengths")
