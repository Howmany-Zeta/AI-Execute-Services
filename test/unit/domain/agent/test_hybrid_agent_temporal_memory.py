"""HybridAgent wiring with temporal_memory plugin (L1 smoke)."""

from __future__ import annotations

from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest

from aiecs.config.config import Settings
from aiecs.domain.agent import HybridAgent
from aiecs.domain.agent.models import AgentConfiguration
from aiecs.domain.agent.plugins.models import PluginConfig
from aiecs.llm import BaseLLMClient, LLMResponse


class _MockLLM(BaseLLMClient):
    def __init__(self) -> None:
        super().__init__(provider_name="openai")

    async def generate_text(self, *args: Any, **kwargs: Any) -> LLMResponse:
        _ = args, kwargs
        return LLMResponse(content="Hybrid temporal smoke.", provider="openai", model="test", tokens_used=1)

    def stream_text(self, *args: Any, **kwargs: Any) -> AsyncGenerator[str, None]:
        _ = args, kwargs

        async def _gen() -> AsyncGenerator[str, None]:
            yield "Hybrid temporal smoke."

        return _gen()

    async def close(self) -> None:
        return None


class _HybridRecordingStore:
    store_id = "mock"

    def __init__(self) -> None:
        self.ingest_calls = 0
        self.search_calls = 0

    async def initialize(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def ingest_episode(self, request: Any) -> Any:
        _ = request
        self.ingest_calls += 1
        from aiecs.domain.temporal_memory.models import IngestEpisodeResult

        return IngestEpisodeResult(episode_id="ep-1", group_id="g1")

    async def ingest_episode_async(self, request: Any, *, job_id: str | None = None) -> str:
        _ = job_id
        await self.ingest_episode(request)
        return "job-1"

    async def search_facts(self, query: str, *, group_ids: list[str], **kwargs: Any) -> list:
        _ = query, group_ids, kwargs
        self.search_calls += 1
        return []

    async def get_fact(self, fact_id: str, *, group_ids: list[str]) -> None:
        _ = fact_id, group_ids
        return None

    async def health_check(self) -> dict[str, Any]:
        return {"backend": "mock", "ready": True}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_hybrid_agent_temporal_memory_post_task_ingest() -> None:
    store = _HybridRecordingStore()
    config = AgentConfiguration(
        goal="hybrid temporal",
        temporal_memory_enabled=True,
        plugins=[
            PluginConfig(name="memory", enabled=True),
            PluginConfig(name="temporal_memory", enabled=True),
        ],
    )
    agent = HybridAgent(
        agent_id="hybrid-tm",
        name="Hybrid TM",
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
            assert agent.temporal_memory_enabled is True

            result = await agent.execute_task(
                {"description": "Remember the launch code ALPHA"},
                {"session_id": "hybrid-sess"},
            )

            await agent.shutdown()

    assert result.get("success") is True
    assert store.ingest_calls >= 1
    assert store.search_calls >= 1
