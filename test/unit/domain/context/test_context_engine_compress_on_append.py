"""O8 ContextEngine compress_on_append unit tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from aiecs.domain.context.context_engine import ContextEngine, ConversationMessage
from aiecs.domain.context.compression.policy import CompressionPolicy
from aiecs.llm import LLMMessage


@pytest.mark.asyncio
async def test_compress_on_append_if_needed_replaces_history() -> None:
    engine = ContextEngine(
        compression_policy=CompressionPolicy(
            enabled=True,
            auto_compact_threshold_tokens=50,
            chain=("microcompact",),
            preserve_recent=1,
        ),
        compress_on_append=True,
    )
    await engine.initialize()

    session_id = "sess-o8"
    engine._memory_conversations[session_id] = [
        ConversationMessage(role="user", content="hello", timestamp=__import__("datetime").datetime.utcnow())
    ]

    compacted = [LLMMessage(role="user", content="compact")]
    with patch(
        "aiecs.domain.context.compression.orchestrator.auto_compact_if_needed",
        new=AsyncMock(return_value=(compacted, True)),
    ) as mock_compact:
        result = await engine.compress_on_append_if_needed(
            session_id,
            strategy=("microcompact",),
        )

    mock_compact.assert_awaited_once()
    assert mock_compact.await_args.kwargs["strategy"] == ("microcompact",)
    assert result is not None
    assert result["success"] is True
    assert result["resolved_chain"] == ("microcompact",)
    stored = engine._memory_conversations[session_id]
    assert len(stored) == 1
    assert stored[0].content == "compact"


@pytest.mark.asyncio
async def test_add_conversation_message_strategy_override() -> None:
    engine = ContextEngine(
        compression_policy=CompressionPolicy(
            enabled=True,
            chain=("microcompact", "llm"),
        ),
        compress_on_append=True,
    )
    await engine.initialize()
    session_id = "sess-strategy"

    with patch.object(
        engine,
        "compress_on_append_if_needed",
        new=AsyncMock(return_value=None),
    ) as mock_compress:
        await engine.add_conversation_message(
            session_id,
            role="user",
            content="hello",
            strategy="truncate",
        )

    mock_compress.assert_awaited_once_with(session_id, strategy="truncate")
