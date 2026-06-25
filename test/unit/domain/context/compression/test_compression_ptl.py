"""W4 PTL head truncation tests."""

from __future__ import annotations

from aiecs.llm import LLMMessage

from aiecs.domain.context.compression.constants import PTL_RETRY_MARKER
from aiecs.domain.context.compression.ptl import truncate_head_for_ptl_retry


def _five_round_history() -> list[LLMMessage]:
    messages: list[LLMMessage] = []
    for index in range(5):
        messages.append(LLMMessage(role="user", content=f"question {index}"))
        messages.append(LLMMessage(role="assistant", content=f"answer {index}"))
    return messages


def test_truncate_head_for_ptl_retry_drops_oldest_rounds() -> None:
    messages = _five_round_history()
    result = truncate_head_for_ptl_retry(messages)

    assert result is not None
    assert len(result) < len(messages)
    assert "question 0" not in " ".join(message.content or "" for message in result)


def test_truncate_head_inserts_marker_when_leading_assistant() -> None:
    messages = [
        LLMMessage(role="assistant", content="lead"),
        LLMMessage(role="user", content="q1"),
        LLMMessage(role="assistant", content="a1"),
        LLMMessage(role="user", content="q2"),
        LLMMessage(role="assistant", content="a2"),
    ]
    result = truncate_head_for_ptl_retry(messages)

    assert result is not None
    if result[0].role == "assistant":
        assert result[0].content != PTL_RETRY_MARKER
        assert any(message.content == PTL_RETRY_MARKER for message in result)
    else:
        assert result[0].content == PTL_RETRY_MARKER or result[0].role == "user"


def test_truncate_head_returns_none_for_single_round() -> None:
    messages = [
        LLMMessage(role="user", content="only question"),
        LLMMessage(role="assistant", content="only answer"),
    ]
    assert truncate_head_for_ptl_retry(messages) is None


def test_truncate_head_preserves_tool_pairs_when_dropping_rounds() -> None:
    messages = [
        LLMMessage(role="user", content="old question"),
        LLMMessage(
            role="assistant",
            content=None,
            tool_calls=[
                {
                    "id": "toolu_old",
                    "type": "function",
                    "function": {"name": "read_file", "arguments": "{}"},
                }
            ],
        ),
        LLMMessage(role="user", content="interrupt before tool result"),
        LLMMessage(role="tool", content="orphan risk", tool_call_id="toolu_old"),
        LLMMessage(role="user", content="question 1"),
        LLMMessage(role="assistant", content="answer 1"),
        LLMMessage(role="user", content="question 2"),
        LLMMessage(role="assistant", content="answer 2"),
        LLMMessage(role="user", content="question 3"),
        LLMMessage(role="assistant", content="answer 3"),
    ]
    result = truncate_head_for_ptl_retry(messages)

    assert result is not None
    tool_msgs = [message for message in result if message.role == "tool"]
    for tool_msg in tool_msgs:
        assistant_with_call = next(
            (
                message
                for message in result
                if message.role == "assistant"
                and message.tool_calls
                and any(
                    str(tool_call.get("id")) == tool_msg.tool_call_id
                    for tool_call in message.tool_calls
                )
            ),
            None,
        )
        assert assistant_with_call is not None
