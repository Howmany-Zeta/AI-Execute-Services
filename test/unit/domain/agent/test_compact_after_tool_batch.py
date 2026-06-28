"""G1 F4 turnkey batch-end compaction tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiecs.domain.agent import AgentConfiguration, HybridAgent
from aiecs.domain.agent.plugins.context import AgentPluginContext
from aiecs.domain.agent.tool_loop_core import ToolLoopCompressionContext, ToolLoopRunState
from aiecs.domain.context.compression.constants import TIME_BASED_MC_CLEARED_MESSAGE
from aiecs.domain.context.compression.orchestrator import auto_compact_if_needed
from aiecs.domain.context.compression.policy import CompressionPolicy
from aiecs.domain.context.compression.state import AutoCompactState
from aiecs.domain.context.compression.tokens import estimate_message_tokens
from aiecs.llm import LLMMessage


def _tool_pair(call_id: str, *, payload_chars: int = 5_000) -> list[LLMMessage]:
    return [
        LLMMessage(
            role="assistant",
            content=None,
            tool_calls=[
                {
                    "id": call_id,
                    "type": "function",
                    "function": {
                        "name": "mock_tool__run",
                        "arguments": "{}",
                    },
                }
            ],
        ),
        LLMMessage(
            role="tool",
            content="X" * payload_chars,
            tool_call_id=call_id,
        ),
    ]


def _tool_history(*, pairs: int, payload_chars: int = 5_000) -> list[LLMMessage]:
    messages: list[LLMMessage] = []
    for index in range(pairs):
        messages.extend(_tool_pair(f"call_{index}", payload_chars=payload_chars))
    return messages


def _g1_agent(**config_overrides) -> HybridAgent:
    defaults = {
        "llm_model": "m",
        "enable_context_compression": True,
        "compact_after_tool_batch": True,
        "compression_policy": CompressionPolicy(
            enabled=True,
            auto_compact_threshold_tokens=100,
            chain=("microcompact",),
            preserve_recent=2,
        ),
    }
    defaults.update(config_overrides)
    config = AgentConfiguration(**defaults)
    return HybridAgent(
        agent_id="g1-integration",
        name="G1 Integration",
        config=config,
        llm_client=MagicMock(),
        tools=[],
    )


@pytest.mark.asyncio
async def test_batch_end_compacts_via_real_orchestrator_and_should_compress() -> None:
    """Integration: batch-end runs should_compress gate + real auto_compact_if_needed."""
    agent = _g1_agent()
    messages = _tool_history(pairs=6)
    pre_tokens = estimate_message_tokens(messages)
    compression_ctx = ToolLoopCompressionContext(
        enabled=True,
        policy=CompressionPolicy(
            enabled=True,
            auto_compact_threshold_tokens=100,
            chain=("microcompact",),
            preserve_recent=2,
        ),
        llm_client=agent.llm_client,
        auto_compact_state=AutoCompactState(),
    )

    await agent._maybe_compact_after_tool_batch(
        messages,
        compression_ctx=compression_ctx,
        context={},
    )

    assert estimate_message_tokens(messages) < pre_tokens
    cleared = [
        message
        for message in messages
        if message.role == "tool" and message.content == TIME_BASED_MC_CLEARED_MESSAGE
    ]
    assert cleared


@pytest.mark.asyncio
async def test_batch_end_skips_real_orchestrator_when_under_should_compress_threshold() -> None:
    agent = _g1_agent()
    messages = [LLMMessage(role="user", content="short")]
    compression_ctx = ToolLoopCompressionContext(
        enabled=True,
        policy=CompressionPolicy(
            enabled=True,
            auto_compact_threshold_tokens=1_000_000,
            chain=("microcompact",),
        ),
        llm_client=agent.llm_client,
        auto_compact_state=AutoCompactState(),
    )

    with patch(
        "aiecs.domain.agent.tool_loop_core.auto_compact_if_needed",
        new=AsyncMock(),
    ) as mock_auto_compact:
        await agent._maybe_compact_after_tool_batch(
            messages,
            compression_ctx=compression_ctx,
            context={},
        )

    mock_auto_compact.assert_not_awaited()
    assert messages[0].content == "short"


@pytest.mark.asyncio
async def test_pre_llm_and_batch_end_at_most_one_real_auto_compact() -> None:
    """Debounce integration: real orchestrator runs at most once per iteration."""
    policy = CompressionPolicy(
        enabled=True,
        auto_compact_threshold_tokens=4_000,
        chain=("microcompact",),
        preserve_recent=2,
    )
    agent = _g1_agent(compression_policy=policy)
    shared_state = AutoCompactState()
    agent._auto_compact_state = shared_state
    messages = _tool_history(pairs=6)
    compression_ctx = ToolLoopCompressionContext(
        enabled=True,
        policy=policy,
        llm_client=agent.llm_client,
        auto_compact_state=shared_state,
    )
    auto_compact_calls = 0

    async def counting_auto_compact(*args, **kwargs):
        nonlocal auto_compact_calls
        auto_compact_calls += 1
        return await auto_compact_if_needed(*args, **kwargs)

    with patch(
        "aiecs.domain.agent.tool_loop_core.auto_compact_if_needed",
        side_effect=counting_auto_compact,
    ):
        await agent._apply_pre_llm_compression(messages, {}, plugin_ctx=None)
        await agent._maybe_compact_after_tool_batch(
            messages,
            compression_ctx=compression_ctx,
            context={},
        )

    assert auto_compact_calls == 1
    assert compression_ctx.auto_compact_state.proactive_compact_used_this_iteration is True


@pytest.mark.asyncio
async def test_process_tool_calls_batch_compacts_via_real_path_after_large_tool_output() -> None:
    """Integration: batch end after _process_tool_calls_batch uses real compression path."""
    policy = CompressionPolicy(
        enabled=True,
        auto_compact_threshold_tokens=100,
        chain=("microcompact",),
        preserve_recent=2,
    )
    agent = HybridAgent(
        agent_id="g1-batch-integration",
        name="G1 Batch Integration",
        config=AgentConfiguration(
            llm_model="m",
            enable_context_compression=True,
            compact_after_tool_batch=True,
            compression_policy=policy,
        ),
        llm_client=MagicMock(),
        tools=[],
    )
    agent._plugin_manager = MagicMock()
    agent._plugin_manager.run_phase = AsyncMock()
    messages = _tool_history(pairs=5)
    pre_tokens = estimate_message_tokens(messages)
    compression_ctx = ToolLoopCompressionContext(
        enabled=True,
        policy=policy,
        llm_client=agent.llm_client,
        auto_compact_state=AutoCompactState(),
    )

    with patch.object(agent, "_execute_tool", new=AsyncMock(return_value={"ok": True})):
        with patch(
            "aiecs.domain.agent.hybrid_agent.apply_tool_output_management",
            new=AsyncMock(return_value="Y" * 5_000),
        ):
            plugin_ctx = AgentPluginContext(
                agent=agent,
                task={"description": "test"},
                context={},
                task_description="test",
            )
            await agent._process_tool_calls_batch(
                thought_raw="thought",
                tool_calls_to_process=[
                    {
                        "id": "call_new",
                        "type": "function",
                        "function": {"name": "mock_tool__run", "arguments": "{}"},
                    }
                ],
                messages=messages,
                iteration=0,
                state=ToolLoopRunState(),
                compression_ctx=compression_ctx,
                plugin_ctx=plugin_ctx,
                context={},
            )

    agent._plugin_manager.run_phase.assert_awaited_once()
    assert estimate_message_tokens(messages) < pre_tokens
    assert any(
        message.role == "tool" and message.content == TIME_BASED_MC_CLEARED_MESSAGE
        for message in messages
    )


@pytest.mark.asyncio
async def test_batch_end_compact_when_config_on_and_over_threshold() -> None:
    agent = HybridAgent(
        agent_id="g1-on",
        name="G1 On",
        config=AgentConfiguration(
            llm_model="m",
            enable_context_compression=True,
            compact_after_tool_batch=True,
            compression_policy=CompressionPolicy(
                enabled=True,
                auto_compact_threshold_tokens=10,
                chain=("microcompact",),
            ),
        ),
        llm_client=MagicMock(),
        tools=[],
    )
    messages = [LLMMessage(role="user", content="x" * 5000)]
    compression_ctx = ToolLoopCompressionContext(
        enabled=True,
        policy=CompressionPolicy(enabled=True, auto_compact_threshold_tokens=10, chain=("microcompact",)),
        auto_compact_state=AutoCompactState(),
    )

    with patch(
        "aiecs.domain.agent.hybrid_agent.maybe_compact_before_llm",
        new=AsyncMock(return_value=[LLMMessage(role="user", content="compact")]),
    ) as mock_compact:
        await agent._maybe_compact_after_tool_batch(
            messages,
            compression_ctx=compression_ctx,
            context={},
        )

    mock_compact.assert_awaited_once()
    assert messages[0].content == "compact"


@pytest.mark.asyncio
async def test_batch_end_compact_skipped_when_config_off() -> None:
    agent = HybridAgent(
        agent_id="g1-off",
        name="G1 Off",
        config=AgentConfiguration(
            llm_model="m",
            compact_after_tool_batch=False,
        ),
        llm_client=MagicMock(),
        tools=[],
    )
    messages = [LLMMessage(role="user", content="x" * 5000)]
    compression_ctx = ToolLoopCompressionContext(enabled=True)

    with patch(
        "aiecs.domain.agent.hybrid_agent.maybe_compact_before_llm",
        new=AsyncMock(),
    ) as mock_compact:
        await agent._maybe_compact_after_tool_batch(
            messages,
            compression_ctx=compression_ctx,
            context={},
        )

    mock_compact.assert_not_awaited()


@pytest.mark.asyncio
async def test_batch_end_respects_min_tokens_gate() -> None:
    agent = HybridAgent(
        agent_id="g1-min",
        name="G1 Min",
        config=AgentConfiguration(
            llm_model="m",
            compact_after_tool_batch=True,
            compact_after_tool_batch_min_tokens=10_000,
            compression_policy=CompressionPolicy(enabled=True, auto_compact_threshold_tokens=1),
        ),
        llm_client=MagicMock(),
        tools=[],
    )
    messages = [LLMMessage(role="user", content="short")]
    compression_ctx = ToolLoopCompressionContext(
        enabled=True,
        policy=CompressionPolicy(enabled=True, auto_compact_threshold_tokens=1),
        auto_compact_state=AutoCompactState(),
    )

    with patch(
        "aiecs.domain.agent.hybrid_agent.maybe_compact_before_llm",
        new=AsyncMock(),
    ) as mock_compact:
        await agent._maybe_compact_after_tool_batch(
            messages,
            compression_ctx=compression_ctx,
            context={},
        )

    mock_compact.assert_not_awaited()


@pytest.mark.asyncio
async def test_pre_llm_and_batch_end_at_most_one_effective_compact() -> None:
    """Debounce: after pre-LLM compact shrinks messages, batch-end skips second compact."""
    policy = CompressionPolicy(
        enabled=True,
        auto_compact_threshold_tokens=100,
        chain=("microcompact",),
        context_window_tokens=200,
        buffer_tokens=0,
    )
    agent = HybridAgent(
        agent_id="g1-debounce",
        name="G1 Debounce",
        config=AgentConfiguration(
            llm_model="m",
            enable_context_compression=True,
            compact_after_tool_batch=True,
            compression_policy=policy,
        ),
        llm_client=MagicMock(),
        tools=[],
    )
    shared_state = AutoCompactState()
    messages = [LLMMessage(role="user", content="word " * 200)]
    compression_ctx = ToolLoopCompressionContext(
        enabled=True,
        policy=policy,
        auto_compact_state=shared_state,
    )
    compact_invocations = 0

    async def fake_maybe_compact(msgs, *, compression_ctx, plugin_ctx=None):
        nonlocal compact_invocations
        compact_invocations += 1
        compacted = [LLMMessage(role="user", content="tiny")]
        msgs[:] = compacted
        if compression_ctx.auto_compact_state is not None:
            compression_ctx.auto_compact_state.proactive_compact_used_this_iteration = True
        return compacted

    with patch(
        "aiecs.domain.agent.hybrid_agent.maybe_compact_before_llm",
        side_effect=fake_maybe_compact,
    ):
        await agent._apply_pre_llm_compression(messages, {}, plugin_ctx=None)
        await agent._maybe_compact_after_tool_batch(
            messages,
            compression_ctx=compression_ctx,
            context={},
        )

    assert compact_invocations == 1
    assert messages[0].content == "tiny"


@pytest.mark.asyncio
async def test_batch_end_skipped_when_pre_llm_already_compacted_this_iteration() -> None:
    """Debounce: one effective proactive compact per iteration, even if still over threshold."""
    policy = CompressionPolicy(
        enabled=True,
        auto_compact_threshold_tokens=10,
        chain=("microcompact",),
    )
    agent = HybridAgent(
        agent_id="g1-debounce-over",
        name="G1 Debounce Over",
        config=AgentConfiguration(
            llm_model="m",
            enable_context_compression=True,
            compact_after_tool_batch=True,
            compression_policy=policy,
        ),
        llm_client=MagicMock(),
        tools=[],
    )
    shared_state = AutoCompactState(proactive_compact_used_this_iteration=True)
    messages = [LLMMessage(role="user", content="word " * 500)]
    compression_ctx = ToolLoopCompressionContext(
        enabled=True,
        policy=policy,
        auto_compact_state=shared_state,
    )

    with patch(
        "aiecs.domain.agent.hybrid_agent.maybe_compact_before_llm",
        new=AsyncMock(),
    ) as mock_compact:
        await agent._maybe_compact_after_tool_batch(
            messages,
            compression_ctx=compression_ctx,
            context={},
        )

    mock_compact.assert_not_awaited()


@pytest.mark.asyncio
async def test_new_iteration_resets_debounce_and_allows_batch_end_compact() -> None:
    """Each iteration clears proactive_compact_used_this_iteration at pre-LLM start."""
    policy = CompressionPolicy(
        enabled=True,
        auto_compact_threshold_tokens=10,
        chain=("microcompact",),
    )
    agent = HybridAgent(
        agent_id="g1-iter-reset",
        name="G1 Iter Reset",
        config=AgentConfiguration(
            llm_model="m",
            enable_context_compression=True,
            compact_after_tool_batch=True,
            compression_policy=policy,
        ),
        llm_client=MagicMock(),
        tools=[],
    )
    agent._auto_compact_state = AutoCompactState(proactive_compact_used_this_iteration=True)
    messages = [LLMMessage(role="user", content="word " * 500)]

    with patch(
        "aiecs.domain.agent.hybrid_agent.maybe_compact_before_llm",
        new=AsyncMock(return_value=messages),
    ) as mock_compact:
        await agent._apply_pre_llm_compression(messages, {}, plugin_ctx=None)

    assert agent._auto_compact_state.proactive_compact_used_this_iteration is False
    mock_compact.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_tool_calls_batch_runs_builtin_after_plugin_phase() -> None:
    agent = HybridAgent(
        agent_id="g1-batch",
        name="G1 Batch",
        config=AgentConfiguration(
            llm_model="m",
            compact_after_tool_batch=True,
            compression_policy=CompressionPolicy(enabled=True, auto_compact_threshold_tokens=1),
        ),
        llm_client=MagicMock(),
        tools=[],
    )
    agent._plugin_manager = MagicMock()
    agent._plugin_manager.run_phase = AsyncMock()
    messages: list[LLMMessage] = []
    compression_ctx = ToolLoopCompressionContext(
        enabled=True,
        policy=CompressionPolicy(enabled=True, auto_compact_threshold_tokens=1),
        auto_compact_state=AutoCompactState(),
    )

    with patch.object(agent, "_execute_tool", new=AsyncMock(return_value={"ok": True})):
        with patch(
            "aiecs.domain.agent.hybrid_agent.apply_tool_output_management",
            new=AsyncMock(return_value='{"ok": true}'),
        ):
            with patch.object(agent, "_maybe_compact_after_tool_batch", new=AsyncMock()) as mock_batch_compact:
                plugin_ctx = AgentPluginContext(
                    agent=agent,
                    task={"description": "test"},
                    context={},
                    task_description="test",
                )
                await agent._process_tool_calls_batch(
                    thought_raw="thought",
                    tool_calls_to_process=[
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {"name": "mock_tool__query", "arguments": "{}"},
                        }
                    ],
                    messages=messages,
                    iteration=0,
                    state=ToolLoopRunState(),
                    compression_ctx=compression_ctx,
                    plugin_ctx=plugin_ctx,
                    context={},
                )

    agent._plugin_manager.run_phase.assert_awaited_once()
    mock_batch_compact.assert_awaited_once()
