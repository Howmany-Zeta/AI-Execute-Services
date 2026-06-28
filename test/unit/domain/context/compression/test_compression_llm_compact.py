"""W5 compact_conversation tests."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock, patch

import pytest

from aiecs.llm import LLMMessage

from aiecs.domain.context.compression.llm_compact import (
    _split_messages_by_token_budget,
    compact_conversation,
)
from aiecs.domain.context.compression.tokens import estimate_message_tokens
from aiecs.domain.context.compression.result import build_post_compact_messages
from aiecs.domain.context.compression.state import AutoCompactState
from aiecs.domain.context.compression.types import (
    CompactionResult,
    PostCompactContext,
    PostCompactHook,
    PreCompactContext,
    PreCompactResult,
    PreCompactHook,
)


@dataclass
class _MockResponse:
    content: str


class _MockLLMClient:
    def __init__(self, content: str = "<summary>condensed history</summary>") -> None:
        self.content = content
        self.calls: list[dict] = []

    async def generate_text(self, *, messages, max_tokens, system_prompt=""):
        self.calls.append(
            {
                "messages": list(messages),
                "max_tokens": max_tokens,
                "system_prompt": system_prompt,
            }
        )
        return _MockResponse(content=self.content)


@pytest.mark.asyncio
async def test_compact_conversation_uses_llm_and_builds_summary_message() -> None:
    messages = [
        LLMMessage(role="user", content=f"question {index}")
        if index % 2 == 0
        else LLMMessage(role="assistant", content=f"answer {index}")
        for index in range(8)
    ]
    client = _MockLLMClient()

    result = await compact_conversation(
        messages,
        llm_client=client,
        preserve_recent=2,
        summary_role="user",
    )

    assert client.calls
    assert result.summary_messages
    assert "continued from a previous conversation" in (
        result.summary_messages[0].content or ""
    )
    rebuilt = build_post_compact_messages(result)
    assert len(rebuilt) < len(messages)


@pytest.mark.asyncio
async def test_compact_conversation_summary_role_system() -> None:
    messages = [LLMMessage(role="user", content="q")] * 8
    result = await compact_conversation(
        messages,
        llm_client=_MockLLMClient(),
        preserve_recent=2,
        summary_role="system",
    )
    assert result.summary_messages[0].role == "system"


@pytest.mark.asyncio
async def test_compact_conversation_microcompact_uses_preserve_recent() -> None:
    from unittest.mock import patch

    messages = [LLMMessage(role="user", content="q")] * 8
    client = _MockLLMClient()

    with patch(
        "aiecs.domain.context.compression.llm_compact.microcompact_messages",
        return_value=(messages, 0),
    ) as mock_mc:
        await compact_conversation(
            messages,
            llm_client=client,
            preserve_recent=2,
        )

    mock_mc.assert_called_once()
    assert mock_mc.call_args.kwargs["keep_recent"] == 2


class _BlockingPreHook:
    async def __call__(self, ctx: PreCompactContext) -> PreCompactResult:
        return PreCompactResult(block=True)


class _AppendPreHook:
    async def __call__(self, ctx: PreCompactContext) -> PreCompactResult:
        return PreCompactResult(append_instructions="Keep tool names explicit.")


class _PostHook:
    def __init__(self) -> None:
        self.called = False
        self.summary_text = ""

    async def __call__(self, ctx: PostCompactContext) -> None:
        self.called = True
        self.summary_text = ctx.summary_text


@pytest.mark.asyncio
async def test_pre_compact_hook_can_block() -> None:
    messages = [LLMMessage(role="user", content="q")] * 8
    result = await compact_conversation(
        messages,
        llm_client=_MockLLMClient(),
        preserve_recent=2,
        pre_compact_hook=_BlockingPreHook(),
    )
    assert result.compact_metadata.get("reason") == "pre-compact hook blocked compaction"


@pytest.mark.asyncio
async def test_hook_stubs_are_invoked() -> None:
    messages = [LLMMessage(role="user", content="q")] * 8
    post = _PostHook()
    await compact_conversation(
        messages,
        llm_client=_MockLLMClient(),
        preserve_recent=2,
        pre_compact_hook=_AppendPreHook(),
        post_compact_hook=post,
    )
    assert post.called
    assert "condensed history" in post.summary_text


@pytest.mark.asyncio
async def test_summary_chunk_size_none_uses_single_summarize_call() -> None:
    messages = [LLMMessage(role="user", content="segment " * 200)] * 10
    client = _MockLLMClient()

    await compact_conversation(
        messages,
        llm_client=client,
        preserve_recent=2,
        summary_chunk_size=None,
    )

    assert len(client.calls) == 1


def test_split_messages_by_token_budget_splits_oversized_single_message() -> None:
    huge_tool_dump = LLMMessage(role="tool", content="output " * 4000, tool_call_id="call-1")
    chunks = _split_messages_by_token_budget([huge_tool_dump], max_tokens=500)

    assert len(chunks) >= 2
    for chunk in chunks:
        assert estimate_message_tokens(chunk) <= 500


def test_split_messages_by_token_budget_splits_oversized_user_message() -> None:
    huge_message = LLMMessage(role="user", content="segment " * 3000)
    chunks = _split_messages_by_token_budget([huge_message], max_tokens=400)

    assert len(chunks) >= 2
    for chunk in chunks:
        assert estimate_message_tokens(chunk) <= 400


@pytest.mark.asyncio
async def test_summary_chunk_size_splits_oversized_single_message_into_multiple_calls() -> None:
    messages = [
        LLMMessage(role="tool", content="dump " * 5000, tool_call_id="call-1"),
        LLMMessage(role="user", content="follow-up question"),
        LLMMessage(role="assistant", content="recent answer"),
    ]
    client = _MockLLMClient()

    result = await compact_conversation(
        messages,
        llm_client=client,
        preserve_recent=2,
        summary_chunk_size=500,
    )

    assert len(client.calls) >= 2
    assert len(result.summary_messages) == 1


@pytest.mark.asyncio
async def test_summary_chunk_size_splits_into_multiple_summarize_calls() -> None:
    messages = [
        LLMMessage(role="user" if index % 2 == 0 else "assistant", content="token " * 300)
        for index in range(12)
    ]
    client = _MockLLMClient()

    result = await compact_conversation(
        messages,
        llm_client=client,
        preserve_recent=2,
        summary_chunk_size=500,
    )

    assert len(client.calls) >= 2
    assert len(result.summary_messages) == 1
    assert "continued from a previous conversation" in (result.summary_messages[0].content or "")


@pytest.mark.asyncio
async def test_orchestrator_llm_step_passes_summary_chunk_size() -> None:
    from aiecs.domain.context.compression.orchestrator import auto_compact_if_needed
    from aiecs.domain.context.compression.policy import CompressionPolicy

    policy = CompressionPolicy(
        enabled=True,
        chain=("llm",),
        preserve_recent=2,
        summary_chunk_size=500,
        auto_compact_threshold_tokens=1,
    )
    messages = [LLMMessage(role="user", content="word " * 300)] * 8

    with patch(
        "aiecs.domain.context.compression.orchestrator.compact_conversation",
        new=AsyncMock(),
    ) as mock_compact:
        mock_compact.return_value = CompactionResult(
            trigger="auto",
            compact_kind="full",
            boundary_marker=LLMMessage(role="user", content="boundary"),
            summary_messages=[LLMMessage(role="user", content="summary")],
            messages_to_keep=messages[-2:],
        )

        await auto_compact_if_needed(
            messages,
            policy=policy,
            state=AutoCompactState(),
            llm_client=_MockLLMClient(),
            force=True,
        )

    assert mock_compact.await_args.kwargs["summary_chunk_size"] == 500


@pytest.mark.asyncio
@pytest.mark.compression
async def test_a5_integration_token_drop_and_single_summary() -> None:
    messages = [
        LLMMessage(role="user" if index % 2 == 0 else "assistant", content=f"segment-{index} " + ("word " * 250))
        for index in range(14)
    ]
    client = _MockLLMClient(content="<summary>coverage of older segments</summary>")

    result = await compact_conversation(
        messages,
        llm_client=client,
        preserve_recent=2,
        summary_chunk_size=500,
    )
    rebuilt = build_post_compact_messages(result)

    assert len(rebuilt) < len(messages)
    assert len(result.summary_messages) == 1
    assert len(client.calls) >= 2
    assert "coverage of older segments" in (result.summary_messages[0].content or "")
