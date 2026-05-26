"""
HybridAgent _tool_loop_with_plugins iteration hook tests (P2-10, §8.4).
"""

from __future__ import annotations

from typing import Any, ClassVar
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiecs.domain.agent.hybrid_agent import HybridAgent
from aiecs.domain.agent.models import AgentConfiguration
from aiecs.domain.agent.plugins.base import BaseAgentPlugin
from aiecs.domain.agent.plugins.context import AgentPluginContext
from aiecs.domain.agent.plugins.models import PluginConfig, PluginMetadata, PluginPhase
from aiecs.domain.agent.plugins.registry import PluginRegistry
from aiecs.llm import BaseLLMClient, LLMMessage, LLMResponse

PLUGIN_STATE_AUDIT_KEY = "audit.iteration_steps"


class AuditPlugin(BaseAgentPlugin):
    """Records iteration step payloads on ON_ITERATION_END (§8.4)."""

    metadata: ClassVar[PluginMetadata] = PluginMetadata(
        name="audit",
        version="1.0.0",
        description="iteration audit plugin",
        priority=10,
    )

    async def on_iteration_end(
        self,
        ctx: AgentPluginContext,
        iteration: int,
        step: dict[str, Any],
    ) -> None:
        audit = ctx.plugin_state.setdefault(PLUGIN_STATE_AUDIT_KEY, [])
        audit.append(
            {
                "iteration": iteration,
                "kind": step.get("kind"),
                "step_count": len(step.get("steps") or []),
            }
        )
        return None


class MockLLMClientFunctionCalling(BaseLLMClient):
    def __init__(self, responses: list[dict[str, Any]] | None = None) -> None:
        super().__init__(provider_name="openai")
        self.responses = responses or [{"content": "Done.", "tool_calls": None}]
        self.call_count = 0

    async def generate_text(self, messages: list[LLMMessage], **kwargs: Any) -> LLMResponse:
        self.call_count += 1
        payload = (
            self.responses[self.call_count - 1]
            if self.call_count <= len(self.responses)
            else self.responses[-1]
        )
        resp = LLMResponse(
            content=payload.get("content", ""),
            provider="openai",
            model="test",
            tokens_used=10,
        )
        if payload.get("tool_calls") is not None:
            setattr(resp, "tool_calls", payload["tool_calls"])
        return resp

    async def stream_text(self, *args: Any, **kwargs: Any):
        yield "x"

    async def close(self) -> None:
        pass


def create_mock_tool() -> MagicMock:
    mock_tool = MagicMock()
    mock_tool.name = "mock_tool"
    mock_tool.description = "A mock tool"
    mock_tool._schemas = {"query": MagicMock()}

    async def mock_run_async(operation=None, **kwargs: Any) -> str:
        return f"Result for {operation}={kwargs}"

    mock_tool.run_async = AsyncMock(side_effect=mock_run_async)
    return mock_tool


@pytest.fixture
async def hybrid_with_audit_plugin() -> HybridAgent:
    registry = PluginRegistry.default()
    registry.register("audit", AuditPlugin, origin="registry")

    config = AgentConfiguration(
        goal="Tool loop plugin test",
        llm_model="test-model",
        plugins=[
            PluginConfig(name="memory", enabled=False),
            PluginConfig(name="skill", enabled=False),
            PluginConfig(name="audit", enabled=True),
        ],
    )
    mock_tool = create_mock_tool()
    client = MockLLMClientFunctionCalling()

    with patch("aiecs.tools.get_tool", return_value=mock_tool):
        agent = HybridAgent(
            agent_id="hybrid-tool-loop-plugin-test",
            name="Hybrid Tool Loop Plugin Test",
            llm_client=client,
            tools=["mock_tool"],
            config=config,
            max_iterations=5,
            plugin_registry=registry,
        )
        await agent.initialize()
        yield agent


@pytest.mark.unit
@pytest.mark.asyncio
class TestHybridToolLoopWithPlugins:
    """_tool_loop_with_plugins iteration hooks and return shape."""

    async def test_audit_plugin_records_steps_on_iteration_end(
        self, hybrid_with_audit_plugin: HybridAgent
    ) -> None:
        agent = hybrid_with_audit_plugin
        agent.llm_client.responses = [  # type: ignore[attr-defined]
            {
                "content": "Using tool.",
                "tool_calls": [
                    {
                        "id": "call_0",
                        "type": "function",
                        "function": {"name": "mock_tool", "arguments": "{}"},
                    }
                ],
            },
            {"content": "Final answer.", "tool_calls": None},
        ]

        plugin_ctx = agent._make_plugin_context(
            task={"description": "audit test"},
            context={},
            task_description="audit test",
        )

        result = await agent._tool_loop_with_plugins("audit test", {}, plugin_ctx)

        audit = plugin_ctx.plugin_state.get(PLUGIN_STATE_AUDIT_KEY)
        assert audit is not None
        assert len(audit) == 2
        assert audit[0]["kind"] == "continue"
        assert audit[1]["kind"] == "final"
        assert result["final_response"] == "Final answer."
        assert result["iterations"] == 2
        assert result["tool_calls_count"] == 1

    async def test_return_dict_has_legacy_tool_loop_keys(
        self, hybrid_with_audit_plugin: HybridAgent
    ) -> None:
        agent = hybrid_with_audit_plugin
        plugin_ctx = agent._make_plugin_context(
            task={"description": "keys test"},
            context={},
            task_description="keys test",
        )

        result = await agent._tool_loop_with_plugins("keys test", {}, plugin_ctx)

        for key in (
            "final_response",
            "steps",
            "iterations",
            "tool_calls_count",
            "total_tokens",
        ):
            assert key in result, f"missing key: {key}"

    async def test_run_phase_invokes_iteration_hooks(self, hybrid_with_audit_plugin: HybridAgent) -> None:
        agent = hybrid_with_audit_plugin
        plugin_ctx = agent._make_plugin_context(
            task={"description": "phase test"},
            context={},
            task_description="phase test",
        )
        phases: list[PluginPhase] = []
        original = agent._plugin_manager.run_phase

        async def track(phase: PluginPhase, **kwargs: Any) -> Any:
            phases.append(phase)
            return await original(phase, **kwargs)

        agent._plugin_manager.run_phase = track  # type: ignore[method-assign]

        await agent._tool_loop_with_plugins("phase test", {}, plugin_ctx)

        assert PluginPhase.ON_ITERATION_START in phases
        assert PluginPhase.ON_ITERATION_END in phases
