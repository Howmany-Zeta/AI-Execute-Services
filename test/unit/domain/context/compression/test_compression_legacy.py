"""W7 legacy compact tests."""

from __future__ import annotations

from aiecs.llm import LLMMessage

from aiecs.domain.context.compression.legacy import (
    CONVERSATION_SUMMARY_PREFIX,
    compact_messages,
    summarize_messages,
)


def test_summarize_messages_includes_recent_roles() -> None:
    messages = [
        LLMMessage(role="user", content="first question"),
        LLMMessage(role="assistant", content="first answer"),
        LLMMessage(role="user", content="second question"),
    ]
    summary = summarize_messages(messages, max_messages=2)
    assert "user: second question" in summary
    assert "assistant: first answer" in summary


def test_compact_messages_adds_summary_and_preserves_recent() -> None:
    messages = [
        LLMMessage(role="user", content=f"question {index}")
        if index % 2 == 0
        else LLMMessage(role="assistant", content=f"answer {index}")
        for index in range(6)
    ]
    compacted = compact_messages(messages, preserve_recent=2)
    assert len(compacted) == 3
    assert compacted[0].content.startswith(CONVERSATION_SUMMARY_PREFIX)
