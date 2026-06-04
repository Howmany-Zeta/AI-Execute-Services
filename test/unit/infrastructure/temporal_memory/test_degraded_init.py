"""Degraded temporal memory init (TM-069, scheme B in TemporalMemoryPlugin)."""

from __future__ import annotations

from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest

from aiecs.config.config import Settings
from aiecs.domain.agent import HybridAgent
from aiecs.domain.agent.models import AgentConfiguration
from aiecs.domain.agent.plugins.builtin.temporal_memory_plugin import TemporalMemoryPlugin
from aiecs.domain.agent.plugins.context import AgentPluginContext
from aiecs.domain.agent.plugins.models import PluginConfig
from aiecs.infrastructure.temporal_memory import NoOpTemporalMemoryStore
from aiecs.llm import BaseLLMClient, LLMResponse


class _MockLLM(BaseLLMClient):
    def __init__(self) -> None:
        super().__init__(provider_name="openai")

    async def generate_text(self, *args: Any, **kwargs: Any) -> LLMResponse:
        _ = args, kwargs
        return LLMResponse(content="ok", provider="openai", model="test", tokens_used=1)

    def stream_text(self, *args: Any, **kwargs: Any) -> AsyncGenerator[str, None]:
        _ = args, kwargs

        async def _gen() -> AsyncGenerator[str, None]:
            yield "ok"

        return _gen()

    async def close(self) -> None:
        return None


class _FailingInitStore:
    store_id = "graphiti"

    async def initialize(self) -> None:
        raise ConnectionError("falkordb unreachable")

    async def close(self) -> None:
        return None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_plugin_init_failure_disables_agent_flag() -> None:
    from aiecs.domain.agent.base_agent import BaseAIAgent
    from aiecs.domain.agent.models import AgentType

    class _Agent(BaseAIAgent):
        async def _initialize(self) -> None:
            return None

        async def _shutdown(self) -> None:
            return None

        async def execute_task(self, task: dict, context: dict) -> dict:
            return {"success": True, "output": "ok"}

        async def process_message(self, message: str, sender_id: str | None = None) -> dict:
            return {"response": "ok"}

    agent = _Agent(
        agent_id="deg-agent",
        name="Deg",
        agent_type=AgentType.DEVELOPER,
        config=AgentConfiguration(goal="g", temporal_memory_enabled=True),
        tools=[],
    )
    store = _FailingInitStore()
    store.close = AsyncMock()
    plugin = TemporalMemoryPlugin(PluginConfig(name="temporal_memory", enabled=True), agent)
    ctx = AgentPluginContext(agent=agent, task={"description": "t"}, context={}, task_description="t")

    with patch(
        "aiecs.domain.agent.plugins.builtin.temporal_memory_plugin.create_temporal_memory_store",
        return_value=store,
    ):
        await plugin.on_agent_init(ctx)

    store.close.assert_awaited_once()
    assert agent.temporal_memory_enabled is False
    assert agent.temporal_memory_engine is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_hybrid_execute_task_does_not_crash_when_temporal_init_fails() -> None:
    store = _FailingInitStore()
    store.close = AsyncMock()
    config = AgentConfiguration(
        goal="degraded",
        temporal_memory_enabled=True,
        plugins=[
            PluginConfig(name="temporal_memory", enabled=True),
        ],
    )
    agent = HybridAgent(
        agent_id="hybrid-deg",
        name="Hybrid Deg",
        llm_client=_MockLLM(),
        tools=[],
        config=config,
        max_iterations=1,
    )

    with patch(
        "aiecs.domain.agent.plugins.builtin.temporal_memory_plugin.create_temporal_memory_store",
        return_value=store,
    ):
        with patch(
            "aiecs.domain.agent.plugins.builtin.temporal_memory_plugin.get_settings",
            return_value=Settings(TM_INGEST_ASYNC=False),
        ):
            await agent.initialize()
            assert agent.temporal_memory_enabled is False

            result = await agent.execute_task(
                {"description": "run without temporal backend"},
                {"session_id": "s1"},
            )
            await agent.shutdown()

    assert result.get("success") is True
    store.close.assert_awaited_once()


@pytest.mark.unit
def test_sync_factory_does_not_swallow_init_errors() -> None:
    """Scheme B: create_temporal_memory_store stays sync; init runs in plugin."""
    from aiecs.infrastructure.temporal_memory.store_factory import create_temporal_memory_store

    store = create_temporal_memory_store(Settings(TM_ENABLED=False))
    assert isinstance(store, NoOpTemporalMemoryStore)
