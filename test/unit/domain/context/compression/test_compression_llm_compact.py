"""W5 compact_conversation tests."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from aiecs.llm import LLMMessage

from aiecs.domain.context.compression.llm_compact import compact_conversation
from aiecs.domain.context.compression.result import build_post_compact_messages
from aiecs.domain.context.compression.types import (
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
