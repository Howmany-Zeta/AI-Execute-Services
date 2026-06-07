"""
Unit tests for D1-08 — DawpPlugin full lifecycle hooks (§9, §6.5).

Covers:
- PRE_TASK: plugin_state keys initialised; workflow loaded; scheduler activations built
- PRE_TASK: missing document_path → no workflow, empty scheduler
- PRE_TASK: bad document → warning logged, workflow=None, returns gracefully
- PRE_MAIN_LOOP: pre_main_loop activations enqueued into dawp.pending
- PRE_MAIN_LOOP: no workflow → no-op, returns None (not PluginShortCircuitResult)
- PRE_MAIN_LOOP: no activations → pending queue unchanged
- ON_ITERATION_END: on_response_trigger fires when assistant text contains trigger
- ON_ITERATION_END: DOES NOT invoke LLM client (critical §6.5 constraint)
- ON_ITERATION_END: no workflow → no-op
- ON_ITERATION_END: no matching activation → pending unchanged
- ON_ITERATION_END: trigger_once guard prevents second enqueue
- POST_TASK: all dawp.* keys removed from plugin_state
- POST_TASK: result dict returned unchanged
- POST_TASK: temp file removed when present in a pending run
- priority=45
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from aiecs.domain.agent.plugins.context import AgentPluginContext
from aiecs.domain.agent.plugins.models import PluginConfig
from aiecs.domain.agent.plugins.dawp.schema import (
    Activation,
    DawpPendingRun,
    OnResponseTriggerPlacement,
    PreMainLoopPlacement,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TRIGGER = "<START_OODA_REVIEW>"
_DAWP_MD = """\
---
name: test-ooda
---

## Contract

### Action
Follow OODA.

### Prompt Completion Marker: `<OODA_STEP_DONE>`

### DAWP Completion Marker: `<OODA_COMPLETE>`

## Prompt 0: observe

Observe the environment.

