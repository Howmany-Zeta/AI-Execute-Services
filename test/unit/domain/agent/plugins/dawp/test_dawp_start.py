"""
Unit tests for D2-01 — ``dawp_start`` tool handler and DawpPlugin injection.

Covers:
- handle_dawp_start: accepted for valid static workflow
- handle_dawp_start: rejected when dawp.active_run_id set (D10)
- handle_dawp_start: rejected when no workflow compiled
- handle_dawp_start: rejected when workflow_id mismatches loaded workflow
- handle_dawp_start: rejected for dynamic with missing document_content
- handle_dawp_start: rejected for unknown workflow_source
- Enqueued DawpPendingRun has trigger='tool', drain_mode='inline'
- DawpStartHandler.run_async delegates to handle_dawp_start
- DawpStartHandler.bind_plugin_state wires plugin_state
- DawpLegacyAliasHandler emits DeprecationWarning and forwards
- DawpPlugin.on_pre_task injects dawp_start into agent._tool_instances and _tool_schemas
- DawpPlugin.on_post_task removes dawp_start and unbinds plugin_state
- DAWP_START_TOOL_SCHEMA has required fields
"""

from __future__ import annotations

import warnings
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from aiecs.domain.agent.plugins.builtin.tools.dawp_start_tool import (
    DAWP_START_TOOL_SCHEMA,
    DawpLegacyAliasHandler,
    DawpStartHandler,
    handle_dawp_start,
)
from aiecs.domain.agent.plugins.dawp.schema import (
    Contract,
    DAWPStep,
    DAWPWorkflow,
    DawpPendingRun,
    MarkerCompletion,
    WorkflowMetadata,
    WorkflowSpec,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PROMPT_MARKER = "<STEP_DONE>"
_DAWP_MARKER = "<WF_COMPLETE>"


def _workflow(name: str = "review-wf") -> DAWPWorkflow:
    return DAWPWorkflow(
        metadata=WorkflowMetadata(name=name),
        spec=WorkflowSpec(
            contract=Contract(
                action="Review.",
                prompt_marker=_PROMPT_MARKER,
                dawp_marker=_DAWP_MARKER,
            )
        ),
        steps=[
            DAWPStep(
                id="step1",
                instruction="Do work.",
                completion=MarkerCompletion(
                    prompt_marker=_PROMPT_MARKER,
                    dawp_marker=_DAWP_MARKER,
                    is_last=True,
                ),
            )
        ],
        activations=[],
    )


def _plugin_state(
    workflow: DAWPWorkflow | None = None,
    active_run_id: str | None = None,
) -> dict[str, Any]:
    state: dict[str, Any] = {
        "dawp.workflow": workflow,
        "dawp.pending": [],
    }
    if active_run_id is not None:
        state["dawp.active_run_id"] = active_run_id
    return state


# ---------------------------------------------------------------------------
# handle_dawp_start — static path
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHandleDawpStartStatic:
    @pytest.mark.asyncio
    async def test_accepted_for_valid_static_workflow(self):
        wf = _workflow("my-review")
        state = _plugin_state(workflow=wf)
        result = await handle_dawp_start(state, workflow_source="static")
        assert result["status"] == "accepted"
        assert result["workflow_id"] == "my-review"
        assert result["workflow_source"] == "static"
        assert result["suppress_from_llm"] is True

    @pytest.mark.asyncio
    async def test_accepted_with_matching_workflow_id(self):
        wf = _workflow("my-review")
        state = _plugin_state(workflow=wf)
        result = await handle_dawp_start(
            state, workflow_source="static", workflow_id="my-review"
        )
        assert result["status"] == "accepted"

    @pytest.mark.asyncio
    async def test_enqueues_pending_run_with_correct_fields(self):
        wf = _workflow("my-review")
        state = _plugin_state(workflow=wf)
        await handle_dawp_start(state, workflow_source="static")
        assert len(state["dawp.pending"]) == 1
        run: DawpPendingRun = state["dawp.pending"][0]
        assert isinstance(run, DawpPendingRun)
        assert run.trigger == "tool"
        assert run.workflow_source == "static"
        assert run.workflow_id == "my-review"
        assert run.drain_mode == "inline"

    @pytest.mark.asyncio
    async def test_rejected_when_no_workflow_in_state(self):
        state = _plugin_state(workflow=None)
        result = await handle_dawp_start(state, workflow_source="static")
        assert result["status"] == "rejected"
        assert "no compiled workflow" in result["reason"]
        assert state["dawp.pending"] == []

    @pytest.mark.asyncio
    async def test_rejected_when_workflow_id_mismatches(self):
        wf = _workflow("real-wf")
        state = _plugin_state(workflow=wf)
        result = await handle_dawp_start(
            state, workflow_source="static", workflow_id="other-wf"
        )
        assert result["status"] == "rejected"
        assert "other-wf" in result["reason"]
        assert state["dawp.pending"] == []

    @pytest.mark.asyncio
    async def test_rejected_when_active_run_id_set(self):
        wf = _workflow()
        state = _plugin_state(workflow=wf, active_run_id="run-abc")
        result = await handle_dawp_start(state, workflow_source="static")
        assert result["status"] == "rejected"
        assert "D10" in result["reason"]
        assert state["dawp.pending"] == []

    @pytest.mark.asyncio
    async def test_accepted_with_document_path(self, tmp_path):
        doc = f"""---
name: path-wf
placement: pre_main_loop
---

## Instruction:
Test.

## Contract
### Action
Act.
### Prompt Completion Marker: `{_PROMPT_MARKER}`
### DAWP Completion Marker: `{_DAWP_MARKER}`

## Prompt
<Prompt 0>
Step.
</Prompt 0>
"""
        path = tmp_path / "inline.dawp.md"
        path.write_text(doc, encoding="utf-8")
        state = _plugin_state(workflow=None)
        from aiecs.domain.agent.plugins.dawp.document_path_policy import (
            configure_document_path_policy,
        )

        configure_document_path_policy(state, {"document_path": str(path)})
        result = await handle_dawp_start(
            state,
            workflow_source="static",
            document_path=str(path),
        )
        assert result["status"] == "accepted"
        assert result["workflow_id"] == "path-wf"
        assert state["dawp.workflows"]["path-wf"].metadata.name == "path-wf"

    @pytest.mark.asyncio
    async def test_document_path_outside_allowlist_rejected(self, tmp_path):
        doc = tmp_path / "outside.dawp.md"
        doc.write_text("x", encoding="utf-8")
        state = _plugin_state(workflow=None)
        from aiecs.domain.agent.plugins.dawp.document_path_policy import (
            configure_document_path_policy,
        )

        configure_document_path_policy(state, {"allowed_document_roots": [str(tmp_path / "allowed")]})
        result = await handle_dawp_start(
            state,
            workflow_source="static",
            document_path=str(doc),
        )
        assert result["status"] == "rejected"
        assert state["dawp.pending"] == []

    @pytest.mark.asyncio
    async def test_rejected_for_unknown_workflow_source(self):
        state = _plugin_state()
        result = await handle_dawp_start(state, workflow_source="custom")  # type: ignore[arg-type]
        assert result["status"] == "rejected"
        assert "unknown workflow_source" in result["reason"]


# ---------------------------------------------------------------------------
# handle_dawp_start — dynamic path
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHandleDawpStartDynamic:
    @pytest.mark.asyncio
    async def test_rejected_when_document_content_missing(self):
        state = _plugin_state()
        result = await handle_dawp_start(state, workflow_source="dynamic")
        assert result["status"] == "rejected"
        assert "document_content" in result["reason"]

    @pytest.mark.asyncio
    async def test_dynamic_with_invalid_content_rejected(self):
        """Invalid document_content produces a rejected status (parse error)."""
        state = _plugin_state()
        result = await handle_dawp_start(
            state,
            workflow_source="dynamic",
            document_content="not a valid dawp document at all",
        )
        assert result["status"] == "rejected"

    @pytest.mark.asyncio
    async def test_no_pending_run_enqueued_on_dynamic_rejection(self):
        state = _plugin_state()
        await handle_dawp_start(
            state,
            workflow_source="dynamic",
            document_content="not a valid dawp document at all",
        )
        assert state["dawp.pending"] == []

    @pytest.mark.asyncio
    async def test_dynamic_accepted_registers_workflow(self):
        doc = f"""---
name: dyn-wf
placement: pre_main_loop
---

## Instruction:
Test.

## Contract
### Action
Act.
### Prompt Completion Marker: `{_PROMPT_MARKER}`
### DAWP Completion Marker: `{_DAWP_MARKER}`

## Prompt
<Prompt 0>
Step.
</Prompt 0>
"""
        state = _plugin_state()
        state["dawp.task_id"] = "task-1"
        result = await handle_dawp_start(
            state,
            workflow_source="dynamic",
            document_content=doc,
        )
        assert result["status"] == "accepted"
        assert state["dawp.workflows"]["dyn-wf"].metadata.name == "dyn-wf"
        assert len(state["dawp.pending"]) == 1
        assert state["dawp.pending"][0].workflow_source == "dynamic"


# ---------------------------------------------------------------------------
# DawpStartHandler
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDawpStartHandler:
    @pytest.mark.asyncio
    async def test_run_async_accepted_when_state_bound(self):
        wf = _workflow("wf1")
        state = _plugin_state(workflow=wf)
        handler = DawpStartHandler()
        handler.bind_plugin_state(state)
        result = await handler.run_async(workflow_source="static")
        assert result["status"] == "accepted"
        assert result["workflow_id"] == "wf1"

    @pytest.mark.asyncio
    async def test_run_async_uses_empty_dict_when_state_none(self):
        handler = DawpStartHandler()
        # No bind_plugin_state call — defaults to {}
        result = await handler.run_async(workflow_source="static")
        assert result["status"] == "rejected"
        assert "no compiled workflow" in result["reason"]

    def test_bind_plugin_state_sets_state(self):
        handler = DawpStartHandler()
        state: dict[str, Any] = {"key": "val"}
        handler.bind_plugin_state(state)
        assert handler._plugin_state is state

    def test_bind_plugin_state_none_clears(self):
        handler = DawpStartHandler()
        handler.bind_plugin_state({"key": "val"})
        handler.bind_plugin_state(None)
        assert handler._plugin_state is None

    def test_name_attribute(self):
        assert DawpStartHandler.name == "dawp_start"


# ---------------------------------------------------------------------------
# DawpLegacyAliasHandler
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDawpLegacyAliasHandler:
    @pytest.mark.asyncio
    async def test_emits_deprecation_warning(self):
        handler = DawpStartHandler()
        wf = _workflow()
        handler.bind_plugin_state(_plugin_state(workflow=wf))
        alias = DawpLegacyAliasHandler("dawp_run", handler)

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            await alias.run_async(workflow_source="static")
        assert any(issubclass(w.category, DeprecationWarning) for w in caught)

    @pytest.mark.asyncio
    async def test_deprecation_warning_mentions_name(self):
        handler = DawpStartHandler()
        handler.bind_plugin_state(_plugin_state())
        alias = DawpLegacyAliasHandler("dawp_publish_workflow", handler)

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            await alias.run_async(workflow_source="dynamic", document_content="x")
        assert any("dawp_publish_workflow" in str(w.message) for w in caught)

    @pytest.mark.asyncio
    async def test_forwards_to_delegate(self):
        wf = _workflow("wf-delegate")
        state = _plugin_state(workflow=wf)
        handler = DawpStartHandler()
        handler.bind_plugin_state(state)
        alias = DawpLegacyAliasHandler("dawp_run", handler)

        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = await alias.run_async(workflow_source="static")
        assert result["status"] == "accepted"
        assert result["workflow_id"] == "wf-delegate"

    def test_name_attribute(self):
        handler = DawpStartHandler()
        alias = DawpLegacyAliasHandler("dawp_run", handler)
        assert alias.name == "dawp_run"


# ---------------------------------------------------------------------------
# DAWP_START_TOOL_SCHEMA
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDawpStartToolSchema:
    def test_name(self):
        assert DAWP_START_TOOL_SCHEMA["name"] == "dawp_start"

    def test_workflow_source_required(self):
        params = DAWP_START_TOOL_SCHEMA["parameters"]
        assert "workflow_source" in params["required"]

    def test_workflow_source_enum(self):
        props = DAWP_START_TOOL_SCHEMA["parameters"]["properties"]
        assert set(props["workflow_source"]["enum"]) == {"static", "dynamic"}

    def test_has_description(self):
        assert DAWP_START_TOOL_SCHEMA.get("description")


# ---------------------------------------------------------------------------
# DawpPlugin tool injection (on_pre_task / on_post_task)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDawpPluginToolInjection:
    """Verify on_pre_task injects dawp_start and on_post_task removes it."""

    def _make_plugin(self, agent: Any) -> Any:
        from aiecs.domain.agent.plugins.builtin.dawp_plugin import DawpPlugin
        from aiecs.domain.agent.plugins.models import PluginConfig

        config = PluginConfig(name="dawp", enabled=True, options={})
        return DawpPlugin(config, agent)

    def _make_agent(self) -> MagicMock:
        agent = MagicMock()
        agent.agent_id = "test-agent"
        agent._tool_instances = {}
        agent._tool_schemas = []
        return agent

    def _make_ctx(self, plugin_state: dict[str, Any] | None = None) -> Any:
        ctx = MagicMock()
        ctx.plugin_state = plugin_state if plugin_state is not None else {}
        return ctx

    @pytest.mark.asyncio
    async def test_on_pre_task_injects_dawp_start_instance(self):
        agent = self._make_agent()
        plugin = self._make_plugin(agent)
        ctx = self._make_ctx()

        await plugin.on_pre_task(ctx)

        assert "dawp_start" in agent._tool_instances
        assert hasattr(agent._tool_instances["dawp_start"], "run_async")

    @pytest.mark.asyncio
    async def test_on_pre_task_injects_legacy_aliases(self):
        agent = self._make_agent()
        plugin = self._make_plugin(agent)
        ctx = self._make_ctx()

        await plugin.on_pre_task(ctx)

        assert "dawp_run" in agent._tool_instances
        assert "dawp_publish_workflow" in agent._tool_instances

    @pytest.mark.asyncio
    async def test_on_pre_task_appends_schema(self):
        agent = self._make_agent()
        plugin = self._make_plugin(agent)
        ctx = self._make_ctx()

        await plugin.on_pre_task(ctx)

        schema_names = [s.get("name") for s in agent._tool_schemas]
        assert "dawp_start" in schema_names

    @pytest.mark.asyncio
    async def test_on_pre_task_does_not_duplicate_schema(self):
        agent = self._make_agent()
        agent._tool_schemas = [{"name": "dawp_start"}]
        plugin = self._make_plugin(agent)
        ctx = self._make_ctx()

        await plugin.on_pre_task(ctx)

        count = sum(1 for s in agent._tool_schemas if s.get("name") == "dawp_start")
        assert count == 1

    @pytest.mark.asyncio
    async def test_on_pre_task_binds_plugin_state_to_handler(self):
        agent = self._make_agent()
        plugin = self._make_plugin(agent)
        state: dict[str, Any] = {}
        ctx = self._make_ctx(plugin_state=state)

        await plugin.on_pre_task(ctx)

        handler = agent._tool_instances["dawp_start"]
        assert handler._plugin_state is state

    @pytest.mark.asyncio
    async def test_on_post_task_removes_dawp_start(self):
        agent = self._make_agent()
        plugin = self._make_plugin(agent)
        ctx = self._make_ctx()

        await plugin.on_pre_task(ctx)
        assert "dawp_start" in agent._tool_instances

        await plugin.on_post_task(ctx, result={})

        assert "dawp_start" not in agent._tool_instances
        assert "dawp_run" not in agent._tool_instances
        assert "dawp_publish_workflow" not in agent._tool_instances

    @pytest.mark.asyncio
    async def test_on_post_task_removes_schema(self):
        agent = self._make_agent()
        plugin = self._make_plugin(agent)
        ctx = self._make_ctx()

        await plugin.on_pre_task(ctx)
        await plugin.on_post_task(ctx, result={})

        schema_names = [s.get("name") for s in agent._tool_schemas]
        assert "dawp_start" not in schema_names

    @pytest.mark.asyncio
    async def test_on_post_task_unbinds_plugin_state(self):
        agent = self._make_agent()
        plugin = self._make_plugin(agent)
        state: dict[str, Any] = {}
        ctx = self._make_ctx(plugin_state=state)

        await plugin.on_pre_task(ctx)
        assert plugin._dawp_start_handler._plugin_state is state

        await plugin.on_post_task(ctx, result={})

        assert plugin._dawp_start_handler._plugin_state is None

    @pytest.mark.asyncio
    async def test_injected_handler_callable_returns_accepted(self):
        """End-to-end: handler injected by plugin can execute correctly.

        on_pre_task resets dawp.workflow to None (no document_path configured),
        so we set it afterwards to simulate a successfully compiled workflow.
        """
        wf = _workflow("e2e-wf")
        agent = self._make_agent()
        plugin = self._make_plugin(agent)
        state: dict[str, Any] = {}
        ctx = self._make_ctx(plugin_state=state)

        await plugin.on_pre_task(ctx)

        # Simulate a compiled workflow being present (as done by document_loader)
        state["dawp.workflow"] = wf

        handler = agent._tool_instances["dawp_start"]
        result = await handler.run_async(workflow_source="static")
        assert result["status"] == "accepted"
        assert result["workflow_id"] == "e2e-wf"
        assert len(state["dawp.pending"]) == 1
        assert state["dawp.pending"][0].drain_mode == "inline"
