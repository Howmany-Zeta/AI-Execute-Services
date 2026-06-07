"""
Unit tests for D2-03 — suppress_from_llm paired message removal (§4.3.1).

Covers:
Unit — apply_suppress_from_llm:
- removes the assistant message whose tool_calls contains tool_call_id
- removes the tool message with matching tool_call_id
- removes both as an atomic pair
- does NOT remove unrelated messages
- does NOT mutate the input list
- handles tool_call_id not present (no-op)
- handles assistant message with multiple tool_calls containing the id

Integration — _process_tool_calls_batch (streaming):
- when tool result has suppress_from_llm=True, messages has no orphan tool_calls
- when tool result has suppress_from_llm=True, messages has no matching tool_result
- streaming tool_result event IS still yielded (audit retained)
- state.steps still records the tool result (audit retained)
- when suppress_from_llm is absent/False, messages retain the full pair

CRITICAL: test validates no orphan tool_calls without tool_result → avoids API 400.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from aiecs.domain.agent.plugins.dawp.suppress import (
    _is_suppressed_tool_pair,
    apply_suppress_from_llm,
)
from aiecs.llm import LLMMessage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _asst_with_tool_call(tool_call_id: str, name: str = "dawp_start") -> LLMMessage:
    return LLMMessage(
        role="assistant",
        content=None,
        tool_calls=[
            {
                "id": tool_call_id,
                "type": "function",
                "function": {"name": name, "arguments": "{}"},
            }
        ],
    )


def _tool_result(tool_call_id: str, content: str = "ack") -> LLMMessage:
    return LLMMessage(role="tool", content=content, tool_call_id=tool_call_id)


def _sys(content: str = "system") -> LLMMessage:
    return LLMMessage(role="system", content=content)


def _user(content: str = "query") -> LLMMessage:
    return LLMMessage(role="user", content=content)


# ---------------------------------------------------------------------------
# Unit — _is_suppressed_tool_pair
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestIsSuppressedToolPair:
    def test_tool_role_with_matching_id(self):
        m = _tool_result("call_abc")
        assert _is_suppressed_tool_pair(m, "call_abc") is True

    def test_tool_role_with_different_id(self):
        m = _tool_result("call_abc")
        assert _is_suppressed_tool_pair(m, "call_xyz") is False

    def test_assistant_with_matching_tool_calls_entry(self):
        m = _asst_with_tool_call("call_abc")
        assert _is_suppressed_tool_pair(m, "call_abc") is True

    def test_assistant_with_different_tool_calls_id(self):
        m = _asst_with_tool_call("call_abc")
        assert _is_suppressed_tool_pair(m, "call_xyz") is False

    def test_system_message_never_matches(self):
        m = _sys("instructions")
        assert _is_suppressed_tool_pair(m, "call_abc") is False

    def test_user_message_never_matches(self):
        m = _user("hello")
        assert _is_suppressed_tool_pair(m, "call_abc") is False

    def test_assistant_with_no_tool_calls_not_matched(self):
        m = LLMMessage(role="assistant", content="just text")
        assert _is_suppressed_tool_pair(m, "call_abc") is False


# ---------------------------------------------------------------------------
# Unit — apply_suppress_from_llm
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestApplySuppressFromLlm:
    def test_removes_assistant_message_with_matching_id(self):
        messages = [
            _sys(),
            _user(),
            _asst_with_tool_call("call_42"),
            _tool_result("call_42"),
        ]
        result = apply_suppress_from_llm(messages, "call_42")
        roles = [m.role for m in result]
        assert "assistant" not in roles

    def test_removes_tool_result_with_matching_id(self):
        messages = [
            _sys(),
            _user(),
            _asst_with_tool_call("call_42"),
            _tool_result("call_42"),
        ]
        result = apply_suppress_from_llm(messages, "call_42")
        tool_msgs = [m for m in result if m.role == "tool"]
        assert tool_msgs == []

    def test_removes_both_as_atomic_pair(self):
        messages = [
            _sys("sys"),
            _user("q"),
            _asst_with_tool_call("call_dawp"),
            _tool_result("call_dawp", "accepted"),
        ]
        result = apply_suppress_from_llm(messages, "call_dawp")
        assert len(result) == 2
        assert result[0].role == "system"
        assert result[1].role == "user"

    def test_retains_unrelated_messages(self):
        messages = [
            _sys("keep-me"),
            _user("keep-me-too"),
            _asst_with_tool_call("call_dawp"),
            _tool_result("call_dawp"),
            _asst_with_tool_call("call_other"),
            _tool_result("call_other", "other result"),
        ]
        result = apply_suppress_from_llm(messages, "call_dawp")
        # system + user + unrelated pair = 4 messages
        assert len(result) == 4
        assert any(m.role == "system" for m in result)
        assert any(m.role == "user" for m in result)
        # The other tool pair is retained
        other_tool = [m for m in result if m.role == "tool"]
        assert len(other_tool) == 1
        assert other_tool[0].tool_call_id == "call_other"

    def test_does_not_mutate_original_list(self):
        messages = [
            _asst_with_tool_call("call_42"),
            _tool_result("call_42"),
        ]
        original_ids = [id(m) for m in messages]
        apply_suppress_from_llm(messages, "call_42")
        # Original list still has both messages
        assert len(messages) == 2
        assert [id(m) for m in messages] == original_ids

    def test_no_op_when_id_not_found(self):
        messages = [_sys(), _user()]
        result = apply_suppress_from_llm(messages, "call_missing")
        assert len(result) == 2

    def test_empty_messages_list(self):
        result = apply_suppress_from_llm([], "call_abc")
        assert result == []

    def test_no_orphan_tool_calls_after_suppress(self):
        """Validate API safety: after suppress, no assistant tool_calls without a matching tool result."""
        messages = [
            _sys(),
            _user(),
            _asst_with_tool_call("call_dawp"),
            _tool_result("call_dawp"),
        ]
        result = apply_suppress_from_llm(messages, "call_dawp")

        # Collect all tool_call ids referenced in assistant messages
        referenced_ids: set[str] = set()
        for m in result:
            if m.role == "assistant" and m.tool_calls:
                for tc in m.tool_calls:
                    referenced_ids.add(tc["id"])

        # Collect all tool_call_ids in tool messages
        responded_ids: set[str] = {
            m.tool_call_id for m in result if m.role == "tool" and m.tool_call_id
        }

        # Every referenced id must have a matching tool result (no orphans)
        assert referenced_ids.issubset(responded_ids), (
            f"Orphan tool_calls detected: {referenced_ids - responded_ids}"
        )


# ---------------------------------------------------------------------------
# Integration — _process_tool_calls_batch
# ---------------------------------------------------------------------------


async def _run_tool_batch(
    tool_result_value: Any,
    *,
    tool_call_id: str = "call_dawp_1",
    prior_messages: list[LLMMessage] | None = None,
) -> tuple[list[LLMMessage], list[dict[str, Any]], Any]:
    """Run _process_tool_calls_batch with a mock tool returning tool_result_value.

    Returns (messages_after, events_collected, state).
    """
    from aiecs.domain.agent.hybrid_agent import HybridAgent
    from aiecs.domain.agent.models import AgentConfiguration
    from aiecs.domain.agent.plugins.models import PluginConfig
    from aiecs.domain.agent.tool_loop_core import ToolLoopRunState
    from unittest.mock import patch

    config = AgentConfiguration(
        goal="suppress test",
        llm_model="test-model",
        plugins=[
            PluginConfig(name="memory", enabled=False),
            PluginConfig(name="skill", enabled=False),
        ],
    )

    mock_tool = MagicMock()
    mock_tool.name = "dawp_start"
    mock_tool.description = "dawp tool"
    mock_tool._schemas = {}
    mock_tool.run_async = AsyncMock(return_value=tool_result_value)

    from aiecs.llm import BaseLLMClient, LLMResponse

    class StubLLM(BaseLLMClient):
        def __init__(self):
            super().__init__(provider_name="openai")

        async def generate_text(self, *a, **kw):
            return LLMResponse(content="done", provider="openai", model="t", tokens_used=1)

        async def stream_text(self, *a, **kw):
            yield None  # won't be called in this test path

        async def close(self):
            pass

    with patch("aiecs.tools.get_tool", return_value=mock_tool):
        agent = HybridAgent(
            agent_id="suppress-test",
            name="Suppress Test",
            llm_client=StubLLM(),
            tools=["dawp_start"],
            config=config,
            max_iterations=5,
        )
        await agent.initialize()

    state = ToolLoopRunState()
    messages = list(prior_messages or [_sys("system"), _user("query")])
    events: list[dict[str, Any]] = []

    async def _emit(event: dict[str, Any]) -> None:
        events.append(event)

    tool_calls = [
        {
            "id": tool_call_id,
            "type": "function",
            "function": {"name": "dawp_start", "arguments": '{"workflow_source":"static"}'},
        }
    ]
    await agent._process_tool_calls_batch(
        thought_raw="",
        tool_calls_to_process=tool_calls,
        messages=messages,
        iteration=0,
        state=state,
        event_callback=_emit,
    )
    return messages, events, state


@pytest.mark.unit
class TestSuppressInToolCallsBatch:
    @pytest.mark.asyncio
    async def test_suppress_removes_assistant_tool_calls_from_messages(self):
        tool_result_val = {"status": "accepted", "suppress_from_llm": True}
        messages, _, _ = await _run_tool_batch(tool_result_val)

        assistant_msgs = [m for m in messages if m.role == "assistant"]
        assert assistant_msgs == [], "assistant message with tool_calls must be suppressed"

    @pytest.mark.asyncio
    async def test_suppress_removes_tool_result_from_messages(self):
        tool_result_val = {"status": "accepted", "suppress_from_llm": True}
        messages, _, _ = await _run_tool_batch(tool_result_val)

        tool_msgs = [m for m in messages if m.role == "tool"]
        assert tool_msgs == [], "tool result message must be suppressed"

    @pytest.mark.asyncio
    async def test_suppress_no_orphan_tool_calls(self):
        """CRITICAL: after suppress, messages must have no assistant tool_calls without a result."""
        tool_result_val = {"status": "accepted", "suppress_from_llm": True}
        messages, _, _ = await _run_tool_batch(tool_result_val)

        referenced: set[str] = set()
        for m in messages:
            if m.role == "assistant" and m.tool_calls:
                for tc in m.tool_calls:
                    referenced.add(tc["id"])

        responded: set[str] = {
            m.tool_call_id for m in messages if m.role == "tool" and m.tool_call_id
        }
        assert referenced.issubset(responded), (
            f"Orphan tool_calls detected — API would return 400: {referenced - responded}"
        )

    @pytest.mark.asyncio
    async def test_streaming_tool_result_event_still_yielded(self):
        """Streaming audit: tool_result event must still be emitted even when suppressed."""
        tool_result_val = {"status": "accepted", "suppress_from_llm": True}
        _, events, _ = await _run_tool_batch(tool_result_val)

        tool_result_events = [e for e in events if e.get("type") == "tool_result"]
        assert len(tool_result_events) == 1, "tool_result event must be yielded for audit"

    @pytest.mark.asyncio
    async def test_state_steps_still_records_tool_result(self):
        """Audit: state.steps must retain the action step even when suppressed."""
        tool_result_val = {"status": "accepted", "suppress_from_llm": True}
        _, _, state = await _run_tool_batch(tool_result_val)

        action_steps = [s for s in state.steps if s.get("type") == "action"]
        assert len(action_steps) == 1, "state.steps must retain tool action for audit"

    @pytest.mark.asyncio
    async def test_no_suppress_when_flag_absent(self):
        """When suppress_from_llm is not in the result, messages retain the full pair."""
        tool_result_val = {"status": "accepted"}
        messages, _, _ = await _run_tool_batch(tool_result_val)

        assistant_msgs = [m for m in messages if m.role == "assistant"]
        tool_msgs = [m for m in messages if m.role == "tool"]
        assert len(assistant_msgs) == 1, "assistant message retained when no suppress"
        assert len(tool_msgs) == 1, "tool result retained when no suppress"

    @pytest.mark.asyncio
    async def test_no_suppress_when_flag_false(self):
        tool_result_val = {"status": "accepted", "suppress_from_llm": False}
        messages, _, _ = await _run_tool_batch(tool_result_val)

        assert any(m.role == "assistant" for m in messages)
        assert any(m.role == "tool" for m in messages)

    @pytest.mark.asyncio
    async def test_prior_messages_retained_after_suppress(self):
        prior = [_sys("keep-sys"), _user("keep-user")]
        tool_result_val = {"status": "accepted", "suppress_from_llm": True}
        messages, _, _ = await _run_tool_batch(tool_result_val, prior_messages=prior)

        assert messages[0].role == "system"
        assert messages[0].content == "keep-sys"
        assert messages[1].role == "user"
        assert messages[1].content == "keep-user"
        assert len(messages) == 2  # only the 2 prior messages remain
