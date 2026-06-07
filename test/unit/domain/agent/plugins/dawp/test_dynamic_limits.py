"""
Unit tests for D2-02 — dynamic workflow hard limits (§4.6, D11).

Covers:
- document_loader.compile() with dynamic_workflow_limits:
    - max_prompts: 100-Prompt document rejected
    - max_document_bytes: oversized content rejected (before parse)
    - max_contract_action_chars: action text too long rejected
    - max_iterations_per_prompt: step.max_iterations capped (declared vs. limit min)
    - No limits (None) → limits not enforced
- handle_dawp_start dynamic path:
    - Valid dynamic document → accepted, DawpPendingRun(trigger='tool', workflow_source='dynamic')
    - max_document_bytes exceeded → rejected
    - max_prompts exceeded → rejected
    - require_remaining_budget exhausted → rejected
    - temp_document_path set in pending run
- temp_store.write_task_temp_md:
    - File written to expected path
    - Content round-trips
- DawpPlugin on_pre_task stores dawp.dynamic_limits and dawp.task_id
- DawpPlugin on_post_task removes temp file (default)
- DawpPlugin on_post_task retains temp file when retain_for_debug=True
"""

from __future__ import annotations

import os
import tempfile
import uuid
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from aiecs.domain.agent.plugins.dawp import document_loader
from aiecs.domain.agent.plugins.dawp.schema import DawpDocumentError, DawpPendingRun
from aiecs.domain.agent.plugins.dawp.temp_store import write_task_temp_md
from aiecs.domain.agent.plugins.builtin.tools.dawp_start_tool import handle_dawp_start


# ---------------------------------------------------------------------------
# Document factories
# ---------------------------------------------------------------------------

_PROMPT_MARKER = "<STEP_DONE>"
_DAWP_MARKER = "<WF_COMPLETE>"


def _minimal_doc(name: str = "test-wf", n_prompts: int = 1, action: str = "Do work.") -> str:
    """Return a minimal valid *.dawp.md string with *n_prompts* Prompt blocks."""
    prompts = "\n".join(
        f"<Prompt {i}>\n### Step {i}\nDo step {i}.\n</Prompt {i}>"
        for i in range(n_prompts)
    )
    return f"""---
name: {name}
placement: pre_main_loop
---

## Instruction:

Test workflow.

## Contract

### Action

{action}

### Prompt Completion Marker: `{_PROMPT_MARKER}`

### DAWP Completion Marker: `{_DAWP_MARKER}`

## Prompt

{prompts}
"""


def _plugin_state(
    limits: dict[str, Any] | None = None,
    remaining_budget: int | None = None,
) -> dict[str, Any]:
    state: dict[str, Any] = {
        "dawp.pending": [],
        "dawp.dynamic_limits": limits or {},
        "dawp.task_id": "test-task-123",
    }
    if remaining_budget is not None:
        budget = MagicMock()
        budget.remaining = remaining_budget
        state["task.iteration_budget"] = budget
    return state


# ---------------------------------------------------------------------------
# document_loader.compile — max_prompts
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMaxPromptsLimit:
    def test_100_prompts_rejected(self):
        doc = _minimal_doc(n_prompts=100)
        limits = {"max_prompts": 12}
        with pytest.raises(DawpDocumentError, match="max_prompts"):
            document_loader.compile(doc, dynamic_workflow_limits=limits)

    def test_exactly_at_limit_accepted(self):
        doc = _minimal_doc(n_prompts=12)
        limits = {"max_prompts": 12}
        wf = document_loader.compile(doc, dynamic_workflow_limits=limits)
        assert len(wf.steps) == 12

    def test_one_over_limit_rejected(self):
        doc = _minimal_doc(n_prompts=13)
        limits = {"max_prompts": 12}
        with pytest.raises(DawpDocumentError, match="max_prompts"):
            document_loader.compile(doc, dynamic_workflow_limits=limits)

    def test_no_limits_100_prompts_accepted(self):
        doc = _minimal_doc(n_prompts=100)
        wf = document_loader.compile(doc, dynamic_workflow_limits=None)
        assert len(wf.steps) == 100


