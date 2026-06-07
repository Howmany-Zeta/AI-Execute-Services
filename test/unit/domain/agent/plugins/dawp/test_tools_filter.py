"""
Unit tests for D1-05 — tools_filter.py (§4.5, D10).

Covers:
- DAWP_EXCLUDED_TOOL_NAMES contains dawp_start, dawp_run, dawp_publish_workflow
- resolve_tools_for_scope: kind=dawp removes excluded tools (dicts and instances)
- resolve_tools_for_scope: kind=main returns list unchanged (no copy)
- resolve_tools_for_scope: empty list returns empty
- resolve_tools_for_scope: non-excluded tools survive filtering
- check_dawp_nesting_guard: returns None when no active run
- check_dawp_nesting_guard: returns rejection dict when active_run_id is set
- Integration: nested runner passes filtered schemas to LLM kwargs
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiecs.domain.agent.plugins.dawp.loop_scope import LoopScope
from aiecs.domain.agent.plugins.dawp.tools_filter import (
    DAWP_EXCLUDED_TOOL_NAMES,
    check_dawp_nesting_guard,
    resolve_tools_for_scope,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MAIN_SCOPE = LoopScope(kind="main")
_DAWP_SCOPE = LoopScope(kind="dawp", run_id="run-abc", workflow_id="wf", step_id="s0")


def _schema(name: str) -> dict[str, Any]:
    """Minimal OpenAI function schema dict."""
    return {"name": name, "description": f"{name} tool", "parameters": {}}


def _instance(name: str) -> SimpleNamespace:
    """Minimal tool instance with .name attribute."""
    return SimpleNamespace(name=name)


# ---------------------------------------------------------------------------
# DAWP_EXCLUDED_TOOL_NAMES
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExcludedNames:
    def test_dawp_start_excluded(self) -> None:
        assert "dawp_start" in DAWP_EXCLUDED_TOOL_NAMES

    def test_dawp_run_excluded(self) -> None:
        assert "dawp_run" in DAWP_EXCLUDED_TOOL_NAMES

    def test_dawp_publish_workflow_excluded(self) -> None:
        assert "dawp_publish_workflow" in DAWP_EXCLUDED_TOOL_NAMES

    def test_excluded_names_is_frozenset(self) -> None:
        assert isinstance(DAWP_EXCLUDED_TOOL_NAMES, frozenset)


# ---------------------------------------------------------------------------
# resolve_tools_for_scope — schema dicts
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestResolveToolsSchemas:
    """resolve_tools_for_scope with raw schema dicts (OpenAI function format)."""

    def test_main_scope_returns_all_schemas(self) -> None:
        schemas = [_schema("search"), _schema("dawp_start")]
        result = resolve_tools_for_scope(schemas, _MAIN_SCOPE)
        assert result is schemas  # same object, no copy

    def test_dawp_scope_removes_dawp_start(self) -> None:
        schemas = [_schema("search"), _schema("dawp_start")]
        result = resolve_tools_for_scope(schemas, _DAWP_SCOPE)
        names = [s["name"] for s in result]
        assert "dawp_start" not in names
        assert "search" in names

    def test_dawp_scope_removes_dawp_run(self) -> None:
        schemas = [_schema("file_read"), _schema("dawp_run")]
        result = resolve_tools_for_scope(schemas, _DAWP_SCOPE)
        names = [s["name"] for s in result]
        assert "dawp_run" not in names
        assert "file_read" in names

    def test_dawp_scope_removes_dawp_publish_workflow(self) -> None:
        schemas = [_schema("dawp_publish_workflow"), _schema("code_exec")]
        result = resolve_tools_for_scope(schemas, _DAWP_SCOPE)
        names = [s["name"] for s in result]
        assert "dawp_publish_workflow" not in names
        assert "code_exec" in names

    def test_dawp_scope_removes_all_excluded(self) -> None:
        schemas = [
            _schema("dawp_start"),
            _schema("dawp_run"),
            _schema("dawp_publish_workflow"),
            _schema("search"),
        ]
        result = resolve_tools_for_scope(schemas, _DAWP_SCOPE)
        names = [s["name"] for s in result]
        assert names == ["search"]

    def test_empty_list_returns_empty(self) -> None:
        assert resolve_tools_for_scope([], _DAWP_SCOPE) == []
        assert resolve_tools_for_scope([], _MAIN_SCOPE) == []

    def test_no_excluded_tools_all_pass(self) -> None:
        schemas = [_schema("search"), _schema("file_read"), _schema("code_exec")]
        result = resolve_tools_for_scope(schemas, _DAWP_SCOPE)
        assert len(result) == 3

    def test_dawp_scope_does_not_mutate_original(self) -> None:
        schemas = [_schema("search"), _schema("dawp_start")]
        original_len = len(schemas)
        resolve_tools_for_scope(schemas, _DAWP_SCOPE)
        assert len(schemas) == original_len  # original untouched


# ---------------------------------------------------------------------------
# resolve_tools_for_scope — tool instances
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestResolveToolsInstances:
    """resolve_tools_for_scope with tool instances (.name attribute)."""

    def test_main_scope_returns_all_instances(self) -> None:
        tools = [_instance("search"), _instance("dawp_start")]
        result = resolve_tools_for_scope(tools, _MAIN_SCOPE)
        assert result is tools

    def test_dawp_scope_removes_excluded_instances(self) -> None:
        tools = [
            _instance("search"),
            _instance("dawp_start"),
            _instance("dawp_run"),
        ]
        result = resolve_tools_for_scope(tools, _DAWP_SCOPE)
        names = [t.name for t in result]
        assert names == ["search"]

    def test_dawp_scope_keeps_non_excluded_instances(self) -> None:
        tools = [_instance("search"), _instance("file_read")]
        result = resolve_tools_for_scope(tools, _DAWP_SCOPE)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# check_dawp_nesting_guard
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCheckDawpNestingGuard:
    def test_returns_none_when_no_active_run(self) -> None:
        state: dict[str, Any] = {}
        assert check_dawp_nesting_guard(state) is None

    def test_returns_none_when_active_run_id_falsy(self) -> None:
        # None and "" are both falsy — guard must not fire
        assert check_dawp_nesting_guard({"dawp.active_run_id": None}) is None
        assert check_dawp_nesting_guard({"dawp.active_run_id": ""}) is None

    def test_returns_rejection_when_active_run_id_set(self) -> None:
        state = {"dawp.active_run_id": "run-xyz"}
        result = check_dawp_nesting_guard(state)
        assert result is not None
        assert result["status"] == "rejected"
        assert "D10" in result["reason"] or "DAWP run" in result["reason"]
        assert result["active_run_id"] == "run-xyz"

    def test_rejection_includes_active_run_id(self) -> None:
        state = {"dawp.active_run_id": "run-nested-test"}
        result = check_dawp_nesting_guard(state)
        assert result is not None
        assert result["active_run_id"] == "run-nested-test"

    def test_other_state_keys_do_not_affect_guard(self) -> None:
        state = {"task.response_index": 3, "task.iteration_budget": object()}
        assert check_dawp_nesting_guard(state) is None


# ---------------------------------------------------------------------------
# Integration: nested runner passes filtered schemas to LLM
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestNestedRunnerFilterIntegration:
    """Verify that _run_tool_loop_nested_streaming passes filtered schemas to the LLM."""

    async def test_excluded_tool_absent_from_llm_kwargs(self) -> None:
        """dawp_start schema must not appear in kwargs passed to stream_text."""
        from aiecs.domain.agent.hybrid_agent import HybridAgent
        from aiecs.domain.agent.models import AgentConfiguration
        from aiecs.domain.agent.plugins.dawp.budget import TaskIterationBudget
        from aiecs.domain.agent.plugins.models import PluginConfig
        from aiecs.llm import BaseLLMClient, LLMMessage, LLMResponse
        from aiecs.llm.clients.openai_compatible_mixin import StreamChunk

        # Capture kwargs passed to stream_text
        captured_kwargs: list[dict[str, Any]] = []

        class CapturingLLM(BaseLLMClient):
            def __init__(self) -> None:
                super().__init__(provider_name="openai")

            async def generate_text(self, **kwargs: Any) -> LLMResponse:
                return LLMResponse(content="done", provider="openai", model="t", tokens_used=1)

            async def stream_text(self, **kwargs: Any):
                captured_kwargs.append(kwargs)
                yield StreamChunk(type="token", content="DAWP step done.")

            async def close(self) -> None:
                pass

        config = AgentConfiguration(
            goal="filter test",
            llm_model="test-model",
            plugins=[
                PluginConfig(name="memory", enabled=False),
                PluginConfig(name="skill", enabled=False),
            ],
        )
        mock_tool = MagicMock()
        mock_tool.name = "mock_tool"
        mock_tool.description = "A mock tool"
        mock_tool._schemas = {"query": MagicMock()}
        mock_tool.run_async = AsyncMock(return_value="result")

        with patch("aiecs.tools.get_tool", return_value=mock_tool):
            agent = HybridAgent(
                agent_id="filter-test",
                name="Filter Test",
                llm_client=CapturingLLM(),
                tools=["mock_tool"],
                config=config,
                max_iterations=5,
            )
            await agent.initialize()

        # Inject a dawp_start schema into the agent's tool schemas
        agent._tool_schemas.append(_schema("dawp_start"))
        agent._tool_schemas.append(_schema("other_tool"))

        plugin_ctx = agent._make_plugin_context(
            task={"description": "filter test"},
            context={},
            task_description="filter test",
        )
        scope = LoopScope(
            kind="dawp", run_id="run-filter", workflow_id="wf", step_id="s0"
        )
        budget = TaskIterationBudget(limit=5)
        messages = [LLMMessage(role="user", content="Step prompt")]

        with patch("aiecs.tools.get_tool", return_value=mock_tool):
            async for _ in agent._run_tool_loop_nested_streaming(
                messages, {}, plugin_ctx,
                scope=scope,
                budget=budget,
                step_iteration_cap=1,
            ):
                pass

        assert captured_kwargs, "stream_text was never called"
        tools_in_call = captured_kwargs[0].get("tools", [])
        tool_names_sent = [t["function"]["name"] for t in tools_in_call]
        assert "dawp_start" not in tool_names_sent, (
            f"dawp_start must be filtered out; got {tool_names_sent}"
        )
        assert "other_tool" in tool_names_sent or "mock_tool" in tool_names_sent

    async def test_main_scope_sends_all_schemas(self) -> None:
        """For kind=main, ALL schemas (including dawp_start) are forwarded to LLM."""
        from aiecs.domain.agent.hybrid_agent import HybridAgent
        from aiecs.domain.agent.models import AgentConfiguration
        from aiecs.domain.agent.plugins.dawp.budget import TaskIterationBudget
        from aiecs.domain.agent.plugins.models import PluginConfig
        from aiecs.llm import BaseLLMClient, LLMMessage, LLMResponse
        from aiecs.llm.clients.openai_compatible_mixin import StreamChunk

        captured_kwargs: list[dict[str, Any]] = []

        class CapturingLLM(BaseLLMClient):
            def __init__(self) -> None:
                super().__init__(provider_name="openai")

            async def generate_text(self, **kwargs: Any) -> LLMResponse:
                return LLMResponse(content="done", provider="openai", model="t", tokens_used=1)

            async def stream_text(self, **kwargs: Any):
                captured_kwargs.append(kwargs)
                yield StreamChunk(type="token", content="done.")

            async def close(self) -> None:
                pass

        config = AgentConfiguration(
            goal="main scope test",
            llm_model="test-model",
            plugins=[
                PluginConfig(name="memory", enabled=False),
                PluginConfig(name="skill", enabled=False),
            ],
        )
        mock_tool = MagicMock()
        mock_tool.name = "mock_tool"
        mock_tool.description = "mock"
        mock_tool._schemas = {"query": MagicMock()}
        mock_tool.run_async = AsyncMock(return_value="result")

        with patch("aiecs.tools.get_tool", return_value=mock_tool):
            agent = HybridAgent(
                agent_id="main-scope-test",
                name="Main Scope Test",
                llm_client=CapturingLLM(),
                tools=["mock_tool"],
                config=config,
                max_iterations=5,
            )
            await agent.initialize()

        agent._tool_schemas.append(_schema("dawp_start"))

        plugin_ctx = agent._make_plugin_context(
            task={"description": "main scope"},
            context={},
            task_description="main scope",
        )
        # Use main scope (kind=main)
        scope = LoopScope(kind="dawp", run_id="run-filter-main", workflow_id="wf", step_id="s0")
        main_scope = LoopScope(kind="main")

        budget = TaskIterationBudget(limit=5)
        messages = [LLMMessage(role="user", content="prompt")]

        # Directly test _build_tool_loop_llm_kwargs with no override (main path)
        kwargs = agent._build_tool_loop_llm_kwargs(messages, {}, streaming=True)
        tool_names = [t["function"]["name"] for t in kwargs.get("tools", [])]
        # dawp_start is in the schema list because no filter applied
        assert "dawp_start" in tool_names
