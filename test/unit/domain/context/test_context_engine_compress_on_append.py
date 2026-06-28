"""O8 ContextEngine compress_on_append unit tests."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiecs.domain.context.context_engine import ContextEngine, ConversationMessage, CompressionConfig
from aiecs.domain.context.compression.hooks import HookExecutor, HookRegistry
from aiecs.domain.context.compression.policy import CompressionPolicy
from aiecs.domain.context.compression.types import PostCompactContext
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


@pytest.mark.asyncio
async def test_compress_on_append_passes_layer_ce_metadata() -> None:
    """G4: O8 compact passes F2 pre-compact metadata with layer=CE."""
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

    session_id = "sess-ce-meta"
    engine._memory_conversations[session_id] = [
        ConversationMessage(role="user", content="hello", timestamp=datetime.utcnow())
    ]

    compacted = [LLMMessage(role="user", content="compact")]
    with patch(
        "aiecs.domain.context.compression.orchestrator.auto_compact_if_needed",
        new=AsyncMock(return_value=(compacted, True)),
    ) as mock_compact:
        await engine.compress_on_append_if_needed(session_id)

    metadata = mock_compact.await_args.kwargs["compact_metadata"]
    assert metadata["layer"] == "CE"
    assert metadata["session_id"] == session_id
    assert "estimated_tokens" in metadata


@pytest.mark.asyncio
async def test_compress_on_append_post_hook_metadata_layer_ce() -> None:
    """G4: POST compact hook receives layer=CE from orchestrator."""
    captured_post: list[dict] = []

    registry = HookRegistry()

    async def capture_post(ctx: PostCompactContext) -> None:
        captured_post.append(dict(ctx.metadata))

    registry.register_post(capture_post)
    hooks = HookExecutor(registry)

    engine = ContextEngine(
        compression_policy=CompressionPolicy(
            enabled=True,
            auto_compact_threshold_tokens=10,
            chain=("microcompact",),
            preserve_recent=0,
            context_window_tokens=100,
            buffer_tokens=0,
        ),
        compress_on_append=True,
        hook_executor=hooks,
    )
    await engine.initialize()

    session_id = "sess-ce-post"
    engine._memory_conversations[session_id] = [
        ConversationMessage(role="user", content="word " * 200, timestamp=datetime.utcnow()),
        ConversationMessage(role="assistant", content="reply " * 200, timestamp=datetime.utcnow()),
    ]

    with patch(
        "aiecs.domain.context.compression.orchestrator.should_compress",
        side_effect=[True, False],
    ):
        with patch(
            "aiecs.domain.context.compression.orchestrator.microcompact_messages",
            side_effect=lambda msgs, **kwargs: (msgs[:1], 100),
        ):
            await engine.compress_on_append_if_needed(session_id)

    assert captured_post
    assert captured_post[0]["layer"] == "CE"
    assert captured_post[0]["checkpoint"]


@pytest.mark.asyncio
async def test_ce_summarize_honors_policy_summary_role_user() -> None:
    """G4: CE summarization uses CompressionPolicy.summary_role default user."""
    engine = ContextEngine(
        llm_client=AsyncMock(),
        compression_policy=CompressionPolicy(summary_role="user"),
    )
    messages = [
        ConversationMessage(role="user", content=f"msg {i}", timestamp=datetime.utcnow())
        for i in range(5)
    ]
    config = CompressionConfig(strategy="summarize", keep_recent=2)

    mock_result = MagicMock(
        summary_messages=[LLMMessage(role="user", content="summary")],
        messages_to_keep=[LLMMessage(role="user", content="recent")],
    )
    with patch(
        "aiecs.domain.context.compression.llm_compact.compact_conversation",
        new=AsyncMock(return_value=mock_result),
    ) as mock_compact:
        compressed = await engine._compress_with_summarization(messages, config)

    assert mock_compact.await_args.kwargs["summary_role"] == "user"
    assert compressed[0].role == "user"


@pytest.mark.asyncio
async def test_ce_summarize_scholar_override_system_role() -> None:
    """G4: compression_summary_role overrides policy for Scholar migration."""
    engine = ContextEngine(
        llm_client=AsyncMock(),
        compression_policy=CompressionPolicy(summary_role="user"),
        compression_summary_role="system",
    )
    messages = [
        ConversationMessage(role="user", content=f"msg {i}", timestamp=datetime.utcnow())
        for i in range(5)
    ]
    config = CompressionConfig(strategy="summarize", keep_recent=2)

    mock_result = MagicMock(
        summary_messages=[LLMMessage(role="system", content="summary")],
        messages_to_keep=[],
    )
    with patch(
        "aiecs.domain.context.compression.llm_compact.compact_conversation",
        new=AsyncMock(return_value=mock_result),
    ) as mock_compact:
        await engine._compress_with_summarization(messages, config)

    assert mock_compact.await_args.kwargs["summary_role"] == "system"
