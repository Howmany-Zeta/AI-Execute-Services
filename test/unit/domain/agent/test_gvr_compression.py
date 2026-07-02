"""GVR compression preservation tests (A-10)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiecs.domain.agent import AgentConfiguration, HybridAgent
from aiecs.domain.context.compression.gvr_preserve import is_gvr_protected_tool_content
from aiecs.domain.context.compression.microcompact import microcompact_messages
from aiecs.domain.context.compression.policy import CompressionPolicy
from aiecs.domain.context.compression.state import AutoCompactState
from aiecs.domain.context.compression.tokens import estimate_message_tokens
from aiecs.domain.agent.tool_loop_core import ToolLoopCompressionContext
from aiecs.llm import LLMMessage


def _protected_tool_pair(call_id: str, *, marker: str = "deliverable_refs") -> list[LLMMessage]:
    payload = '{"' + marker + '": ["output.md"], "data": "' + ("X" * 5000) + '"}'
    return [
        LLMMessage(
            role="assistant",
            content=None,
            tool_calls=[
                {
                    "id": call_id,
                    "type": "function",
                    "function": {"name": "read_file__run", "arguments": "{}"},
                }
            ],
        ),
        LLMMessage(role="tool", content=payload, tool_call_id=call_id),
    ]


def _plain_tool_pair(call_id: str) -> list[LLMMessage]:
    return [
        LLMMessage(
            role="assistant",
            content=None,
            tool_calls=[
                {
                    "id": call_id,
                    "type": "function",
                    "function": {"name": "read_file__run", "arguments": "{}"},
                }
            ],
        ),
        LLMMessage(role="tool", content="Y" * 5000, tool_call_id=call_id),
    ]


@pytest.mark.unit
class TestGvrPreserveDetection:
    def test_deliverable_refs_marker(self) -> None:
        assert is_gvr_protected_tool_content('{"deliverable_refs": ["a.md"]}')

    def test_criteria_marker(self) -> None:
        assert is_gvr_protected_tool_content('{"acceptance_criteria": [{"criterion_id": "c1"}]}')

    def test_plain_content_not_protected(self) -> None:
        assert not is_gvr_protected_tool_content("plain tool output")


@pytest.mark.unit
class TestMicrocompactGvrPreservation:
    def test_preserves_deliverable_refs_outside_keep_recent(self) -> None:
        messages: list[LLMMessage] = []
        messages.extend(_protected_tool_pair("prot_0"))
        protected_content = messages[1].content
        for index in range(1, 8):
            messages.extend(_plain_tool_pair(f"plain_{index}"))
        compacted, cleared = microcompact_messages(messages, keep_recent=2)
        assert cleared > 0
        assert any(m.content == protected_content for m in compacted if m.role == "tool")

    def test_preserves_criteria_related_tool_results(self) -> None:
        messages: list[LLMMessage] = []
        for index in range(6):
            messages.extend(_protected_tool_pair(f"crit_{index}", marker="criterion_id"))
        criteria_content = messages[1].content
        compacted, _ = microcompact_messages(messages, keep_recent=1)
        assert any(m.content == criteria_content for m in compacted if m.role == "tool")

    def test_non_protected_results_still_cleared(self) -> None:
        messages: list[LLMMessage] = []
        for index in range(6):
            messages.extend(_plain_tool_pair(f"plain_{index}"))
        compacted, cleared = microcompact_messages(messages, keep_recent=2)
        assert cleared > 0
        from aiecs.domain.context.compression.constants import TIME_BASED_MC_CLEARED_MESSAGE

        assert any(m.content == TIME_BASED_MC_CLEARED_MESSAGE for m in compacted if m.role == "tool")


@pytest.mark.asyncio
async def test_long_fc_loop_token_growth_bounded_with_batch_end_compact() -> None:
    """Long FC loop: repeated batch-end compaction keeps tokens bounded."""
    policy = CompressionPolicy(
        enabled=True,
        auto_compact_threshold_tokens=200,
        chain=("microcompact",),
        preserve_recent=2,
    )
    agent = HybridAgent(
        agent_id="gvr-a10-loop",
        name="GVR A10 Loop",
        config=AgentConfiguration(
            llm_model="m",
            enable_context_compression=True,
            compact_after_tool_batch=True,
            compression_policy=policy,
        ),
        llm_client=MagicMock(),
        tools=[],
    )
    messages: list[LLMMessage] = [LLMMessage(role="user", content="task")]
    compression_ctx = ToolLoopCompressionContext(
        enabled=True,
        policy=policy,
        llm_client=agent.llm_client,
        auto_compact_state=AutoCompactState(),
    )

    peak_tokens = 0
    for batch in range(12):
        messages.extend(_plain_tool_pair(f"batch_{batch}"))
        await agent._maybe_compact_after_tool_batch(
            messages,
            compression_ctx=compression_ctx,
            context={},
        )
        tokens = estimate_message_tokens(messages)
        peak_tokens = max(peak_tokens, tokens)

    final_tokens = estimate_message_tokens(messages)
    assert final_tokens < peak_tokens * 0.85 or final_tokens < 8000
    assert final_tokens < 15000
