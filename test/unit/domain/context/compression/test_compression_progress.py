"""O7 CompactProgressEvent callback and async-iterator tests."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiecs.llm import LLMMessage

from aiecs.domain.context.compression.orchestrator import auto_compact_if_needed
from aiecs.domain.context.compression.policy import CompressionPolicy
from aiecs.domain.context.compression.progress import (
    COMPACT_PROGRESS_PHASES,
    CompactProgressEmitter,
    CompactProgressEvent,
)
from aiecs.domain.context.compression.state import AutoCompactState
from aiecs.domain.context.compression.tokens import estimate_message_tokens


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


def test_compact_progress_phases_include_required_set() -> None:
    required = {
        "hooks_start",
        "microcompact_start",
        "microcompact_done",
        "compact_start",
        "compact_done",
        "compact_failed",
        "compact_retry",
        "compact_retry_prompt_too_long",
    }
    assert required.issubset(set(COMPACT_PROGRESS_PHASES))


def test_on_progress_callback_receives_events() -> None:
    received: list[CompactProgressEvent] = []

    def on_progress(event: CompactProgressEvent) -> None:
        received.append(event)

    emitter = CompactProgressEmitter(on_progress=on_progress)
    emitter.emit("microcompact_start", pre_tokens=100)
    emitter.emit("microcompact_done", pre_tokens=100, post_tokens=40)

    assert [event.phase for event in received] == [
        "microcompact_start",
        "microcompact_done",
    ]
    assert received[0].pre_tokens == 100
    assert received[1].post_tokens == 40


@pytest.mark.asyncio
async def test_iter_compact_progress_async_iterator_path() -> None:
    messages: list[LLMMessage] = []
    for index in range(4):
        messages.extend(_mcp_tool_pair(index))

    token_estimate = estimate_message_tokens(messages)
    policy = CompressionPolicy(
        auto_compact_threshold_tokens=max(500, token_estimate - 500),
        preserve_recent=1,
        chain=("microcompact",),
    )
    progress = CompactProgressEmitter()
    phases: list[str] = []

    async def collect() -> None:
        async for event in progress.iter_compact_progress():
            phases.append(event.phase)

    collector = asyncio.create_task(collect())
    await asyncio.sleep(0)

    await auto_compact_if_needed(
        messages,
        policy=policy,
        state=AutoCompactState(),
        llm_client=AsyncMock(),
        progress=progress,
    )

    await collector

    assert "microcompact_start" in phases
    assert "microcompact_done" in phases
    assert "compact_done" in phases
    assert len(set(phases)) >= 3


@pytest.mark.asyncio
async def test_compact_failed_emits_progress_phase() -> None:
    messages = [LLMMessage(role="user", content="word " * 400)] * 8
    policy = CompressionPolicy(
        context_window_tokens=500,
        preserve_recent=2,
        chain=("llm",),
    )
    callback_phases: list[str] = []
    progress = CompactProgressEmitter(
        on_progress=lambda event: callback_phases.append(event.phase)
    )

    with patch(
        "aiecs.domain.context.compression.orchestrator.compact_conversation",
        new=AsyncMock(side_effect=RuntimeError("compact boom")),
    ):
        compacted, did_compact = await auto_compact_if_needed(
            messages,
            policy=policy,
            state=AutoCompactState(),
            llm_client=AsyncMock(),
            progress=progress,
            force=True,
        )

    assert did_compact is False
    assert compacted == messages
    assert "compact_failed" in callback_phases


@pytest.mark.asyncio
async def test_compact_retry_emitted_after_prior_failure() -> None:
    messages = [LLMMessage(role="user", content="word " * 400)] * 8
    policy = CompressionPolicy(
        context_window_tokens=500,
        preserve_recent=2,
        chain=("llm",),
        max_consecutive_failures=5,
    )
    state = AutoCompactState(consecutive_failures=1)
    phases: list[str] = []
    progress = CompactProgressEmitter(on_progress=lambda e: phases.append(e.phase))

    with patch(
        "aiecs.domain.context.compression.orchestrator.compact_conversation",
        new=AsyncMock(side_effect=RuntimeError("compact boom")),
    ):
        compacted, did_compact = await auto_compact_if_needed(
            messages,
            policy=policy,
            state=state,
            llm_client=AsyncMock(),
            progress=progress,
            force=True,
        )

    assert did_compact is False
    assert phases.index("compact_retry") < phases.index("compact_failed")


@pytest.mark.asyncio
async def test_compact_retry_prompt_too_long_on_reactive_ptl() -> None:
    from aiecs.domain.context.compression.orchestrator import on_prompt_too_long

    messages = [LLMMessage(role="user", content="x" * 1000)]
    policy = CompressionPolicy(enabled=True, chain=("llm",))
    state = AutoCompactState()
    phases: list[str] = []
    progress = CompactProgressEmitter(on_progress=lambda e: phases.append(e.phase))

    with patch(
        "aiecs.domain.context.compression.orchestrator.auto_compact_if_needed",
        new=AsyncMock(return_value=(messages, True)),
    ):
        did = await on_prompt_too_long(
            RuntimeError("prompt too long for model context window"),
            messages=messages,
            policy=policy,
            state=state,
            llm_client=AsyncMock(),
            progress=progress,
        )

    assert did is True
    assert "compact_retry_prompt_too_long" in phases
