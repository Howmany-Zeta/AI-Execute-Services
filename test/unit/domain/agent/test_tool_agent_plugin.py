"""
ToolAgent plugin integration tests (P3-03, §7.3 LLM FC mode).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from aiecs.domain.agent.models import AgentConfiguration
from aiecs.domain.agent.plugins.builtin.tool_plugin import filter_tool_schemas
from aiecs.domain.agent.plugins.models import PluginConfig, PluginPhase
from aiecs.domain.agent.plugins.testing.normalize import (
    normalize_execute_task_response,
    normalize_messages,
    normalize_tool_schema_names,
)
from aiecs.domain.agent.tool_agent import ToolAgent
from aiecs.llm import BaseLLMClient, LLMMessage, LLMResponse
from aiecs.tools.base_tool import BaseTool

_REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURES_DIR = _REPO_ROOT / "tests" / "fixtures" / "plugin_parity"


class ParityStubTool(BaseTool):
    async def run_async(self, op: str = "run", **kwargs: Any) -> Any:
        return {"status": "ok", "operation": op, **kwargs}


class ParityMockFCClient(BaseLLMClient):
    def __init__(
        self,
        *,
        content: str = "I'll search for that.",
        tool_calls: list[dict[str, Any]] | None = None,
    ):
        super().__init__(provider_name="openai")
        self._content = content
        self._tool_calls = tool_calls or []
        self.last_tools: list[dict[str, Any]] = []

    async def generate_text(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        tools: list[dict] | None = None,
        tool_choice: str | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        self.last_tools = tools or []
        response = LLMResponse(
            content=self._content,
            provider="openai",
            model=model or "parity-mock",
            tokens_used=50,
        )
        if self._tool_calls:
            response.tool_calls = self._tool_calls
        return response

    async def stream_text(self, *args: Any, **kwargs: Any):
        yield self._content

    async def close(self) -> None:
        pass


def _load_fixture(name: str) -> dict[str, Any]:
    return yaml.safe_load((FIXTURES_DIR / name).read_text(encoding="utf-8"))


async def _tool_agent_from_fixture(
    spec: dict[str, Any],
    *,
    client: ParityMockFCClient | None = None,
    config_overrides: dict[str, Any] | None = None,
) -> tuple[ToolAgent, dict[str, Any], dict[str, Any]]:
    raw_config = dict(spec.get("config") or {})
    if config_overrides:
        raw_config.update(config_overrides)
    config = AgentConfiguration(**raw_config)
    tools = {"parity_search": ParityStubTool(tool_name="parity_search")}
    task = spec.get("task") or {"description": "Parity test task"}
    context = dict(spec.get("context") or {})

    capture = spec.get("capture") or {}
    client = client or ParityMockFCClient(
        content=str(capture.get("mock_final_output", "I'll search for that.")),
        tool_calls=capture.get("mock_tool_calls"),
    )

    agent = ToolAgent(
        agent_id="tool-plugin-test",
        name="Tool Plugin Test",
        llm_client=client,
        tools=tools,
        config=config,
    )
    await agent.initialize()
    return agent, task, context


@pytest.mark.unit
@pytest.mark.asyncio
class TestToolAgentPluginExecute:
    async def test_llm_fc_mode_matches_p3_00_golden(self) -> None:
        spec = _load_fixture("tool_llm_fc_mode.yaml")
        expect = spec["expect"]
        agent, task, context = await _tool_agent_from_fixture(spec)

        task_description = task["description"]
        plugin_ctx = agent._make_plugin_context(task, context, task_description)
        agent._apply_task_plugin_configs(task=task, context=context)
        await agent._plugin_manager.run_phase(PluginPhase.PRE_TASK, ctx=plugin_ctx)
        await agent._plugin_manager.run_phase(PluginPhase.PRE_MAIN_LOOP, ctx=plugin_ctx)
        messages = await agent._build_messages_via_plugins(
            task_description,
            context,
            plugin_ctx,
        )

        assert normalize_messages(messages) == expect["messages_normalized"]
        assert normalize_tool_schema_names(agent._tool_schemas) == expect["tool_schema_names"]

        result = await agent.execute_task(task, context)
        shell = normalize_execute_task_response(result, extra_fields=frozenset({"tool_calls_count"}))
        assert shell == expect["execute_task_response"]

    async def test_pre_main_loop_filters_schemas_for_llm_fc(self) -> None:
        spec = _load_fixture("tool_llm_fc_mode.yaml")
        agent, task, context = await _tool_agent_from_fixture(
            spec,
            config_overrides={
                "plugins": [
                    PluginConfig(
                        name="tool",
                        enabled=True,
                        options={"allowed_tools": ["parity_search"]},
                    ),
                ],
            },
        )
        assert len(agent._tool_schemas) == 1

        agent._tool_schemas = [
            {"name": "parity_search"},
            {"name": "other_tool"},
        ]
        plugin_ctx = agent._make_plugin_context(task, context, task["description"])
        await agent._plugin_manager.run_phase(PluginPhase.PRE_MAIN_LOOP, ctx=plugin_ctx)

        assert normalize_tool_schema_names(agent._tool_schemas) == ["parity_search"]

        client = agent.llm_client
        assert isinstance(client, ParityMockFCClient)
        await agent._execute_task_with_plugins(task, context)
        assert len(client.last_tools) == 1
        assert client.last_tools[0]["function"]["name"] == "parity_search"

    async def test_direct_invoke_regression(self) -> None:
        """Direct mode: PRE_TASK/POST_TASK only, no BUILD_MESSAGES (documented P3-03 behavior)."""
        spec = _load_fixture("tool_direct_invoke.yaml")
        raw_config = dict(spec.get("config") or {})
        config = AgentConfiguration(**raw_config)
        agent = ToolAgent(
            agent_id="tool-direct-test",
            name="Tool Direct Test",
            llm_client=ParityMockFCClient(),
            tools={"parity_search": ParityStubTool(tool_name="parity_search")},
            config=config,
        )
        await agent.initialize()

        phases: list[str] = []
        original = agent._plugin_manager.run_phase

        async def tracking(phase: PluginPhase, **kwargs: Any) -> Any:
            phases.append(phase.value)
            return await original(phase, **kwargs)

        agent._plugin_manager.run_phase = tracking  # type: ignore[method-assign]

        result = await agent.execute_task(spec["task"], spec.get("context") or {})

        assert result["success"] is True
        assert result["tool_used"] == "parity_search"
        assert result["output"]["status"] == "ok"
        assert "build_messages" not in phases
        assert phases == ["pre_task", "post_task"]

    async def test_filter_tool_schemas_helper(self) -> None:
        schemas = [{"name": "parity_search"}, {"name": "other_tool"}]
        filtered = filter_tool_schemas(schemas, ["parity_search"])
        assert [s["name"] for s in filtered] == ["parity_search"]
