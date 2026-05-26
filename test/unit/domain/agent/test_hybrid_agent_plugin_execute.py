"""
HybridAgent execute_task plugin kernel/shell tests (P2-09, §8.2, §4.4).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
import yaml

from aiecs.domain.agent.hybrid_agent import HybridAgent
from aiecs.domain.agent.models import AgentConfiguration
from aiecs.domain.agent.plugins.base import BaseAgentPlugin
from aiecs.domain.agent.plugins.context import AgentPluginContext, PluginShortCircuitResult
from aiecs.domain.agent.plugins.models import PluginConfig, PluginMetadata, PluginPhase
from aiecs.domain.agent.plugins.registry import PluginRegistry
from aiecs.domain.agent.plugins.testing.normalize import normalize_execute_task_response
from aiecs.llm import BaseLLMClient, LLMMessage, LLMResponse
from aiecs.tools.base_tool import BaseTool

_REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURES_DIR = _REPO_ROOT / "tests" / "fixtures" / "plugin_parity"


class ParityStubTool(BaseTool):
    async def run_async(self, operation: str, **kwargs: Any) -> dict[str, Any]:
        return {"status": "ok", "operation": operation}


class MockLLMClientFunctionCalling(BaseLLMClient):
    def __init__(self, content: str = "Parity baseline final response.") -> None:
        super().__init__(provider_name="openai")
        self._content = content
        self.call_count = 0

    async def generate_text(self, messages: list[LLMMessage], **kwargs: Any) -> LLMResponse:
        self.call_count += 1
        return LLMResponse(
            content=self._content,
            provider="openai",
            model=kwargs.get("model") or "parity-mock",
            tokens_used=42,
        )

    async def stream_text(self, *args: Any, **kwargs: Any):
        yield self._content

    async def close(self) -> None:
        pass


class ShortCircuitPlugin(BaseAgentPlugin):
    """PRE_MAIN_LOOP short-circuit for execute_task kernel tests."""

    metadata = PluginMetadata(
        name="short",
        version="1.0.0",
        description="short-circuit test plugin",
        priority=5,
    )

    async def on_pre_main_loop(self, ctx: AgentPluginContext) -> PluginShortCircuitResult:
        return PluginShortCircuitResult(
            result={
                "final_response": "short-circuited output",
                "steps": [{"type": "thought", "content": "short", "iteration": 0}],
                "iterations": 0,
                "tool_calls_count": 0,
                "total_tokens": 0,
            },
            source_plugin_id="short@registry",
            reason="test_short_circuit",
        )


def _load_fixture(name: str) -> dict[str, Any]:
    return yaml.safe_load((FIXTURES_DIR / name).read_text(encoding="utf-8"))


def _build_registry_with_short_plugin() -> PluginRegistry:
    registry = PluginRegistry()
    registry.register("short", ShortCircuitPlugin, origin="registry")
    return registry


@pytest.mark.unit
@pytest.mark.asyncio
class TestHybridAgentPluginExecute:
    """execute_task outer shell and plugin phase wiring."""

    async def test_outer_shell_parity_without_short_circuit(self) -> None:
        spec = _load_fixture("hybrid_baseline.yaml")
        raw_config = dict(spec.get("config") or {})
        raw_config["plugins"] = [
            PluginConfig(name="memory", enabled=False),
            PluginConfig(name="skill", enabled=False),
        ]
        config = AgentConfiguration(**raw_config)
        tools = {"parity_search": ParityStubTool(tool_name="parity_search")}
        capture = spec.get("capture") or {}
        client = MockLLMClientFunctionCalling(
            content=capture.get("mock_final_output", "Parity baseline final response.")
        )

        agent = HybridAgent(
            agent_id="plugin-execute-test",
            name="Plugin Execute Test",
            llm_client=client,
            tools=tools,
            config=config,
            max_iterations=3,
        )
        await agent.initialize()

        task = spec.get("task") or {"description": "Find latest news about AI"}
        context = dict(spec.get("context") or {})
        result = await agent.execute_task(task, context)

        assert "execution_time" in result
        assert result["timestamp"]
        assert result["success"] is True
        assert normalize_execute_task_response(result) == spec["expect"]["execute_task_response"]
        assert client.call_count >= 1

    async def test_pre_main_loop_short_circuit_skips_tool_loop_post_task_runs(self) -> None:
        registry = _build_registry_with_short_plugin()
        config = AgentConfiguration(
            goal="Short-circuit test",
            llm_model="parity-mock",
            plugins=[
                PluginConfig(name="tool", enabled=False),
                PluginConfig(name="skill", enabled=False),
                PluginConfig(name="memory", enabled=False),
                PluginConfig(name="short", enabled=True),
            ],
        )
        client = MockLLMClientFunctionCalling(content="should not be called")

        agent = HybridAgent(
            agent_id="plugin-short-circuit-test",
            name="Short Circuit Test",
            llm_client=client,
            tools=[],
            config=config,
            max_iterations=3,
            plugin_registry=registry,
        )
        await agent.initialize()

        tool_loop_mock = AsyncMock(side_effect=AssertionError("tool loop must not run"))
        phases_run: list[PluginPhase] = []
        original_run_phase = agent._plugin_manager.run_phase

        async def tracking_run_phase(phase: PluginPhase, **kwargs: Any) -> Any:
            phases_run.append(phase)
            return await original_run_phase(phase, **kwargs)

        agent._tool_loop_with_plugins = tool_loop_mock  # type: ignore[method-assign]

        with patch.object(agent._plugin_manager, "run_phase", side_effect=tracking_run_phase):
            result = await agent.execute_task(
                {"description": "Any task"},
                {},
            )

        tool_loop_mock.assert_not_called()
        assert PluginPhase.PRE_TASK in phases_run
        assert PluginPhase.PRE_MAIN_LOOP in phases_run
        assert PluginPhase.POST_TASK in phases_run
        assert result["output"] == "short-circuited output"
        assert result["success"] is True
        assert client.call_count == 0

    async def test_format_passthrough_when_output_present(self) -> None:
        agent = HybridAgent(
            agent_id="format-passthrough",
            name="Format",
            llm_client=MockLLMClientFunctionCalling(),
            tools=[],
            config=AgentConfiguration(goal="test"),
        )
        inner = {
            "success": True,
            "output": "already formatted",
            "reasoning_steps": [],
            "iterations": 0,
        }
        outer = agent._format_execute_task_response(inner, execution_time=1.5)
        assert outer["output"] == "already formatted"
        assert outer["execution_time"] == 1.5
        assert "final_response" not in outer or outer.get("output") == "already formatted"
