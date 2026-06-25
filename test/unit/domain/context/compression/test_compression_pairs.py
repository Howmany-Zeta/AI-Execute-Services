"""W1 split_preserving_tool_pairs and sanitize tests."""

from __future__ import annotations

from aiecs.llm import LLMMessage

from aiecs.domain.context.compression.pairs import (
    sanitize_messages_for_compaction,
    split_messages_preserving_tool_pairs,
    split_preserving_tool_pairs,
)


def _tool_pair_messages() -> list[LLMMessage]:
    return [
        LLMMessage(role="user", content="first"),
        LLMMessage(
            role="assistant",
            content=None,
            tool_calls=[
                {
                    "id": "toolu_pair",
                    "type": "function",
                    "function": {"name": "read_file", "arguments": '{"path":"x"}'},
                }
            ],
        ),
        LLMMessage(role="tool", content="ok", tool_call_id="toolu_pair"),
        LLMMessage(role="assistant", content="done"),
    ]


def test_split_preserving_tool_pairs_backs_off_one_index() -> None:
    messages = _tool_pair_messages()
    # Naive split at 2 would cut assistant tool_use from tool result.
    adjusted = split_preserving_tool_pairs(messages, 2)
    assert adjusted == 1


def test_split_messages_keeps_tool_pair_in_preserved_segment() -> None:
    messages = _tool_pair_messages()
    _older, newer = split_messages_preserving_tool_pairs(messages, preserve_recent=2)
    roles_and_tools = [(m.role, m.tool_call_id, bool(m.tool_calls)) for m in newer]
    assert ("assistant", None, True) in roles_and_tools
    assert ("tool", "toolu_pair", False) in roles_and_tools


def test_sanitize_drops_dangling_tool_use() -> None:
    messages = [
        LLMMessage(role="user", content="first"),
        LLMMessage(role="assistant", content="second"),
        LLMMessage(
            role="assistant",
            content=None,
            tool_calls=[
                {
                    "id": "toolu_orphan",
                    "type": "function",
                    "function": {"name": "edit_file", "arguments": "{}"},
                }
            ],
        ),
    ]
    sanitized = sanitize_messages_for_compaction(messages)
    assert not any(
        tc.get("id") == "toolu_orphan"
        for message in sanitized
        for tc in (message.tool_calls or [])
    )


def test_sanitize_drops_orphan_tool_result() -> None:
    messages = [
        LLMMessage(role="user", content="hello"),
        LLMMessage(role="tool", content="unexpected", tool_call_id="missing"),
    ]
    sanitized = sanitize_messages_for_compaction(messages)
    assert all(message.role != "tool" for message in sanitized)
