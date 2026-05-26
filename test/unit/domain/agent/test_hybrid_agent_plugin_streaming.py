"""
HybridAgent execute_task_streaming plugin phase tests (P2-11, §8.5).
"""

from __future__ import annotations

from typing import Any, ClassVar
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiecs.domain.agent.hybrid_agent import HybridAgent
from aiecs.domain.agent.models import AgentConfiguration
from aiecs.domain.agent.plugins.base import BaseAgentPlugin
from aiecs.domain.agent.plugins.context import AgentPluginContext, PluginShortCircuitResult
from aiecs.domain.agent.plugins.models import PluginConfig, PluginMetadata, PluginPhase
from aiecs.domain.agent.plugins.registry import PluginRegistry
from aiecs.llm import BaseLLMClient, LLMResponse


class ShortCircuitStreamingPlugin(BaseAgentPlugin):
    """PRE_MAIN_LOOP short-circuit for streaming tests."""

    metadata: ClassVar[PluginMetadata] = PluginMetadata(
        name="short",
        version="1.0.0",
        description="streaming short-circuit",
        priority=5,
    )

    async def on_pre_main_loop(self, ctx: AgentPluginContext) -> PluginShortCircuitResult:
        return PluginShortCircuitResult(
            result={
                "final_response": "stream short-circuit",
                "steps": [],
                "iterations": 0,
                "tool_calls_count": 0,
                "total_tokens": 0,
            },
            source_plugin_id="short@registry",
        )


class PostTaskMarkerStreamingPlugin(BaseAgentPlugin):
    """Marks POST_TASK execution via plugin_state."""

    metadata: ClassVar[PluginMetadata] = PluginMetadata(
        name="post_marker",
        version="1.0.0",
        description="post-task marker",
        priority=200,
    )

    async def on_post_task(self, ctx: AgentPluginContext, result: dict[str, Any]) -> dict[str, Any]:
        ctx.plugin_state["post_task_ran"] = True
        return result


class MockStreamLLM(BaseLLMClient):
    def __init__(self) -> None:
        super().__init__(provider_name="openai")

    async def generate_text(self, *args: Any, **kwargs: Any) -> LLMResponse:
        return LLMResponse(content="unused", provider="openai", model="test", tokens_used=1)

    async def stream_text(self, *args: Any, **kwargs: Any):
        yield "Done."

    async def close(self) -> None:
        pass


def _registry_with_short_and_post() -> PluginRegistry:
    registry = PluginRegistry()
    registry.register("short", ShortCircuitStreamingPlugin, origin="registry")
    registry.register("post_marker", PostTaskMarkerStreamingPlugin, origin="registry")
    return registry


@pytest.fixture
async def streaming_agent() -> HybridAgent:
    config = AgentConfiguration(
        goal="Streaming plugin test",
        llm_model="test-model",
        plugins=[
            PluginConfig(name="tool", enabled=False),
            PluginConfig(name="skill", enabled=False),
            PluginConfig(name="memory", enabled=True),
            PluginConfig(name="short", enabled=False),
            PluginConfig(name="post_marker", enabled=False),
        ],
    )
    agent = HybridAgent(
        agent_id="streaming-plugin-test",
        name="Streaming Plugin Test",
        llm_client=MockStreamLLM(),
        tools=[],
        config=config,
        max_iterations=3,
    )
    await agent.initialize()
    return agent


@pytest.mark.unit
@pytest.mark.asyncio
class TestHybridAgentPluginStreaming:
    """Plugin framework events during execute_task_streaming."""

    async def test_emits_plugin_phase_and_hook_events(self, streaming_agent: HybridAgent) -> None:
        events: list[dict[str, Any]] = []
        async for event in streaming_agent.execute_task_streaming(
            {"description": "plugin streaming test"},
            {},
        ):
            events.append(event)

        phase_started = [e for e in events if e.get("type") == "plugin_phase_started"]
        hook_completed = [e for e in events if e.get("type") == "plugin_hook_completed"]
        config_resolved = [e for e in events if e.get("type") == "plugin_config_resolved"]

        assert len(phase_started) >= 1
        assert len(hook_completed) >= 1
        assert {e.get("phase") for e in phase_started} >= {PluginPhase.PRE_TASK.value}
        assert any(e.get("type") == "result" for e in events)
        assert len(config_resolved) == 1

    async def test_short_circuit_yields_result_and_runs_post_task(self) -> None:
        registry = _registry_with_short_and_post()
        config = AgentConfiguration(
            goal="Short-circuit streaming",
            llm_model="test-model",
            plugins=[
                PluginConfig(name="tool", enabled=False),
                PluginConfig(name="skill", enabled=False),
                PluginConfig(name="memory", enabled=False),
                PluginConfig(name="short", enabled=True),
                PluginConfig(name="post_marker", enabled=True),
            ],
        )
        agent = HybridAgent(
            agent_id="streaming-short-circuit",
            name="Streaming Short",
            llm_client=MockStreamLLM(),
            tools=[],
            config=config,
            plugin_registry=registry,
        )
        await agent.initialize()

        tool_loop_mock = AsyncMock(side_effect=AssertionError("streaming tool loop must not run"))

        with patch.object(
            agent,
            "_tool_loop_streaming_with_plugins",
            new=tool_loop_mock,
        ):
            events = []
            async for event in agent.execute_task_streaming(
                {"description": "short stream"},
                {},
            ):
                events.append(event)

        tool_loop_mock.assert_not_called()
        result_events = [e for e in events if e.get("type") == "result"]
        assert len(result_events) == 1
        assert result_events[0]["output"] == "stream short-circuit"
        post_phases = [
            e for e in events if e.get("type") == "plugin_phase_started" and e.get("phase") == PluginPhase.POST_TASK.value
        ]
        assert len(post_phases) >= 1
