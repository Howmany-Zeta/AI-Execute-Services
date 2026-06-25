"""W6 session memory compaction tests."""

from __future__ import annotations

import pytest

from aiecs.llm import LLMMessage

from aiecs.domain.context.compression.session_memory import try_session_memory_compaction
from aiecs.domain.context.compression.types import NoOpSessionMemoryPort


def _long_history(count: int = 20) -> list[LLMMessage]:
    messages: list[LLMMessage] = []
    for index in range(count):
        role = "user" if index % 2 == 0 else "assistant"
        messages.append(
            LLMMessage(role=role, content=(f"{role} {index} " * 200).strip())
        )
    return messages


@pytest.mark.asyncio
async def test_noop_session_memory_port_returns_none() -> None:
    result = await try_session_memory_compaction(
        _long_history(),
        session_memory=NoOpSessionMemoryPort(),
        metadata={"session_id": "sess-1"},
    )
    assert result is None


@pytest.mark.asyncio
async def test_session_memory_compaction_builds_summary_for_long_history() -> None:
    class _MemoryPort:
        def __init__(self) -> None:
            self.written: dict[str, str] = {}

        async def read_compact_text(self, *, session_id: str) -> str | None:
            return None

        async def write_turn_summary(self, *, session_id: str, text: str) -> None:
            self.written[session_id] = text

    port = _MemoryPort()
    result = await try_session_memory_compaction(
        _long_history(),
        session_memory=port,
        preserve_recent=12,
        metadata={"session_id": "sess-write"},
    )
    assert result is not None
    assert result.compact_kind == "session_memory"
    assert result.summary_messages
    assert "Session memory summary" in (result.summary_messages[0].content or "")
    assert "sess-write" in port.written
    assert port.written["sess-write"] == (result.summary_messages[0].content or "")
