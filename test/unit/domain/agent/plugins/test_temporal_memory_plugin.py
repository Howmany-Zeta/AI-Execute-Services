"""Unit tests for TemporalMemoryPlugin."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiecs.config.config import Settings
from aiecs.domain.agent.base_agent import BaseAIAgent
from aiecs.domain.agent.models import AgentConfiguration, AgentType
from aiecs.domain.agent.plugins.builtin.temporal_memory_plugin import (
    PLUGIN_STATE_EPISODE_ID,
    PLUGIN_STATE_FACTS_KEY,
    PLUGIN_STATE_GROUP_ID,
    PLUGIN_STATE_INGEST_JOB_ID,
    TemporalMemoryPlugin,
    format_facts_for_prompt,
)
from aiecs.domain.agent.plugins.context import AgentPluginContext
from aiecs.domain.agent.plugins.defaults import derive_default_plugins
from aiecs.domain.agent.plugins.models import PluginConfig
from aiecs.domain.temporal_memory.engine import TemporalMemoryEngine
from aiecs.domain.temporal_memory.models import (
    IngestEpisodeRequest,
    IngestEpisodeResult,
    TemporalFact,
)
from aiecs.infrastructure.temporal_memory import NoOpTemporalMemoryStore


class _RecordingStore:
    store_id = "mock"

    def __init__(self) -> None:
        self.search_calls: list[tuple[str, list[str]]] = []
        self.ingest_calls: list[IngestEpisodeRequest] = []

    async def initialize(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def ingest_episode(self, request: IngestEpisodeRequest) -> IngestEpisodeResult:
        self.ingest_calls.append(request)
        return IngestEpisodeResult(episode_id="ep-1", group_id=request.group_id)

    async def ingest_episode_async(
        self,
        request: IngestEpisodeRequest,
        *,
        job_id: str | None = None,
    ) -> str:
        _ = job_id
        await self.ingest_episode(request)
        return "job-1"

    async def search_facts(
        self,
        query: str,
        *,
        group_ids: list[str],
        limit: int = 10,
        valid_at: datetime | None = None,
        filters: Any = None,
    ) -> list[TemporalFact]:
        _ = limit, valid_at, filters
        self.search_calls.append((query, group_ids))
        return [
            TemporalFact(
                fact_id="f1",
                text="sunny weather",
                group_id=group_ids[0],
                valid_at=datetime.now(timezone.utc),
            )
        ]

    async def get_fact(self, fact_id: str, *, group_ids: list[str]) -> TemporalFact | None:
        _ = fact_id, group_ids
        return None

    async def health_check(self) -> dict[str, Any]:
        return {"backend": "mock", "ready": True}


class TemporalTestAgent(BaseAIAgent):
    async def _initialize(self) -> None:
        return None

    async def _shutdown(self) -> None:
        return None

    async def execute_task(self, task: dict, context: dict) -> dict:
        return {"success": True, "output": "ok"}

    async def process_message(self, message: str, sender_id: str | None = None) -> dict:
        return {"response": "ok"}


def _plugin_ctx(agent: TemporalTestAgent, **kwargs: Any) -> AgentPluginContext:
    return AgentPluginContext(
        agent=agent,
        task=kwargs.get("task", {"task_id": "t1", "description": "weather?"}),
        context=kwargs.get("context", {"session_id": "sess-1"}),
        task_description=kwargs.get("task_description", "What is the weather?"),
    )


@pytest.fixture
def temporal_agent() -> TemporalTestAgent:
    return TemporalTestAgent(
        agent_id="tm-agent",
        name="Temporal Test",
        agent_type=AgentType.DEVELOPER,
        config=AgentConfiguration(
            goal="test",
            temporal_memory_enabled=True,
            plugins=[PluginConfig(name="temporal_memory", enabled=True)],
        ),
        tools=[],
    )


def test_derive_default_plugins_disabled_when_noop_store() -> None:
    agent = TemporalTestAgent(
        agent_id="a",
        name="A",
        agent_type=AgentType.DEVELOPER,
        config=AgentConfiguration(temporal_memory_enabled=True),
        tools=[],
    )
    with patch(
        "aiecs.domain.agent.plugins.defaults.create_temporal_memory_store",
        return_value=NoOpTemporalMemoryStore(),
    ):
        configs = derive_default_plugins(agent._config, agent)
    tm = next(c for c in configs if c.name == "temporal_memory")
    assert tm.enabled is False


def test_format_facts_for_prompt() -> None:
    facts = [TemporalFact(fact_id="1", text="fact one", group_id="g")]
    text = format_facts_for_prompt(facts)
    assert "TEMPORAL MEMORY FACTS" in text
    assert "fact one" in text


@pytest.mark.asyncio
async def test_noop_store_disables_plugin_on_init(temporal_agent: TemporalTestAgent) -> None:
    plugin = TemporalMemoryPlugin(
        PluginConfig(name="temporal_memory", enabled=True),
        temporal_agent,
    )
    ctx = _plugin_ctx(temporal_agent)
    with patch(
        "aiecs.domain.agent.plugins.builtin.temporal_memory_plugin.create_temporal_memory_store",
        return_value=NoOpTemporalMemoryStore(),
    ):
        await plugin.on_agent_init(ctx)

    assert temporal_agent.temporal_memory_enabled is False
    assert temporal_agent.temporal_memory_engine is None


@pytest.mark.asyncio
async def test_pre_task_writes_facts_to_plugin_state(temporal_agent: TemporalTestAgent) -> None:
    store = _RecordingStore()
    temporal_agent.temporal_memory_engine = TemporalMemoryEngine(store)
    temporal_agent.temporal_memory_enabled = True

    plugin = TemporalMemoryPlugin(
        PluginConfig(name="temporal_memory", enabled=True),
        temporal_agent,
    )
    ctx = _plugin_ctx(temporal_agent)
    await plugin.on_pre_task(ctx)

    facts = ctx.plugin_state.get(PLUGIN_STATE_FACTS_KEY)
    assert isinstance(facts, list)
    assert len(facts) == 1
    assert facts[0].text == "sunny weather"
    assert len(store.search_calls) == 1


@pytest.mark.asyncio
async def test_post_task_ingest_calls_engine(temporal_agent: TemporalTestAgent) -> None:
    store = _RecordingStore()
    engine = TemporalMemoryEngine(store, settings=Settings(TM_INGEST_ASYNC=False))
    temporal_agent.temporal_memory_engine = engine
    temporal_agent.temporal_memory_enabled = True

    plugin = TemporalMemoryPlugin(
        PluginConfig(name="temporal_memory", enabled=True),
        temporal_agent,
    )
    ctx = _plugin_ctx(temporal_agent)
    result = {"final_response": "It is sunny."}
    with patch(
        "aiecs.domain.agent.plugins.builtin.temporal_memory_plugin.get_settings",
        return_value=Settings(TM_INGEST_ASYNC=False),
    ):
        await plugin.on_post_task(ctx, result)

    assert len(store.ingest_calls) == 1
    assert "user:" in store.ingest_calls[0].body
    assert "assistant:" in store.ingest_calls[0].body
    assert isinstance(ctx.plugin_state.get(PLUGIN_STATE_INGEST_JOB_ID), str)
    assert ctx.plugin_state.get(PLUGIN_STATE_EPISODE_ID) == "ep-1"
    assert ctx.plugin_state.get(PLUGIN_STATE_GROUP_ID) == store.ingest_calls[0].group_id


@pytest.mark.asyncio
async def test_post_task_async_enqueues_without_blocking_ingest(
    temporal_agent: TemporalTestAgent,
) -> None:
    store = _RecordingStore()
    engine = TemporalMemoryEngine(store, settings=Settings(TM_INGEST_ASYNC=True))
    temporal_agent.temporal_memory_engine = engine
    temporal_agent.temporal_memory_enabled = True

    mock_queue = MagicMock()
    mock_queue.enqueue = AsyncMock()

    plugin = TemporalMemoryPlugin(
        PluginConfig(name="temporal_memory", enabled=True),
        temporal_agent,
    )
    ctx = _plugin_ctx(temporal_agent)

    with patch(
        "aiecs.domain.agent.plugins.builtin.temporal_memory_plugin.get_temporal_memory_ingest_queue",
        return_value=mock_queue,
    ):
        await plugin.on_post_task(ctx, {"final_response": "done"})

    mock_queue.enqueue.assert_awaited_once()
    assert len(store.ingest_calls) == 0


@pytest.mark.asyncio
async def test_agent_shutdown_releases_queue_refcount_not_global_stop(
    temporal_agent: TemporalTestAgent,
) -> None:
    import aiecs.infrastructure.temporal_memory.ingest_queue as ingest_mod
    from aiecs.infrastructure.temporal_memory.ingest_queue import get_temporal_memory_ingest_queue

    ingest_mod._queue = None
    try:
        store = _RecordingStore()
        plugin_a = TemporalMemoryPlugin(
            PluginConfig(name="temporal_memory", enabled=True),
            temporal_agent,
        )
        agent_b = TemporalTestAgent(
            agent_id="tm-agent-b",
            name="B",
            agent_type=AgentType.DEVELOPER,
            config=AgentConfiguration(
                goal="test",
                temporal_memory_enabled=True,
                plugins=[PluginConfig(name="temporal_memory", enabled=True)],
            ),
            tools=[],
        )
        plugin_b = TemporalMemoryPlugin(
            PluginConfig(name="temporal_memory", enabled=True),
            agent_b,
        )

        with patch(
            "aiecs.domain.agent.plugins.builtin.temporal_memory_plugin.create_temporal_memory_store",
            return_value=store,
        ):
            with patch(
                "aiecs.domain.agent.plugins.builtin.temporal_memory_plugin.get_settings",
                return_value=Settings(TM_INGEST_ASYNC=True),
            ):
                await plugin_a.on_agent_init(_plugin_ctx(temporal_agent))
                await plugin_b.on_agent_init(_plugin_ctx(agent_b))

        queue = get_temporal_memory_ingest_queue()
        assert queue.holder_count == 2
        assert queue.running

        with patch(
            "aiecs.domain.agent.plugins.builtin.temporal_memory_plugin.get_settings",
            return_value=Settings(TM_INGEST_ASYNC=True),
        ):
            await plugin_a.on_agent_shutdown(_plugin_ctx(temporal_agent))

        assert queue.running
        assert queue.holder_count == 1

        with patch(
            "aiecs.domain.agent.plugins.builtin.temporal_memory_plugin.get_settings",
            return_value=Settings(TM_INGEST_ASYNC=True),
        ):
            await plugin_b.on_agent_shutdown(_plugin_ctx(agent_b))

        assert not queue.running
        assert queue.holder_count == 0
    finally:
        ingest_mod._queue = None


@pytest.mark.asyncio
async def test_agent_init_failure_closes_store(temporal_agent: TemporalTestAgent) -> None:
    store = _RecordingStore()
    store.initialize = AsyncMock(side_effect=ConnectionError("graph down"))
    store.close = AsyncMock()

    plugin = TemporalMemoryPlugin(
        PluginConfig(name="temporal_memory", enabled=True),
        temporal_agent,
    )

    with patch(
        "aiecs.domain.agent.plugins.builtin.temporal_memory_plugin.create_temporal_memory_store",
        return_value=store,
    ):
        await plugin.on_agent_init(_plugin_ctx(temporal_agent))

    store.close.assert_awaited_once()
    assert temporal_agent.temporal_memory_engine is None
    assert temporal_agent.temporal_memory_enabled is False


@pytest.mark.asyncio
async def test_build_messages_injects_facts_when_enabled(temporal_agent: TemporalTestAgent) -> None:
    from aiecs.llm import LLMMessage

    temporal_agent.temporal_memory_engine = TemporalMemoryEngine(_RecordingStore())
    temporal_agent.temporal_memory_enabled = True

    plugin = TemporalMemoryPlugin(
        PluginConfig(name="temporal_memory", enabled=True, options={"inject_facts": True}),
        temporal_agent,
    )
    ctx = _plugin_ctx(temporal_agent)
    ctx.plugin_state[PLUGIN_STATE_FACTS_KEY] = [
        TemporalFact(fact_id="f1", text="rain expected", group_id="g"),
    ]

    messages = await plugin.on_build_messages(ctx, [LLMMessage(role="system", content="You are helpful.")])
    assert len(messages) == 2
    assert "rain expected" in (messages[-1].content or "")
