"""O1–O5 orchestrator tests."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from aiecs.llm import LLMMessage

from aiecs.domain.context.compression.constants import TIME_BASED_MC_CLEARED_MESSAGE
from aiecs.domain.context.compression.orchestrator import (
    auto_compact_if_needed,
    is_prompt_too_long_error,
    on_prompt_too_long,
)
from aiecs.domain.context.compression.policy import (
    CompressionPolicy,
    get_autocompact_threshold,
    should_compress,
)
from aiecs.domain.context.compression.state import AutoCompactState
from aiecs.domain.context.compression.tokens import estimate_message_tokens


def _long_history(count: int, *, fill: str = "word ") -> list[LLMMessage]:
    messages: list[LLMMessage] = []
    for index in range(count):
        role = "user" if index % 2 == 0 else "assistant"
        messages.append(LLMMessage(role=role, content=fill * 400 + str(index)))
    return messages


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


def test_get_autocompact_threshold_from_policy() -> None:
    policy = CompressionPolicy(
        context_window_tokens=100_000,
        buffer_tokens=5_000,
        auto_compact_threshold_tokens=80_000,
    )
    assert get_autocompact_threshold(policy) == 80_000


def test_should_compress_respects_disabled_and_force() -> None:
    policy = CompressionPolicy(enabled=False, context_window_tokens=10_000)
    messages = _long_history(5)
    assert should_compress(messages, policy) is False
    assert should_compress(messages, policy, force=True) is True


def test_should_compress_circuit_breaker_blocks_proactive() -> None:
    policy = CompressionPolicy(
        enabled=True,
        context_window_tokens=1_000,
        max_consecutive_failures=2,
    )
    messages = _long_history(8)
    state = AutoCompactState(consecutive_failures=2)
    assert should_compress(messages, policy, state=state) is False
    assert should_compress(messages, policy, state=state, force=True) is True


@pytest.mark.asyncio
async def test_auto_compact_mc_only_early_exit() -> None:
    messages: list[LLMMessage] = []
    for index in range(4):
        messages.extend(_mcp_tool_pair(index))

    token_estimate = estimate_message_tokens(messages)
    policy = CompressionPolicy(
        auto_compact_threshold_tokens=max(500, token_estimate - 500),
        preserve_recent=1,
        chain=("microcompact",),
    )
    state = AutoCompactState()
    llm_client = AsyncMock()

    compacted, did_compact = await auto_compact_if_needed(
        messages,
        policy=policy,
        state=state,
        llm_client=llm_client,
    )

    assert did_compact is True
    llm_client.assert_not_called()
    tool_contents = [m.content for m in compacted if m.role == "tool"]
    assert TIME_BASED_MC_CLEARED_MESSAGE in tool_contents


@pytest.mark.asyncio
async def test_auto_compact_full_chain_calls_llm_step() -> None:
    messages = _long_history(30)
    policy = CompressionPolicy(
        context_window_tokens=500,
        preserve_recent=4,
        chain=("llm",),
    )
    state = AutoCompactState()
    llm_client = AsyncMock()

    from aiecs.domain.context.compression.types import CompactionResult

    fake_result = CompactionResult(
        trigger="auto",
        compact_kind="full",
        summary_messages=[LLMMessage(role="user", content="summary")],
        messages_to_keep=list(messages[-4:]),
    )

    with patch(
        "aiecs.domain.context.compression.orchestrator.compact_conversation",
        new=AsyncMock(return_value=fake_result),
    ):
        compacted, did_compact = await auto_compact_if_needed(
            messages,
            policy=policy,
            state=state,
            llm_client=llm_client,
            force=True,
        )

    assert did_compact is True
    assert compacted[0].content == "summary"
    assert len(compacted) == 5


@pytest.mark.asyncio
async def test_circuit_breaker_skips_proactive_compact() -> None:
    messages = _long_history(20)
    policy = CompressionPolicy(
        context_window_tokens=500,
        max_consecutive_failures=1,
        chain=("llm",),
    )
    state = AutoCompactState(consecutive_failures=1)
    llm_client = AsyncMock()

    result, did_compact = await auto_compact_if_needed(
        messages,
        policy=policy,
        state=state,
        llm_client=llm_client,
    )

    assert did_compact is False
    assert result == messages
    llm_client.assert_not_called()


@pytest.mark.asyncio
async def test_on_prompt_too_long_reactive_once_per_session() -> None:
    messages = _long_history(10)
    policy = CompressionPolicy(context_window_tokens=500, chain=("microcompact",))
    state = AutoCompactState()
    llm_client = AsyncMock()
    exc = RuntimeError("prompt too long for model context window")

    with patch(
        "aiecs.domain.context.compression.orchestrator.auto_compact_if_needed",
        new=AsyncMock(return_value=([LLMMessage(role="user", content="x")], True)),
    ) as mock_compact:
        first = await on_prompt_too_long(
            exc,
            messages=messages,
            policy=policy,
            state=state,
            llm_client=llm_client,
        )
        second = await on_prompt_too_long(
            exc,
            messages=messages,
            policy=policy,
            state=state,
            llm_client=llm_client,
        )

    assert first is True
    assert second is False
    assert state.reactive_compact_used is True
    assert mock_compact.await_count == 1
    assert mock_compact.await_args.kwargs["force"] is True
    assert mock_compact.await_args.kwargs["trigger"] == "reactive"


def test_is_prompt_too_long_error_matches_provider_messages() -> None:
    assert is_prompt_too_long_error(ValueError("context_length_exceeded"))
    assert is_prompt_too_long_error(ValueError("messages resulted in 200k tokens"))
    assert is_prompt_too_long_error(ValueError("exceeds the available context size"))
    assert not is_prompt_too_long_error(ValueError("rate limit"))


def test_ptl_detection_shared_between_orchestrator_and_llm_compact() -> None:
    from aiecs.domain.context.compression.ptl import (
        PROMPT_TOO_LONG_NEEDLES,
        is_prompt_too_long_error as ptl_is_prompt_too_long_error,
    )

    assert ptl_is_prompt_too_long_error is is_prompt_too_long_error
    assert "messages resulted in" in PROMPT_TOO_LONG_NEEDLES
    assert "exceeds the available context size" in PROMPT_TOO_LONG_NEEDLES


@pytest.mark.asyncio
async def test_m3_single_compact_gate_delegates_to_auto_compact_if_needed() -> None:
    """CC-077: tool_loop must delegate to O3 — no inline duplicate gate."""
    from aiecs.domain.agent.tool_loop_core import (
        ToolLoopCompressionContext,
        maybe_compact_before_llm,
    )
    from aiecs.domain.context.compression.hooks import HookExecutor, HookRegistry
    from aiecs.domain.context.compression.progress import CompactProgressEmitter
    from aiecs.domain.context.compression.types import InMemorySessionMemoryPort

    messages = [LLMMessage(role="user", content="hello")]
    session_memory = InMemorySessionMemoryPort()
    hooks = HookExecutor(HookRegistry())
    progress = CompactProgressEmitter()
    ctx = ToolLoopCompressionContext(
        enabled=True,
        policy=CompressionPolicy(enabled=True),
        llm_client=object(),
        auto_compact_state=AutoCompactState(),
        session_memory=session_memory,
        hooks=hooks,
        progress=progress,
    )

    with patch(
        "aiecs.domain.agent.tool_loop_core.auto_compact_if_needed",
        new=AsyncMock(return_value=([LLMMessage(role="user", content="compact")], True)),
    ) as mock_auto:
        result = await maybe_compact_before_llm(messages, compression_ctx=ctx)

    mock_auto.assert_awaited_once()
    assert mock_auto.await_args.kwargs["session_memory"] is session_memory
    assert mock_auto.await_args.kwargs["hooks"] is hooks
    assert mock_auto.await_args.kwargs["progress"] is progress
    assert result[0].content == "compact"


def test_public_export_truncate_head_for_ptl_retry() -> None:
    from aiecs.domain.context.compression import truncate_head_for_ptl_retry

    assert callable(truncate_head_for_ptl_retry)


@pytest.mark.asyncio
async def test_auto_compact_failure_preserves_partial_chain_work() -> None:
    messages: list[LLMMessage] = []
    for index in range(4):
        messages.extend(_mcp_tool_pair(index))

    token_estimate = estimate_message_tokens(messages)
    policy = CompressionPolicy(
        auto_compact_threshold_tokens=max(500, token_estimate - 500),
        preserve_recent=1,
        chain=("microcompact", "llm"),
    )

    with patch(
        "aiecs.domain.context.compression.orchestrator.compact_conversation",
        new=AsyncMock(side_effect=RuntimeError("llm compact failed")),
    ):
        result, did_compact = await auto_compact_if_needed(
            messages,
            policy=policy,
            state=AutoCompactState(),
            llm_client=AsyncMock(),
            force=True,
        )

    assert did_compact is False
    assert result is not messages
    tool_contents = [m.content for m in result if m.role == "tool"]
    assert TIME_BASED_MC_CLEARED_MESSAGE in tool_contents


@pytest.mark.asyncio
async def test_maybe_compact_runs_a8_for_custom_budget_store() -> None:
    from aiecs.domain.agent.tool_loop_core import (
        ToolLoopCompressionContext,
        maybe_compact_before_llm,
    )

    class _CustomToolBudgetStore:
        def get_replacement(self, tool_call_id: str) -> str | None:
            return None

        def set_replacement(self, tool_call_id: str, preview: str) -> None:
            return None

        def mark_seen(self, tool_call_id: str) -> None:
            return None

        def is_seen(self, tool_call_id: str) -> bool:
            return False

    messages = [LLMMessage(role="user", content="hello")]
    store = _CustomToolBudgetStore()
    ctx = ToolLoopCompressionContext(
        enabled=True,
        policy=CompressionPolicy(enabled=True),
        llm_client=object(),
        auto_compact_state=AutoCompactState(),
        budget_store=store,
    )

    with patch(
        "aiecs.domain.agent.tool_loop_core.enforce_tool_result_budget",
        new=AsyncMock(return_value=messages),
    ) as mock_a8:
        with patch(
            "aiecs.domain.agent.tool_loop_core.auto_compact_if_needed",
            new=AsyncMock(return_value=(messages, False)),
        ):
            await maybe_compact_before_llm(messages, compression_ctx=ctx)

    mock_a8.assert_awaited_once()
    assert mock_a8.await_args.kwargs["budget_store"] is store
