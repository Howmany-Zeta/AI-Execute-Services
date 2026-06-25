"""W3 context collapse tests."""

from __future__ import annotations

from aiecs.llm import LLMMessage

from aiecs.domain.context.compression.collapse import _collapse_text, try_context_collapse


def test_collapse_text_head_tail() -> None:
    text = "alpha " * 1200
    collapsed = _collapse_text(text.strip())
    assert "[collapsed" in collapsed
    assert collapsed.startswith("alpha alpha")


def test_try_context_collapse_trims_oversized_messages() -> None:
    giant = ("alpha " * 1200).strip()
    messages = [
        LLMMessage(role="user", content=giant),
        LLMMessage(role="assistant", content=giant),
        LLMMessage(role="user", content=giant),
        LLMMessage(role="assistant", content=giant),
        LLMMessage(role="user", content=giant),
        LLMMessage(role="assistant", content="keep recent"),
        LLMMessage(role="user", content="latest"),
    ]

    result = try_context_collapse(messages, preserve_recent=2)

    assert result is not None
    assert "[collapsed" in (result[0].content or "")


def test_try_context_collapse_trims_oversized_tool_results() -> None:
    giant = ("snapshot node " * 1200).strip()
    messages = [
        LLMMessage(role="user", content="open page"),
        LLMMessage(
            role="assistant",
            content=None,
            tool_calls=[
                {
                    "id": "toolu_snapshot",
                    "type": "function",
                    "function": {
                        "name": "mcp__playwright__browser_snapshot",
                        "arguments": "{}",
                    },
                }
            ],
        ),
        LLMMessage(role="tool", content=giant, tool_call_id="toolu_snapshot"),
        LLMMessage(role="assistant", content="I inspected the snapshot"),
        LLMMessage(role="user", content="latest"),
        LLMMessage(role="assistant", content="keep recent"),
    ]

    result = try_context_collapse(messages, preserve_recent=2)

    assert result is not None
    tool_contents = [
        message.content
        for message in result
        if message.role == "tool" and message.tool_call_id == "toolu_snapshot"
    ]
    assert len(tool_contents) == 1
    assert "[collapsed" in (tool_contents[0] or "")
