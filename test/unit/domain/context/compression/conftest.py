"""Shared factories for compression unit tests."""

from __future__ import annotations

from datetime import datetime, timezone

from aiecs.llm import LLMMessage

from aiecs.domain.context.compression.types import ImageBlock, TextBlock, ToolResultBlock, ToolUseBlock


def make_tool_pair_messages(
    *,
    tool_name: str = "read_file",
    tool_call_id: str = "call_abc123",
    tool_input: dict | None = None,
    tool_result: str = "file contents here",
) -> list[LLMMessage]:
    """Assistant tool_use + matching tool_result pair."""
    tool_input = tool_input or {"path": "/tmp/example.txt"}
    return [
        LLMMessage(
            role="assistant",
            content=None,
            tool_calls=[
                {
                    "id": tool_call_id,
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "arguments": '{"path": "/tmp/example.txt"}',
                    },
                }
            ],
        ),
        LLMMessage(
            role="tool",
            content=tool_result,
            tool_call_id=tool_call_id,
        ),
    ]


def make_long_tool_result(
    *,
    tool_call_id: str = "call_long",
    length: int = 20_000,
    fill: str = "x",
) -> LLMMessage:
    return LLMMessage(
        role="tool",
        content=fill * length,
        tool_call_id=tool_call_id,
    )


def make_multimodal_message(
    *,
    text: str = "Describe this image",
    image_source: str = "https://example.com/image.png",
) -> LLMMessage:
    return LLMMessage(
        role="user",
        content=text,
        images=[{"source": image_source, "media_type": "image/png"}],
    )


def make_n_turn_history(n: int) -> list[LLMMessage]:
    """Alternating user/assistant turns without tool calls."""
    messages: list[LLMMessage] = []
    for index in range(n):
        role = "user" if index % 2 == 0 else "assistant"
        messages.append(
            LLMMessage(role=role, content=f"turn-{index + 1}-{role}")
        )
    return messages


def make_tool_pair_blocks(
    *,
    tool_call_id: str = "call_blocks",
) -> list[list[TextBlock | ToolUseBlock | ToolResultBlock]]:
    return [
        [ToolUseBlock(id=tool_call_id, name="grep", input={"pattern": "foo"})],
        [ToolResultBlock(tool_use_id=tool_call_id, content="match line 1")],
    ]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
