"""W12 truncation mode tests (general semantics golden)."""

from __future__ import annotations

from aiecs.llm import LLMMessage

from aiecs.domain.context.compression.pairs import split_preserving_tool_pairs
from aiecs.domain.context.compression.truncation import (
    MIDDLE_PLACEHOLDER,
    compress_preserve_recent,
    compress_with_earlier_placeholder,
    earlier_placeholder_text,
    truncate_middle,
)
from aiecs.domain.context.compression.types import TruncationMode


def _history(count: int) -> list[LLMMessage]:
    return [
        LLMMessage(
            role="user" if index % 2 == 0 else "assistant",
            content=f"message-{index}",
        )
        for index in range(count)
    ]


def test_earlier_placeholder_drops_head_with_marker() -> None:
    messages = _history(10)
    compressed = compress_with_earlier_placeholder(messages, max_tokens=20)
    assert any(
        (message.content or "").startswith("[")
        and "earlier messages omitted" in (message.content or "")
        for message in compressed
    )
    assert len(compressed) < len(messages)


def test_truncate_middle_keeps_head_and_tail() -> None:
    messages = _history(8)
    compressed = truncate_middle(messages, keep_start=2, keep_end=2)
    assert compressed[0].content == "message-0"
    assert compressed[1].content == "message-1"
    assert compressed[2].content == MIDDLE_PLACEHOLDER
    assert compressed[3].content == "message-6"
    assert compressed[4].content == "message-7"


def test_truncate_middle_keeps_tool_pairs_at_tail_boundary() -> None:
    messages = [
        LLMMessage(role="user", content="head-0"),
        LLMMessage(role="user", content="head-1"),
        LLMMessage(
            role="assistant",
            content=None,
            tool_calls=[
                {
                    "id": "toolu_tail",
                    "type": "function",
                    "function": {"name": "read_file", "arguments": "{}"},
                }
            ],
        ),
        LLMMessage(role="user", content="middle filler"),
        LLMMessage(role="tool", content="tool output", tool_call_id="toolu_tail"),
        LLMMessage(role="user", content="tail-1"),
    ]
    compressed = truncate_middle(messages, keep_start=2, keep_end=2)

    tool_msgs = [message for message in compressed if message.role == "tool"]
    for tool_msg in tool_msgs:
        assert any(
            message.role == "assistant"
            and message.tool_calls
            and any(
                str(tool_call.get("id")) == tool_msg.tool_call_id
                for tool_call in message.tool_calls
            )
            for message in compressed
        )


def test_split_preserving_tool_pairs_runs_before_head_drop() -> None:
    messages = [
        LLMMessage(role="user", content="first"),
        LLMMessage(
            role="assistant",
            content=None,
            tool_calls=[
                {
                    "id": "toolu_pair",
                    "type": "function",
                    "function": {"name": "read_file", "arguments": "{}"},
                }
            ],
        ),
        LLMMessage(role="tool", content="ok", tool_call_id="toolu_pair"),
        LLMMessage(role="assistant", content="done"),
    ]
    split_index = split_preserving_tool_pairs(messages, 2)
    assert split_index == 1


def test_earlier_placeholder_text_format() -> None:
    assert earlier_placeholder_text(3) == "[3 earlier messages omitted for context limit]"


def test_truncation_mode_enum_values() -> None:
    assert TruncationMode.EARLIER_PLACEHOLDER.value == "earlier_placeholder"
    assert TruncationMode.TRUNCATE_MIDDLE.value == "truncate_middle"


def test_compress_preserve_recent_keeps_tool_pairs() -> None:
    messages = [
        LLMMessage(role="user", content="first"),
        LLMMessage(
            role="assistant",
            content=None,
            tool_calls=[
                {
                    "id": "toolu_pair",
                    "type": "function",
                    "function": {"name": "read_file", "arguments": "{}"},
                }
            ],
        ),
        LLMMessage(role="tool", content="ok " * 200, tool_call_id="toolu_pair"),
        LLMMessage(role="assistant", content="done"),
        LLMMessage(role="user", content="recent " * 50),
    ]
    compressed = compress_preserve_recent(messages, max_tokens=250)
    tool_msgs = [message for message in compressed if message.role == "tool"]
    for tool_msg in tool_msgs:
        assert any(
            message.role == "assistant"
            and message.tool_calls
            and any(
                str(tool_call.get("id")) == tool_msg.tool_call_id
                for tool_call in message.tool_calls
            )
            for message in compressed
        )