## Appendix
"""


def _make_plugin(options: dict[str, Any] | None = None) -> Any:
    from aiecs.domain.agent.plugins.builtin.dawp_plugin import DawpPlugin

    agent = MagicMock()
    agent.llm_client = MagicMock()  # should NEVER be called in ON_ITERATION_END
    config = PluginConfig(name="dawp", enabled=True, options=options or {})
    return DawpPlugin(config, agent)


def _ctx() -> AgentPluginContext:
    ctx = MagicMock(spec=AgentPluginContext)
    ctx.plugin_state = {}
    return ctx


def _step_payload(thoughts: list[str], kind: str = "final") -> dict[str, Any]:
    """Minimal step payload matching _iteration_step_payload output."""
    steps = [{"type": "thought", "content": t} for t in thoughts]
    return {"kind": kind, "iteration": 1, "steps": steps, "tool_calls_count": 0}


# ---------------------------------------------------------------------------
# Priority
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_priority_45() -> None:
    from aiecs.domain.agent.plugins.builtin.dawp_plugin import DawpPlugin
    assert DawpPlugin.metadata.priority == 45


# ---------------------------------------------------------------------------
# PRE_TASK
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestPreTask:
    async def test_initialises_state_keys_no_document(self) -> None:
        plugin = _make_plugin()
        ctx = _ctx()
        await plugin.on_pre_task(ctx)

        assert "dawp.workflow" in ctx.plugin_state
        assert "dawp.scheduler" in ctx.plugin_state
        assert "dawp.pending" in ctx.plugin_state

    async def test_no_document_path_workflow_is_none(self) -> None:
        plugin = _make_plugin()
        ctx = _ctx()
        await plugin.on_pre_task(ctx)

        assert ctx.plugin_state["dawp.workflow"] is None
        assert ctx.plugin_state["dawp.scheduler"] == []

    async def test_loads_workflow_from_file(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".dawp.md", mode="w", delete=False) as f:
            f.write(_DAWP_MD)
            path = f.name

        try:
            plugin = _make_plugin({"document_path": path})
            ctx = _ctx()
            await plugin.on_pre_task(ctx)

            wf = ctx.plugin_state["dawp.workflow"]
            assert wf is not None
            assert wf.metadata.name == "test-ooda"
        finally:
            Path(path).unlink(missing_ok=True)

    async def test_builds_scheduler_activations(self) -> None:
        """plugin_state["dawp.scheduler"] is a list of (workflow_id, Activation) pairs."""
        with tempfile.NamedTemporaryFile(suffix=".dawp.md", mode="w", delete=False) as f:
            # Add an on_response_trigger activation
            content = _DAWP_MD + "\n---\nplacement: on_response_trigger\ndawp_trigger: " + _TRIGGER + "\n---\n"
            f.write(content)
            path = f.name

        try:
            plugin = _make_plugin({"document_path": path})
            ctx = _ctx()
            await plugin.on_pre_task(ctx)

            scheduler = ctx.plugin_state["dawp.scheduler"]
            assert isinstance(scheduler, list)
        finally:
            Path(path).unlink(missing_ok=True)

    async def test_bad_document_path_warns_and_continues(self) -> None:
        plugin = _make_plugin({"document_path": "/nonexistent/path/workflow.dawp.md"})
        ctx = _ctx()
        # Should not raise
        await plugin.on_pre_task(ctx)
        assert ctx.plugin_state["dawp.workflow"] is None

    async def test_pending_queue_initialised_as_list(self) -> None:
        plugin = _make_plugin()
        ctx = _ctx()
        await plugin.on_pre_task(ctx)
        assert ctx.plugin_state["dawp.pending"] == []


# ---------------------------------------------------------------------------
# PRE_MAIN_LOOP
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestPreMainLoop:
    async def test_no_workflow_returns_none(self) -> None:
        plugin = _make_plugin()
        ctx = _ctx()
        await plugin.on_pre_task(ctx)
        result = await plugin.on_pre_main_loop(ctx)
        assert result is None

    async def test_pre_main_loop_activation_enqueued(self) -> None:
        """pre_main_loop activation → appended to dawp.pending."""
        plugin = _make_plugin()
        ctx = _ctx()
        await plugin.on_pre_task(ctx)

        # Inject a pre_main_loop activation into the scheduler list
        ctx.plugin_state["dawp.scheduler"] = [
            ("test-wf", Activation(placement=PreMainLoopPlacement())),
        ]

        await plugin.on_pre_main_loop(ctx)

        pending = ctx.plugin_state["dawp.pending"]
        assert len(pending) == 1
        assert pending[0].workflow_id == "test-wf"
        assert pending[0].drain_mode == "on_iteration_end"

    async def test_no_activations_pending_unchanged(self) -> None:
        plugin = _make_plugin()
        ctx = _ctx()
        await plugin.on_pre_task(ctx)
        ctx.plugin_state["dawp.scheduler"] = []  # no activations
        await plugin.on_pre_main_loop(ctx)
        assert ctx.plugin_state["dawp.pending"] == []

    async def test_on_response_trigger_activation_not_enqueued_at_pre_main(self) -> None:
        """on_response_trigger activations must not fire during pre_main_loop."""
        plugin = _make_plugin()
        ctx = _ctx()
        await plugin.on_pre_task(ctx)
        ctx.plugin_state["dawp.scheduler"] = [
            ("test-wf", Activation(
                placement=OnResponseTriggerPlacement(dawp_trigger=_TRIGGER)
            )),
        ]
        await plugin.on_pre_main_loop(ctx)
        assert ctx.plugin_state["dawp.pending"] == []

    async def test_never_returns_short_circuit_result(self) -> None:
        from aiecs.domain.agent.plugins.base import PluginShortCircuitResult
        plugin = _make_plugin()
        ctx = _ctx()
        await plugin.on_pre_task(ctx)
        ctx.plugin_state["dawp.scheduler"] = [
            ("wf", Activation(placement=PreMainLoopPlacement())),
        ]
        result = await plugin.on_pre_main_loop(ctx)
        assert not isinstance(result, PluginShortCircuitResult)


# ---------------------------------------------------------------------------
# ON_ITERATION_END — §6.5 critical: MUST NOT call LLM
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestOnIterationEnd:
    async def test_does_not_invoke_llm_client(self) -> None:
        """Critical §6.5 constraint: ON_ITERATION_END must not call the LLM."""
        plugin = _make_plugin()
        ctx = _ctx()
        await plugin.on_pre_task(ctx)
        ctx.plugin_state["dawp.scheduler"] = [
            ("test-wf", Activation(
                placement=OnResponseTriggerPlacement(dawp_trigger=_TRIGGER)
            )),
        ]

        step = _step_payload([f"Analysis done.\n{_TRIGGER}"])
        await plugin.on_iteration_end(ctx, iteration=0, step=step)

        # LLM client must never have been called
        plugin._agent.llm_client.assert_not_called()
        # But the run should be enqueued
        assert len(ctx.plugin_state["dawp.pending"]) == 1

    async def test_trigger_in_assistant_text_enqueues(self) -> None:
        plugin = _make_plugin()
        ctx = _ctx()
        await plugin.on_pre_task(ctx)
        ctx.plugin_state["dawp.scheduler"] = [
            ("ooda", Activation(
                placement=OnResponseTriggerPlacement(dawp_trigger=_TRIGGER)
            )),
        ]

        step = _step_payload([f"Analysis complete.\n{_TRIGGER}"])
        await plugin.on_iteration_end(ctx, iteration=2, step=step)

        pending = ctx.plugin_state["dawp.pending"]
        assert len(pending) == 1
        run = pending[0]
        assert run.workflow_id == "ooda"
        assert run.enqueued_at_iteration == 2

    async def test_trigger_not_in_text_no_enqueue(self) -> None:
        plugin = _make_plugin()
        ctx = _ctx()
        await plugin.on_pre_task(ctx)
        ctx.plugin_state["dawp.scheduler"] = [
            ("ooda", Activation(
                placement=OnResponseTriggerPlacement(dawp_trigger=_TRIGGER)
            )),
        ]

        step = _step_payload(["No trigger here."])
        await plugin.on_iteration_end(ctx, iteration=0, step=step)

        assert ctx.plugin_state["dawp.pending"] == []

    async def test_trigger_once_blocks_second_enqueue(self) -> None:
        plugin = _make_plugin()
        ctx = _ctx()
        await plugin.on_pre_task(ctx)
        ctx.plugin_state["dawp.scheduler"] = [
            ("ooda", Activation(
                placement=OnResponseTriggerPlacement(dawp_trigger=_TRIGGER, trigger_once=True)
            )),
        ]
        text = f"Done.\n{_TRIGGER}"
        step = _step_payload([text])

        await plugin.on_iteration_end(ctx, iteration=0, step=step)
        await plugin.on_iteration_end(ctx, iteration=1, step=step)

        assert len(ctx.plugin_state["dawp.pending"]) == 1

    async def test_no_workflow_activations_no_op(self) -> None:
        plugin = _make_plugin()
        ctx = _ctx()
        await plugin.on_pre_task(ctx)
        # scheduler is empty (no document_path)
        step = _step_payload([f"Text.\n{_TRIGGER}"])
        await plugin.on_iteration_end(ctx, iteration=0, step=step)
        assert ctx.plugin_state["dawp.pending"] == []

    async def test_empty_steps_list_no_crash(self) -> None:
        """Step payload with empty steps list must not raise."""
        plugin = _make_plugin()
        ctx = _ctx()
        await plugin.on_pre_task(ctx)
        ctx.plugin_state["dawp.scheduler"] = [
            ("ooda", Activation(
                placement=OnResponseTriggerPlacement(dawp_trigger=_TRIGGER)
            )),
        ]
        step = {"kind": "continue", "iteration": 1, "steps": [], "tool_calls_count": 1}
        await plugin.on_iteration_end(ctx, iteration=0, step=step)
        assert ctx.plugin_state["dawp.pending"] == []

    async def test_uses_last_thought_when_multiple_steps(self) -> None:
        """When step payload has thought + actions + thought, uses the LAST thought."""
        plugin = _make_plugin()
        ctx = _ctx()
        await plugin.on_pre_task(ctx)
        ctx.plugin_state["dawp.scheduler"] = [
            ("ooda", Activation(
                placement=OnResponseTriggerPlacement(dawp_trigger=_TRIGGER)
            )),
        ]
        steps = [
            {"type": "thought", "content": "Initial analysis."},
            {"type": "action", "tool": "search"},
            {"type": "observation", "content": "results"},
            {"type": "thought", "content": f"Final analysis.\n{_TRIGGER}"},
        ]
        step = {"kind": "final", "iteration": 1, "steps": steps, "tool_calls_count": 1}
        await plugin.on_iteration_end(ctx, iteration=0, step=step)
        assert len(ctx.plugin_state["dawp.pending"]) == 1


# ---------------------------------------------------------------------------
# POST_TASK
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestPostTask:
    async def test_removes_all_dawp_keys(self) -> None:
        plugin = _make_plugin()
        ctx = _ctx()
        ctx.plugin_state["dawp.workflow"] = MagicMock()
        ctx.plugin_state["dawp.scheduler"] = []
        ctx.plugin_state["dawp.pending"] = []
        ctx.plugin_state["dawp.active_run_id"] = "run-123"
        ctx.plugin_state["dawp.triggered.<FOO>"] = True
        ctx.plugin_state["other.key"] = "preserved"

        await plugin.on_post_task(ctx, {"success": True})

        dawp_keys = [k for k in ctx.plugin_state if k.startswith("dawp.")]
        assert dawp_keys == []
        assert ctx.plugin_state["other.key"] == "preserved"

    async def test_returns_result_unchanged(self) -> None:
        plugin = _make_plugin()
        ctx = _ctx()
        await plugin.on_pre_task(ctx)
        result = {"success": True, "output": "done"}
        returned = await plugin.on_post_task(ctx, result)
        assert returned == result

    async def test_temp_file_removed(self) -> None:
        """Temp files referenced in pending DawpPendingRun are deleted."""
        plugin = _make_plugin()
        ctx = _ctx()
        await plugin.on_pre_task(ctx)

        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = f.name
        assert Path(temp_path).exists()

        pending_run = DawpPendingRun(
            trigger="tool",
            workflow_source="dynamic",
            workflow_id="dyn-wf",
            temp_document_path=temp_path,
            enqueued_at_iteration=0,
            drain_mode="inline",
        )
        ctx.plugin_state["dawp.pending"] = [pending_run]

        await plugin.on_post_task(ctx, {})

        assert not Path(temp_path).exists()

    async def test_no_error_on_empty_state(self) -> None:
        """post_task on a fresh ctx must not raise."""
        plugin = _make_plugin()
        ctx = _ctx()
        await plugin.on_post_task(ctx, {})
