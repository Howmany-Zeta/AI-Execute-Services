"""OpenHarness Phase 1 parity spot-checks (inputs mirrored; no runtime import)."""

from __future__ import annotations

from aiecs.llm import LLMMessage

from aiecs.domain.context.compression.collapse import _collapse_text, try_context_collapse
from aiecs.domain.context.compression.constants import TIME_BASED_MC_CLEARED_MESSAGE
from aiecs.domain.context.compression.microcompact import microcompact_messages
from aiecs.domain.context.compression.pairs import split_preserving_tool_pairs


def test_parity_collapse_text_limit_matches_openharness() -> None:
    giant = ("alpha " * 1200).strip()
    collapsed = _collapse_text(giant)
    assert len(giant) > 2400
    assert "[collapsed" in collapsed
    assert collapsed.count("alpha") >= 2


def test_parity_microcompact_three_snapshot_tools() -> None:
    messages: list[LLMMessage] = []
    for index in range(3):
        tool_id = f"toolu_snapshot_{index}"
        messages.extend(
            [
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
        )

    compacted, tokens_saved = microcompact_messages(messages, keep_recent=1)
    contents = [message.content for message in compacted if message.role == "tool"]

    assert tokens_saved > 0
    assert contents[0] == TIME_BASED_MC_CLEARED_MESSAGE
    assert contents[1] == TIME_BASED_MC_CLEARED_MESSAGE
    assert contents[2].startswith("snapshot 2")


def test_parity_context_collapse_giant_history() -> None:
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


def test_parity_split_preserving_tool_pair_boundary() -> None:
    messages = [
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

    assert split_preserving_tool_pairs(messages, 2) == 1