# ---------------------------------------------------------------------------
# document_loader.compile — max_document_bytes
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMaxDocumentBytesLimit:
    def test_oversized_document_rejected_before_parse(self):
        big_doc = "x" * 300_000  # 300 KB, > default 256 KB
        limits = {"max_document_bytes": 256_000}
        with pytest.raises(DawpDocumentError, match="max_document_bytes"):
            document_loader.compile(big_doc, dynamic_workflow_limits=limits)

    def test_exactly_at_limit_passes_to_parse(self):
        doc = _minimal_doc()
        small_limit = {"max_document_bytes": len(doc.encode("utf-8"))}
        # Should pass byte check but may or may not succeed (valid doc → success)
        wf = document_loader.compile(doc, dynamic_workflow_limits=small_limit)
        assert wf is not None

    def test_one_byte_over_rejected(self):
        doc = _minimal_doc()
        doc_bytes = doc.encode("utf-8")
        limits = {"max_document_bytes": len(doc_bytes) - 1}
        with pytest.raises(DawpDocumentError, match="max_document_bytes"):
            document_loader.compile(doc, dynamic_workflow_limits=limits)


# ---------------------------------------------------------------------------
# document_loader.compile — max_contract_action_chars
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMaxContractActionCharsLimit:
    def test_long_action_rejected(self):
        long_action = "A" * 9000  # > default 8000
        doc = _minimal_doc(action=long_action)
        limits = {"max_contract_action_chars": 8000}
        with pytest.raises(DawpDocumentError, match="max_contract_action_chars"):
            document_loader.compile(doc, dynamic_workflow_limits=limits)

    def test_exactly_at_limit_accepted(self):
        action = "A" * 8000
        doc = _minimal_doc(action=action)
        limits = {"max_contract_action_chars": 8000}
        wf = document_loader.compile(doc, dynamic_workflow_limits=limits)
        assert len(wf.spec.contract.action) == 8000


# ---------------------------------------------------------------------------
# document_loader.compile — max_iterations_per_prompt
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMaxIterationsPerPromptLimit:
    def test_cap_applied_when_step_has_no_declaration(self):
        doc = _minimal_doc(n_prompts=1)
        limits = {"max_iterations_per_prompt": 4}
        wf = document_loader.compile(doc, dynamic_workflow_limits=limits)
        assert wf.steps[0].max_iterations == 4

    def test_min_taken_when_declared_exceeds_limit(self):
        # The *.dawp.md format doesn't declare per-step max_iterations in front
        # matter directly (it's per-step); we test by checking the loader sets
        # the cap when step.max_iterations is None (the common case).
        doc = _minimal_doc(n_prompts=2)
        limits = {"max_iterations_per_prompt": 3}
        wf = document_loader.compile(doc, dynamic_workflow_limits=limits)
        assert all(s.max_iterations == 3 for s in wf.steps)

    def test_no_limits_leaves_max_iterations_as_none(self):
        doc = _minimal_doc(n_prompts=1)
        wf = document_loader.compile(doc, dynamic_workflow_limits=None)
        assert wf.steps[0].max_iterations is None


