"""O6 hook registry and executor tests."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from aiecs.llm import LLMMessage

from aiecs.domain.context.compression.constants import TIME_BASED_MC_CLEARED_MESSAGE
from aiecs.domain.context.compression.hooks import HookEvent, HookExecutor, HookRegistry
from aiecs.domain.context.compression.orchestrator import auto_compact_if_needed
from aiecs.domain.context.compression.policy import CompressionPolicy
from aiecs.domain.context.compression.state import AutoCompactState
from aiecs.domain.context.compression.tokens import estimate_message_tokens
from aiecs.domain.context.compression.types import (
    PostCompactContext,
    PreCompactContext,
    PreCompactResult,
)


def _mcp_tool_pair(index: int, *, content_len: int = 600) -> list[LLMMessage]:
    tool_id = f"toolu_{index}"
    return [
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
            content="snapshot " * content_len,
            tool_call_id=tool_id,
        ),
    ]


def test_hook_registry_register_pre_and_post() -> None:
    registry = HookRegistry()
    pre = AsyncMock(return_value=PreCompactResult())
    post = AsyncMock(return_value=None)

    registry.register(HookEvent.PRE_COMPACT, pre)
    registry.register(HookEvent.POST_COMPACT, post)

    assert len(registry.pre_hooks) == 1
    assert len(registry.post_hooks) == 1


@pytest.mark.asyncio
async def test_pre_compact_hook_blocks_compaction() -> None:
    messages: list[LLMMessage] = []
    for index in range(4):
        messages.extend(_mcp_tool_pair(index))

    token_estimate = estimate_message_tokens(messages)
    policy = CompressionPolicy(
        auto_compact_threshold_tokens=max(500, token_estimate - 500),
        preserve_recent=1,
        chain=("microcompact",),
    )
    registry = HookRegistry()

    async def block_pre(_ctx: PreCompactContext) -> PreCompactResult:
        return PreCompactResult(block=True)

    registry.register_pre(block_pre)
    hooks = HookExecutor(registry)

    compacted, did_compact = await auto_compact_if_needed(
        messages,
        policy=policy,
        state=AutoCompactState(),
        llm_client=AsyncMock(),
        hooks=hooks,
    )

    assert did_compact is False
    assert compacted == messages
    assert TIME_BASED_MC_CLEARED_MESSAGE not in [
        m.content for m in compacted if m.role == "tool"
    ]


@pytest.mark.asyncio
async def test_pre_compact_hook_appends_instructions() -> None:
    messages = [LLMMessage(role="user", content="hello " * 2000)]
    policy = CompressionPolicy(
        auto_compact_threshold_tokens=100,
        preserve_recent=1,
        chain=("microcompact",),
    )
    registry = HookRegistry()
    captured: dict[str, Any] = {}

    async def append_pre(ctx: PreCompactContext) -> PreCompactResult:
        captured["count"] = len(ctx.messages)
        return PreCompactResult(append_instructions="Focus on billing errors.")

    registry.register_pre(append_pre)
    hooks = HookExecutor(registry)

    await auto_compact_if_needed(
        messages,
        policy=policy,
        state=AutoCompactState(),
        llm_client=AsyncMock(),
        hooks=hooks,
        force=True,
    )

    assert captured["count"] >= len(messages)


@pytest.mark.asyncio
async def test_post_compact_hook_receives_summary() -> None:
    messages = [LLMMessage(role="user", content="word " * 400)] * 8
    policy = CompressionPolicy(
        context_window_tokens=500,
        preserve_recent=2,
        chain=("llm",),
    )
    registry = HookRegistry()
    seen: dict[str, Any] = {}

    async def capture_post(ctx: PostCompactContext) -> None:
        seen["summary"] = ctx.summary_text
        seen["result"] = ctx.result

    registry.register_post(capture_post)
    hooks = HookExecutor(registry)

    from aiecs.domain.context.compression.types import CompactionResult

    fake_result = CompactionResult(
        trigger="auto",
        compact_kind="full",
        summary_messages=[LLMMessage(role="user", content="summary body")],
        messages_to_keep=list(messages[-2:]),
    )

    with patch(
        "aiecs.domain.context.compression.orchestrator.compact_conversation",
        new=AsyncMock(return_value=fake_result),
    ):
        await auto_compact_if_needed(
            messages,
            policy=policy,
            state=AutoCompactState(),
            llm_client=AsyncMock(),
            hooks=hooks,
            force=True,
        )

    assert "summary body" in (seen.get("summary") or "")
    assert seen.get("result") is fake_result


@pytest.mark.asyncio
async def test_post_compact_hook_runs_on_microcompact_early_exit() -> None:
    messages: list[LLMMessage] = []
    for index in range(4):
        messages.extend(_mcp_tool_pair(index))

    token_estimate = estimate_message_tokens(messages)
    policy = CompressionPolicy(
        auto_compact_threshold_tokens=max(500, token_estimate - 500),
        preserve_recent=1,
        chain=("microcompact",),
    )
    registry = HookRegistry()
    seen: dict[str, Any] = {}

    async def capture_post(ctx: PostCompactContext) -> None:
        seen["checkpoint"] = ctx.result.compact_metadata.get("checkpoint")
        seen["result"] = ctx.result

    registry.register_post(capture_post)
    hooks = HookExecutor(registry)

    compacted, did_compact = await auto_compact_if_needed(
        messages,
        policy=policy,
        state=AutoCompactState(),
        llm_client=AsyncMock(),
        hooks=hooks,
    )

    assert did_compact is True
    assert seen.get("checkpoint") == "microcompact_early_exit"
    assert seen.get("result") is not None
    assert TIME_BASED_MC_CLEARED_MESSAGE in [
        m.content for m in compacted if m.role == "tool"
    ]
