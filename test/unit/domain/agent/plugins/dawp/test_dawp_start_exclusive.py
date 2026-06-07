"""
Unit tests for D2-04 — dawp_start sole tool_call per iteration (§4.3.2, D13).

Covers:
- dawp_start + read_file in same turn → dawp_start rejected, not enqueued
- dawp_start alone → accepted (baseline)
- Legacy aliases (dawp_run, dawp_publish_workflow) + other tool → rejected
- The other tool in a multi-call batch executes normally (dawp_start rejection is per-call)
- No DawpPendingRun enqueued when D13 violation detected
- Rejection message contains useful guidance
- DAWP_START_TOOL_SCHEMA description warns about sole-call requirement
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiecs.domain.agent.plugins.builtin.tools.dawp_start_tool import DAWP_START_TOOL_SCHEMA
from aiecs.llm import LLMMessage


# ---------------------------------------------------------------------------
# Helpers: build agent + run _process_tool_calls_batch
# ---------------------------------------------------------------------------


async def _run_multi_tool_batch(
    tool_calls: list[dict[str, Any]],
    *,
    plugin_state: dict[str, Any] | None = None,
) -> tuple[list[LLMMessage], list[dict[str, Any]], Any]:
    """Run _process_tool_calls_batch with multiple tool calls.

    Returns (messages_after, events_emitted, state).
    The mock 'other_tool' always returns 'other_result'.
    The 'dawp_start' handler uses plugin_state (or empty dict).
    """
    from aiecs.domain.agent.hybrid_agent import HybridAgent
    from aiecs.domain.agent.models import AgentConfiguration
    from aiecs.domain.agent.plugins.models import PluginConfig
    from aiecs.domain.agent.tool_loop_core import ToolLoopRunState
    from aiecs.llm import BaseLLMClient, LLMResponse

    config = AgentConfiguration(
        goal="exclusive test",
        llm_model="test-model",
        plugins=[
            PluginConfig(name="memory", enabled=False),
            PluginConfig(name="skill", enabled=False),
        ],
    )

    # Build handler mocks
    dawp_handler = MagicMock()
    dawp_handler.name = "dawp_start"
    dawp_handler.run_async = AsyncMock(
        return_value={
            "status": "accepted",
            "suppress_from_llm": True,
            "workflow_id": "test-wf",
            "workflow_source": "static",
        }
    )

    other_handler = MagicMock()
    other_handler.name = "other_tool"
    other_handler.run_async = AsyncMock(return_value="other_result")

    def _get_tool_side_effect(name: str):
        if name == "dawp_start":
            return dawp_handler
        return other_handler

    class StubLLM(BaseLLMClient):
        def __init__(self):
            super().__init__(provider_name="openai")

        async def generate_text(self, *a, **kw):
            return LLMResponse(content="done", provider="openai", model="t", tokens_used=1)

        async def stream_text(self, *a, **kw):
            yield None

        async def close(self):
            pass

    with patch("aiecs.tools.get_tool", side_effect=_get_tool_side_effect):
        agent = HybridAgent(
            agent_id="excl-test",
            name="Exclusive Test",
            llm_client=StubLLM(),
            tools=["dawp_start", "other_tool"],
            config=config,
            max_iterations=5,
        )
        await agent.initialize()

    # Inject plugin_state into dawp handler if provided
    if plugin_state is not None:
        dawp_tool = agent._tool_instances.get("dawp_start")
        if hasattr(dawp_tool, "bind_plugin_state"):
            dawp_tool.bind_plugin_state(plugin_state)

    state = ToolLoopRunState()
    messages: list[LLMMessage] = [LLMMessage(role="system", content="sys")]
    events: list[dict[str, Any]] = []

    async def _emit(event: dict[str, Any]) -> None:
        events.append(event)

    await agent._process_tool_calls_batch(
        thought_raw="",
        tool_calls_to_process=tool_calls,
        messages=messages,
        iteration=0,
        state=state,
        event_callback=_emit,
    )
    return messages, events, state


def _tc(name: str, call_id: str = "call_1", args: str = "{}") -> dict[str, Any]:
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": args},
    }


# ---------------------------------------------------------------------------
# D13: rejection when dawp_start is not sole tool_call
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDawpStartExclusive:
    @pytest.mark.asyncio
    async def test_dawp_start_alone_accepted(self):
        """Baseline: dawp_start alone in a batch → handler is called (accepted)."""
        state_dict: dict[str, Any] = {"dawp.pending": [], "dawp.workflow": None}
        tool_calls = [_tc("dawp_start", "call_dawp")]
        messages, events, state = await _run_multi_tool_batch(
            tool_calls, plugin_state=state_dict
        )
        # dawp_start was called — tool_result event emitted
        tr_events = [e for e in events if e.get("type") == "tool_result"]
        assert len(tr_events) == 1

    @pytest.mark.asyncio
    async def test_dawp_start_plus_other_tool_rejected(self):
        """dawp_start + other_tool in same iteration → dawp_start gets rejected."""
        state_dict: dict[str, Any] = {"dawp.pending": [], "dawp.workflow": None}
        tool_calls = [
            _tc("dawp_start", "call_dawp"),
            _tc("other_tool", "call_other"),
        ]
        messages, events, state = await _run_multi_tool_batch(
            tool_calls, plugin_state=state_dict
        )
        # Find the tool_result event for dawp_start
        tool_results = [e for e in events if e.get("type") == "tool_result"]
        dawp_result = next(
            (e["result"] for e in tool_results if _is_dawp_result(e)), None
        )
        assert dawp_result is not None, "dawp_start tool_result event must be emitted"
        assert dawp_result.get("status") == "rejected"
        assert "D13" in dawp_result.get("reason", "")

    @pytest.mark.asyncio
    async def test_dawp_start_rejected_not_enqueued(self):
        """D13 violation: no DawpPendingRun must be added to plugin_state."""
        state_dict: dict[str, Any] = {"dawp.pending": [], "dawp.workflow": None}
        tool_calls = [
            _tc("dawp_start", "call_dawp"),
            _tc("other_tool", "call_other"),
        ]
        await _run_multi_tool_batch(tool_calls, plugin_state=state_dict)
        assert state_dict["dawp.pending"] == [], "no run should be enqueued on D13 rejection"

    @pytest.mark.asyncio
    async def test_other_tool_still_executes_on_d13_rejection(self):
        """The companion tool (read_file etc.) must still execute normally."""
        state_dict: dict[str, Any] = {"dawp.pending": [], "dawp.workflow": None}
        tool_calls = [
            _tc("dawp_start", "call_dawp"),
            _tc("other_tool", "call_other"),
        ]
        messages, events, state = await _run_multi_tool_batch(
            tool_calls, plugin_state=state_dict
        )
        # other_tool should still appear in state.steps
        action_tools = [s["tool"] for s in state.steps if s.get("type") == "action"]
        assert "other_tool" in action_tools, "other_tool must execute even when dawp_start is rejected"

    @pytest.mark.asyncio
    async def test_other_tool_first_dawp_second_both_rejected(self):
        """Order shouldn't matter: other_tool first, dawp_start second → still rejected."""
        state_dict: dict[str, Any] = {"dawp.pending": [], "dawp.workflow": None}
        tool_calls = [
            _tc("other_tool", "call_other"),
            _tc("dawp_start", "call_dawp"),
        ]
        messages, events, state = await _run_multi_tool_batch(
            tool_calls, plugin_state=state_dict
        )
        tool_results = [e for e in events if e.get("type") == "tool_result"]
        dawp_result = next(
            (e["result"] for e in tool_results if _is_dawp_result(e)), None
        )
        assert dawp_result is not None
        assert dawp_result.get("status") == "rejected"
        assert state_dict["dawp.pending"] == []

    @pytest.mark.asyncio
    async def test_rejection_reason_contains_guidance(self):
        """The rejection message should guide the model to call dawp_start alone."""
        state_dict: dict[str, Any] = {"dawp.pending": [], "dawp.workflow": None}
        tool_calls = [
            _tc("dawp_start", "call_dawp"),
            _tc("other_tool", "call_other"),
        ]
        messages, events, _ = await _run_multi_tool_batch(
            tool_calls, plugin_state=state_dict
        )
        tool_results = [e for e in events if e.get("type") == "tool_result"]
        dawp_result = next(
            (e["result"] for e in tool_results if _is_dawp_result(e)), None
        )
        assert dawp_result is not None
        reason = dawp_result.get("reason", "")
        assert "sole" in reason.lower() or "alone" in reason.lower(), (
            "Rejection reason should guide model to call dawp_start alone"
        )

    @pytest.mark.asyncio
    async def test_dawp_run_legacy_alias_also_rejected_when_not_sole(self):
        """dawp_run (legacy alias) + other_tool → rejected (D13 applies to all DAWP triggers)."""
        state_dict: dict[str, Any] = {"dawp.pending": [], "dawp.workflow": None}
        tool_calls = [
            _tc("dawp_run", "call_dawp"),
            _tc("other_tool", "call_other"),
        ]
        messages, events, state = await _run_multi_tool_batch(
            tool_calls, plugin_state=state_dict
        )
        tool_results = [e for e in events if e.get("type") == "tool_result"]
        # dawp_run result should be rejected
        dawp_result = next(
            (e["result"] for e in tool_results if _is_dawp_result(e, name="dawp_run")),
            None,
        )
        assert dawp_result is not None, "dawp_run tool_result event must be emitted"
        assert dawp_result.get("status") == "rejected"

    @pytest.mark.asyncio
    async def test_dawp_publish_workflow_legacy_also_rejected(self):
        """dawp_publish_workflow + other_tool → rejected."""
        state_dict: dict[str, Any] = {"dawp.pending": [], "dawp.workflow": None}
        tool_calls = [
            _tc("dawp_publish_workflow", "call_dawp"),
            _tc("other_tool", "call_other"),
        ]
        messages, events, state = await _run_multi_tool_batch(
            tool_calls, plugin_state=state_dict
        )
        tool_results = [e for e in events if e.get("type") == "tool_result"]
        dawp_result = next(
            (e["result"] for e in tool_results if _is_dawp_result(e, name="dawp_publish_workflow")),
            None,
        )
        assert dawp_result is not None
        assert dawp_result.get("status") == "rejected"


# ---------------------------------------------------------------------------
# Schema description contains sole-call warning
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDawpStartSchemaDescription:
    def test_schema_description_warns_about_sole_call(self):
        desc = DAWP_START_TOOL_SCHEMA.get("description", "")
        # Must contain strong guidance
        assert "sole" in desc.lower() or "only" in desc.lower() or "alone" in desc.lower()

    def test_schema_description_mentions_other_tools_constraint(self):
        desc = DAWP_START_TOOL_SCHEMA.get("description", "")
        # Should reference the constraint in some form
        assert "tool" in desc.lower()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _is_dawp_result(event: dict[str, Any], name: str = "dawp_start") -> bool:
    """True if the tool_result event is for the given tool name and result is a dict."""
    result = event.get("result")
    return event.get("tool_name") == name and isinstance(result, dict)
