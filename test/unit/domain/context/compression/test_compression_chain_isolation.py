"""Phase 2 compact chain isolation tests."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from aiecs.llm import LLMMessage

from aiecs.domain.context.compression.llm_compact import run_phase2_compact_chain
from aiecs.domain.context.compression.types import NoOpSessionMemoryPort


@dataclass
class _MockResponse:
    content: str


class _MockLLMClient:
    async def generate_text(self, *, messages, max_tokens, system_prompt=""):
        _ = messages, max_tokens, system_prompt
        return _MockResponse(content="<summary>chain fallback summary</summary>")


def _long_tool_history() -> list[LLMMessage]:
    messages: list[LLMMessage] = []
    for index in range(6):
        tool_id = f"toolu_{index}"
        messages.extend(
            [
                LLMMessage(role="user", content=f"task {index}"),
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
                    content=f"snapshot payload {index} " * 500,
                    tool_call_id=tool_id,
                ),
            ]
        )
    messages.extend(
        [
            LLMMessage(role="user", content="latest question"),
            LLMMessage(role="assistant", content="latest answer"),
        ]
    )
    return messages


@pytest.mark.asyncio
async def test_chain_falls_back_to_llm_when_session_memory_noop() -> None:
    compacted = await run_phase2_compact_chain(
        _long_tool_history(),
        llm_client=_MockLLMClient(),
        session_memory=NoOpSessionMemoryPort(),
        preserve_recent=4,
    )
    assert len(compacted) < len(_long_tool_history())
    assert any(
        "continued from a previous conversation" in (message.content or "")
        or "Compact boundary marker" in (message.content or "")
        for message in compacted
    )


@pytest.mark.asyncio
async def test_chain_uses_session_memory_when_available() -> None:
    class _Port:
        async def read_compact_text(self, *, session_id: str) -> str | None:
            return "Persisted session memory summary."

        async def write_turn_summary(self, *, session_id: str, text: str) -> None:
            return None

    compacted = await run_phase2_compact_chain(
        _long_tool_history(),
        llm_client=_MockLLMClient(),
        session_memory=_Port(),
        session_id="sess-chain",
        preserve_recent=4,
    )
    assert any(
        "Persisted session memory summary" in (message.content or "")
        or "Session memory summary" in (message.content or "")
        for message in compacted
    )