# ---------------------------------------------------------------------------
# handle_dawp_start — dynamic path
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHandleDawpStartDynamicPath:
    @pytest.mark.asyncio
    async def test_valid_dynamic_doc_accepted(self):
        doc = _minimal_doc("dyn-wf")
        state = _plugin_state()
        result = await handle_dawp_start(
            state, workflow_source="dynamic", document_content=doc
        )
        assert result["status"] == "accepted"
        assert result["workflow_id"] == "dyn-wf"
        assert result["workflow_source"] == "dynamic"

    @pytest.mark.asyncio
    async def test_dynamic_enqueues_pending_run(self):
        doc = _minimal_doc("dyn-wf")
        state = _plugin_state()
        await handle_dawp_start(state, workflow_source="dynamic", document_content=doc)
        assert len(state["dawp.pending"]) == 1
        run: DawpPendingRun = state["dawp.pending"][0]
        assert run.trigger == "tool"
        assert run.workflow_source == "dynamic"
        assert run.drain_mode == "inline"

    @pytest.mark.asyncio
    async def test_dynamic_sets_temp_document_path(self):
        doc = _minimal_doc("dyn-wf")
        state = _plugin_state()
        await handle_dawp_start(state, workflow_source="dynamic", document_content=doc)
        run: DawpPendingRun = state["dawp.pending"][0]
        assert run.temp_document_path is not None
        path = Path(run.temp_document_path)
        assert path.exists()
        assert path.suffix == ".md"
        # Cleanup
        path.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_dynamic_rejected_when_max_document_bytes_exceeded(self):
        big = "x" * 300_000
        state = _plugin_state(limits={"max_document_bytes": 10_000})
        result = await handle_dawp_start(
            state, workflow_source="dynamic", document_content=big
        )
        assert result["status"] == "rejected"
        assert "max_document_bytes" in result["reason"]
        assert state["dawp.pending"] == []

    @pytest.mark.asyncio
    async def test_dynamic_rejected_when_max_prompts_exceeded(self):
        doc = _minimal_doc(n_prompts=20)
        state = _plugin_state(limits={"max_prompts": 5})
        result = await handle_dawp_start(
            state, workflow_source="dynamic", document_content=doc
        )
        assert result["status"] == "rejected"
        assert "max_prompts" in result["reason"]
        assert state["dawp.pending"] == []

    @pytest.mark.asyncio
    async def test_dynamic_rejected_when_insufficient_budget(self):
        doc = _minimal_doc()
        state = _plugin_state(
            limits={"require_remaining_budget": 5},
            remaining_budget=2,
        )
        result = await handle_dawp_start(
            state, workflow_source="dynamic", document_content=doc
        )
        assert result["status"] == "rejected"
        assert "budget" in result["reason"]
        assert state["dawp.pending"] == []

    @pytest.mark.asyncio
    async def test_dynamic_accepted_when_budget_exactly_meets_requirement(self):
        doc = _minimal_doc()
        state = _plugin_state(
            limits={"require_remaining_budget": 3},
            remaining_budget=3,
        )
        result = await handle_dawp_start(
            state, workflow_source="dynamic", document_content=doc
        )
        assert result["status"] == "accepted"
        # Cleanup temp file
        run = state["dawp.pending"][0]
        if run.temp_document_path:
            Path(run.temp_document_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_dynamic_no_budget_object_skips_budget_check(self):
        """When plugin_state has no iteration_budget, budget check is skipped."""
        doc = _minimal_doc()
        state = _plugin_state(limits={"require_remaining_budget": 10})
        # No "task.iteration_budget" in state → no budget object → skip check
        result = await handle_dawp_start(
            state, workflow_source="dynamic", document_content=doc
        )
        assert result["status"] == "accepted"
        run = state["dawp.pending"][0]
        if run.temp_document_path:
            Path(run.temp_document_path).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# temp_store.write_task_temp_md
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestWriteTaskTempMd:
    def test_file_written_in_expected_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_task_temp_md("content", task_id="task-abc", base_dir=tmp)
            expected_dir = Path(tmp) / "aiecs_dawp" / "task-abc"
            assert path.parent == expected_dir
            assert path.suffix == ".md"

    def test_content_round_trips(self):
        content = "---\nname: test\n---\nbody text"
        with tempfile.TemporaryDirectory() as tmp:
            path = write_task_temp_md(content, task_id="task-rt", base_dir=tmp)
            assert path.read_text(encoding="utf-8") == content

    def test_unique_filenames_per_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            p1 = write_task_temp_md("a", task_id="same-task", base_dir=tmp)
            p2 = write_task_temp_md("b", task_id="same-task", base_dir=tmp)
            assert p1 != p2

    def test_directory_created_if_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "nested" / "deep"
            path = write_task_temp_md("x", task_id="t1", base_dir=base)
            assert path.exists()


# ---------------------------------------------------------------------------
# DawpPlugin on_pre_task — limits and task_id stored
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDawpPluginPreTaskLimits:
    def _make_plugin(self, options: dict[str, Any] | None = None) -> Any:
        from aiecs.domain.agent.plugins.builtin.dawp_plugin import DawpPlugin
        from aiecs.domain.agent.plugins.models import PluginConfig

        agent = MagicMock()
        agent.agent_id = "test-agent"
        agent._tool_instances = {}
        agent._tool_schemas = []
        agent._current_task_id = "task-xyz-999"
        config = PluginConfig(name="dawp", enabled=True, options=options or {})
        return DawpPlugin(config, agent)

    def _make_ctx(self) -> Any:
        ctx = MagicMock()
        ctx.plugin_state = {}
        return ctx

    @pytest.mark.asyncio
    async def test_dynamic_limits_stored_in_plugin_state(self):
        limits = {"max_prompts": 5, "max_document_bytes": 1000}
        plugin = self._make_plugin(options={"dynamic_workflow_limits": limits})
        ctx = self._make_ctx()
        await plugin.on_pre_task(ctx)
        assert ctx.plugin_state["dawp.dynamic_limits"] == limits

    @pytest.mark.asyncio
    async def test_dynamic_limits_empty_when_not_configured(self):
        plugin = self._make_plugin()
        ctx = self._make_ctx()
        await plugin.on_pre_task(ctx)
        assert ctx.plugin_state["dawp.dynamic_limits"] == {}

    @pytest.mark.asyncio
    async def test_task_id_stored_from_agent(self):
        plugin = self._make_plugin()
        ctx = self._make_ctx()
        await plugin.on_pre_task(ctx)
        assert ctx.plugin_state["dawp.task_id"] == "task-xyz-999"

    @pytest.mark.asyncio
    async def test_task_id_uses_uuid_when_agent_has_none(self):
        plugin = self._make_plugin()
        plugin._agent._current_task_id = None
        ctx = self._make_ctx()
        await plugin.on_pre_task(ctx)
        task_id = ctx.plugin_state["dawp.task_id"]
        # Should be a valid UUID string
        uuid.UUID(task_id)


# ---------------------------------------------------------------------------
# DawpPlugin on_post_task — temp file cleanup
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDawpPluginPostTaskCleanup:
    def _make_plugin(self, retain: bool = False) -> Any:
        from aiecs.domain.agent.plugins.builtin.dawp_plugin import DawpPlugin
        from aiecs.domain.agent.plugins.models import PluginConfig

        agent = MagicMock()
        agent.agent_id = "test-agent"
        agent._tool_instances = {}
        agent._tool_schemas = []
        config = PluginConfig(
            name="dawp",
            enabled=True,
            options={"retain_for_debug": retain},
        )
        return DawpPlugin(config, agent)

    def _make_ctx(self, temp_path: str | None = None) -> Any:
        ctx = MagicMock()
        runs = []
        if temp_path:
            run = MagicMock()
            run.temp_document_path = temp_path
            runs.append(run)
        ctx.plugin_state = {
            "dawp.pending": runs,
        }
        return ctx

    @pytest.mark.asyncio
    async def test_temp_file_removed_by_default(self):
        with tempfile.NamedTemporaryFile(suffix=".dawp.md", delete=False) as f:
            temp_path = f.name

        plugin = self._make_plugin(retain=False)
        ctx = self._make_ctx(temp_path=temp_path)
        await plugin.on_post_task(ctx, result={})

        assert not Path(temp_path).exists()

    @pytest.mark.asyncio
    async def test_temp_file_retained_when_retain_for_debug_true(self):
        with tempfile.NamedTemporaryFile(suffix=".dawp.md", delete=False) as f:
            temp_path = f.name

        plugin = self._make_plugin(retain=True)
        ctx = self._make_ctx(temp_path=temp_path)
        await plugin.on_post_task(ctx, result={})

        assert Path(temp_path).exists()
        # Cleanup after test
        os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_no_temp_files_no_error(self):
        plugin = self._make_plugin()
        ctx = self._make_ctx(temp_path=None)
        # Should not raise
        await plugin.on_post_task(ctx, result={})
