"""W2 microcompact tests."""

from __future__ import annotations

from aiecs.llm import LLMMessage

from aiecs.domain.context.compression.constants import TIME_BASED_MC_CLEARED_MESSAGE
from aiecs.domain.context.compression.microcompact import (
    is_microcompactable_tool_result,
    microcompact_messages,
)


def _mcp_snapshot_pair(index: int) -> list[LLMMessage]:
    tool_id = f"toolu_snapshot_{index}"
    return [
        LLMMessage(
            role="assistant",
            content=None,
            tool_calls=[
                {
                    "id": tool_id,
                    "type": "function",
                    "function": {
                        "name": "mcp__playwright__browser_snapshot",
                        "arguments": "{}",
                    },
                }
            ],
        ),
        LLMMessage(
            role="tool",
            content=f"snapshot {index} " * 600,
            tool_call_id=tool_id,
        ),
    ]


def test_microcompact_clears_old_mcp_results() -> None:
    messages: list[LLMMessage] = []
    for index in range(3):
        messages.extend(_mcp_snapshot_pair(index))

    compacted, tokens_saved = microcompact_messages(messages, keep_recent=1)

    assert tokens_saved > 0
    contents = [message.content for message in compacted if message.role == "tool"]
    assert contents[0] == TIME_BASED_MC_CLEARED_MESSAGE
    assert contents[1] == TIME_BASED_MC_CLEARED_MESSAGE
    assert contents[2].startswith("snapshot 2")


def test_microcompact_large_non_allowlisted_results(monkeypatch) -> None:
    monkeypatch.setenv("AIECS_MICROCOMPACT_TOOL_RESULT_CHARS", "256")
    messages = [
        LLMMessage(
            role="assistant",
            content=None,
            tool_calls=[
                {
                    "id": "toolu_custom_0",
                    "type": "function",
                    "function": {"name": "custom_snapshot_tool", "arguments": "{}"},
                }
            ],
        ),
        LLMMessage(role="tool", content="A" * 512, tool_call_id="toolu_custom_0"),
        LLMMessage(
            role="assistant",
            content=None,
            tool_calls=[
                {
                    "id": "toolu_custom_1",
                    "type": "function",
                    "function": {"name": "custom_snapshot_tool", "arguments": "{}"},
                }
            ],
        ),
        LLMMessage(role="tool", content="B" * 512, tool_call_id="toolu_custom_1"),
    ]

    compacted, tokens_saved = microcompact_messages(messages, keep_recent=1)

    assert tokens_saved > 0
    contents = [message.content for message in compacted if message.role == "tool"]
    assert contents[0] == TIME_BASED_MC_CLEARED_MESSAGE
    assert contents[1] == "B" * 512


def test_is_microcompactable_mcp_prefix() -> None:
    assert is_microcompactable_tool_result("mcp__foo", "tiny")
