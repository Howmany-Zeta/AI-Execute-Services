"""
Unit tests for D1-12 — merge_back append vs inject_only (§6.3).

Tests:
- inject.messages_for_dawp_run:
    - append  → returns same object (by reference)
    - inject_only → returns a copy (new list, equal content)
- inject.apply_inject_only:
    - appends summary assistant message with correct content
    - workflow_id embedded in summary
- DawpPendingRun.merge_back field (schema):
    - default is "append"
    - accepts "inject_only"
- run_scheduler propagates merge_back from Activation:
    - pre_main_loop activation with merge_back=inject_only → pending run has merge_back=inject_only
    - default (append) activation → pending run has merge_back=append
- Integration (_drain_pending_dawp_runs):
    - append: all DAWP messages end up in main messages
    - inject_only: DAWP messages do NOT appear in main messages; only summary does
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiecs.domain.agent.plugins.dawp.inject import (
    _INJECT_ONLY_SUMMARY,
    apply_inject_only,
    messages_for_dawp_run,
)
from aiecs.domain.agent.plugins.dawp.schema import (
    Activation,
    DawpPendingRun,
    OnResponseTriggerPlacement,
    PreMainLoopPlacement,
)
from aiecs.llm import LLMMessage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sys(content: str) -> LLMMessage:
    return LLMMessage(role="system", content=content)


def _asst(content: str) -> LLMMessage:
    return LLMMessage(role="assistant", content=content)


def _user(content: str) -> LLMMessage:
    return LLMMessage(role="user", content=content)


def _pending_run(
    merge_back: str = "append",
    workflow_id: str = "wf-test",
) -> DawpPendingRun:
    return DawpPendingRun(
        trigger="config",
        workflow_source="static",
        workflow_id=workflow_id,
        enqueued_at_iteration=0,
        drain_mode="on_iteration_end",
        merge_back=merge_back,
    )


# ---------------------------------------------------------------------------
# inject.messages_for_dawp_run
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMessagesForDawpRun:
    def test_append_returns_same_object(self) -> None:
        """append mode: returns main_messages by reference."""
        msgs = [_sys("system")]
        result = messages_for_dawp_run(msgs, merge_back="append")
        assert result is msgs

    def test_inject_only_returns_copy(self) -> None:
        """inject_only mode: returns a new list (not same object)."""
        msgs = [_sys("system"), _user("hello")]
        result = messages_for_dawp_run(msgs, merge_back="inject_only")
        assert result is not msgs

    def test_inject_only_copy_has_same_content(self) -> None:
        """inject_only copy contains all original messages."""
        msgs = [_sys("system"), _user("hello")]
        result = messages_for_dawp_run(msgs, merge_back="inject_only")
        assert result == msgs

    def test_inject_only_mutation_does_not_affect_original(self) -> None:
        """Appending to the copy must not affect main_messages."""
        msgs = [_sys("system")]
        copy = messages_for_dawp_run(msgs, merge_back="inject_only")
        copy.append(_asst("dawp output"))
        assert len(msgs) == 1  # original unchanged

    def test_append_mutation_is_visible_on_original(self) -> None:
        """Appending to the append-mode return value is visible on main_messages."""
        msgs = [_sys("system")]
        ref = messages_for_dawp_run(msgs, merge_back="append")
        ref.append(_asst("dawp output"))
        assert len(msgs) == 2  # same object — change reflected


# ---------------------------------------------------------------------------
# inject.apply_inject_only
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestApplyInjectOnly:
    def test_appends_assistant_message(self) -> None:
        """apply_inject_only appends one assistant message."""
        msgs: list[LLMMessage] = []
        apply_inject_only(msgs, workflow_id="my-workflow")
        assert len(msgs) == 1
        assert msgs[0].role == "assistant"

    def test_summary_contains_workflow_id(self) -> None:
        """Summary text includes the workflow_id."""
        msgs: list[LLMMessage] = []
        apply_inject_only(msgs, workflow_id="ooda-review")
        assert "ooda-review" in msgs[0].content

    def test_summary_format(self) -> None:
        """Summary matches the _INJECT_ONLY_SUMMARY template."""
        msgs: list[LLMMessage] = []
        apply_inject_only(msgs, workflow_id="my-wf")
        expected = _INJECT_ONLY_SUMMARY.format(workflow_id="my-wf")
        assert msgs[0].content == expected

    def test_appends_after_existing_messages(self) -> None:
        """Summary is appended at the end of the existing messages list."""
        existing = [_sys("system"), _asst("previous")]
        apply_inject_only(existing, workflow_id="wf")
        assert len(existing) == 3
        assert existing[-1].role == "assistant"

    def test_mutates_in_place(self) -> None:
        """apply_inject_only mutates the list in-place."""
        msgs: list[LLMMessage] = []
        original_id = id(msgs)
        apply_inject_only(msgs, workflow_id="wf")
        assert id(msgs) == original_id


# ---------------------------------------------------------------------------
# DawpPendingRun.merge_back schema field
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDawpPendingRunMergeBack:
    def test_default_merge_back_is_append(self) -> None:
        """DawpPendingRun.merge_back defaults to 'append'."""
        run = DawpPendingRun(
            trigger="config",
            workflow_source="static",
            workflow_id="wf",
            enqueued_at_iteration=0,
            drain_mode="on_iteration_end",
        )
        assert run.merge_back == "append"

    def test_merge_back_inject_only_accepted(self) -> None:
        run = _pending_run(merge_back="inject_only")
        assert run.merge_back == "inject_only"

    def test_merge_back_append_accepted(self) -> None:
        run = _pending_run(merge_back="append")
        assert run.merge_back == "append"


# ---------------------------------------------------------------------------
# run_scheduler propagates merge_back from Activation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSchedulerPropagatesMergeBack:
    def _schedule(self, activation: Activation) -> DawpPendingRun:
        from aiecs.domain.agent.plugins.dawp.run_scheduler import schedule_at_checkpoint

        plugin_state: dict[str, Any] = {}
        runs = schedule_at_checkpoint(
            [("wf-test", activation)],
            phase="pre_main_loop",
            plugin_state=plugin_state,
        )
        assert len(runs) == 1
        return runs[0]

    def test_pre_main_loop_default_merge_back_is_append(self) -> None:
        activation = Activation(placement=PreMainLoopPlacement())
        run = self._schedule(activation)
        assert run.merge_back == "append"

    def test_pre_main_loop_inject_only_propagated(self) -> None:
        activation = Activation(
            placement=PreMainLoopPlacement(), merge_back="inject_only"
        )
        run = self._schedule(activation)
        assert run.merge_back == "inject_only"

    def test_on_response_trigger_merge_back_propagated(self) -> None:
        from aiecs.domain.agent.plugins.dawp.run_scheduler import schedule_at_checkpoint

        activation = Activation(
            placement=OnResponseTriggerPlacement(dawp_trigger="<START_WF>"),
            merge_back="inject_only",
        )
        plugin_state: dict[str, Any] = {}
        runs = schedule_at_checkpoint(
            [("wf-test", activation)],
            phase="on_iteration_end",
            plugin_state=plugin_state,
            assistant_text="<START_WF>",
        )
        assert len(runs) == 1
        assert runs[0].merge_back == "inject_only"


# ---------------------------------------------------------------------------
# Integration: _drain_pending_dawp_runs merge_back behavior
# ---------------------------------------------------------------------------


async def _collect(gen) -> list[dict[str, Any]]:
    return [e async for e in gen]


def _make_drain_agent(
    llm_responses: list[str],
    pending_run: DawpPendingRun,
    workflow_name: str = "wf-test",
) -> tuple[Any, Any, list[LLMMessage]]:
    """Build a minimal HybridAgent configured for drain testing."""
    from pathlib import Path

    from aiecs.domain.agent.hybrid_agent import HybridAgent
    from aiecs.domain.agent.models import AgentConfiguration
    from aiecs.domain.agent.plugins.context import AgentPluginContext
    from aiecs.domain.agent.plugins.dawp.budget import TaskIterationBudget
    from aiecs.domain.agent.plugins.dawp.schema import DAWPStep, DAWPWorkflow, MarkerCompletion, WorkflowMetadata, WorkflowSpec, Contract
    from aiecs.domain.agent.plugins.models import PluginConfig
    from aiecs.llm import BaseLLMClient, LLMResponse

    PROMPT_MARKER = "<STEP_DONE>"
    DAWP_MARKER = "<DAWP_DONE>"

    class MockLLM(BaseLLMClient):
        def __init__(self) -> None:
            super().__init__(provider_name="openai")
            self._idx = 0

        async def generate_text(self, messages, **kwargs):
            content = llm_responses[min(self._idx, len(llm_responses) - 1)]
            self._idx += 1
            return LLMResponse(content=content, provider="openai", model="t", tokens_used=1)

        async def stream_text(self, *args, **kwargs):
            from aiecs.llm.clients.openai_compatible_mixin import StreamChunk
            content = llm_responses[min(self._idx, len(llm_responses) - 1)]
            self._idx += 1
            yield StreamChunk(type="token", content=content)

        async def close(self): pass

    mock_tool = MagicMock()
    mock_tool.name = "mock_tool"
    mock_tool.description = "mock"
    mock_tool._schemas = {}
    mock_tool.run_async = AsyncMock(return_value="ok")

    with patch("aiecs.tools.get_tool", return_value=mock_tool):
        agent = HybridAgent(
            agent_id="drain-test",
            name="Drain Test",
            llm_client=MockLLM(),
            tools=["mock_tool"],
            config=AgentConfiguration(
                goal="drain test",
                llm_model="test",
                plugins=[PluginConfig(name="dawp", enabled=False)],
            ),
            max_iterations=10,
        )

    # Build a minimal workflow
    step = DAWPStep(
        id="step-0",
        instruction="Do the thing.",
        completion=MarkerCompletion(
            type="marker",
            prompt_marker=PROMPT_MARKER,
            dawp_marker=DAWP_MARKER,
            is_last=True,
        ),
    )
    workflow = DAWPWorkflow(
        metadata=WorkflowMetadata(name=workflow_name),
        spec=WorkflowSpec(
            instruction="",
            contract=Contract(
                action="Act.",
                prompt_marker=PROMPT_MARKER,
                dawp_marker=DAWP_MARKER,
            ),
        ),
        steps=[step],
        activations=[],
    )

    plugin_ctx = AgentPluginContext(
        agent=agent,
        task={},
        context={},
        task_description="drain test",
        plugin_state={
            "dawp.pending": [pending_run],
            "dawp.workflow": workflow,
            "task.iteration_budget": TaskIterationBudget(limit=10),
        },
    )
    budget = plugin_ctx.plugin_state["task.iteration_budget"]
    messages: list[LLMMessage] = [_sys("system")]
    return agent, plugin_ctx, messages, budget


@pytest.mark.unit
@pytest.mark.asyncio
class TestDrainMergeBackIntegration:
    async def test_append_dawp_messages_visible_in_main(self) -> None:
        """append: DAWP assistant messages are added to main messages list."""
        dawp_content = f"Evidence found.\n<DAWP_DONE>"
        run = _pending_run(merge_back="append", workflow_id="wf-test")
        agent, plugin_ctx, messages, budget = _make_drain_agent(
            llm_responses=[dawp_content], pending_run=run
        )

        events = await _collect(
            agent._drain_pending_dawp_runs(
                "on_iteration_end", messages, {}, plugin_ctx, budget
            )
        )

        # Main messages must have grown (DAWP assistant messages were appended)
        assert len(messages) > 1
        # No inject_only summary
        assert not any(
            "[DAWP wf-test: run complete]" in (m.content or "") for m in messages
        )

    async def test_inject_only_dawp_messages_not_in_main(self) -> None:
        """inject_only: DAWP messages must NOT appear in main messages."""
        dawp_content = f"Private evidence.\n<DAWP_DONE>"
        run = _pending_run(merge_back="inject_only", workflow_id="wf-test")
        agent, plugin_ctx, messages, budget = _make_drain_agent(
            llm_responses=[dawp_content], pending_run=run
        )

        await _collect(
            agent._drain_pending_dawp_runs(
                "on_iteration_end", messages, {}, plugin_ctx, budget
            )
        )

        # DAWP content must not be in main messages
        all_content = " ".join(m.content or "" for m in messages)
        assert "Private evidence" not in all_content

    async def test_inject_only_summary_appended_to_main(self) -> None:
        """inject_only: summary message appended to main messages after run."""
        dawp_content = f"Isolated result.\n<DAWP_DONE>"
        run = _pending_run(merge_back="inject_only", workflow_id="wf-test")
        agent, plugin_ctx, messages, budget = _make_drain_agent(
            llm_responses=[dawp_content], pending_run=run
        )

        await _collect(
            agent._drain_pending_dawp_runs(
                "on_iteration_end", messages, {}, plugin_ctx, budget
            )
        )

        # Summary must be present
        summaries = [m for m in messages if "[DAWP wf-test: run complete]" in (m.content or "")]
        assert len(summaries) == 1
        assert summaries[0].role == "assistant"

    async def test_inject_only_exactly_one_extra_message(self) -> None:
        """inject_only: exactly one message added to main messages (the summary)."""
        dawp_content = f"Done.\n<DAWP_DONE>"
        run = _pending_run(merge_back="inject_only", workflow_id="wf-test")
        agent, plugin_ctx, messages, budget = _make_drain_agent(
            llm_responses=[dawp_content], pending_run=run
        )
        before = len(messages)

        await _collect(
            agent._drain_pending_dawp_runs(
                "on_iteration_end", messages, {}, plugin_ctx, budget
            )
        )

        assert len(messages) == before + 1
