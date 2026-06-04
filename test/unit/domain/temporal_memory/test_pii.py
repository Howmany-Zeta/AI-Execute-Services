"""Tests for episode body PII redaction (TM-075)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from aiecs.config.config import Settings
from aiecs.domain.agent.plugins.context import AgentPluginContext
from aiecs.domain.temporal_memory.engine import TemporalMemoryEngine
from aiecs.domain.temporal_memory.models import IngestEpisodeRequest, IngestEpisodeResult
from aiecs.domain.temporal_memory.pii import redact_episode_body


def test_redact_store_raw_false_truncates_and_hashes() -> None:
    body = "x" * 5000
    out = redact_episode_body(body, store_raw=False, max_chars=100)
    assert len(out) > 100
    assert out.startswith("x" * 100)
    assert "body_sha256_prefix=" in out


def test_redact_store_raw_true_truncates_without_hash() -> None:
    body = "y" * 5000
    out = redact_episode_body(body, store_raw=True, max_chars=200)
    assert out == "y" * 200
    assert "redacted" not in out


def test_redact_under_limit_unchanged() -> None:
    body = "user: hello\nassistant: hi"
    assert redact_episode_body(body, store_raw=False, max_chars=4000) == body
    assert redact_episode_body(body, store_raw=True, max_chars=4000) == body


@pytest.mark.asyncio
async def test_engine_applies_redaction_before_ingest() -> None:
    captured: list[IngestEpisodeRequest] = []

    class _Store:
        store_id = "mock"

        async def initialize(self) -> None:
            return None

        async def close(self) -> None:
            return None

        async def ingest_episode(self, request: IngestEpisodeRequest) -> IngestEpisodeResult:
            captured.append(request)
            return IngestEpisodeResult(episode_id="ep-1", group_id=request.group_id)

        async def ingest_episode_async(
            self,
            request: IngestEpisodeRequest,
            *,
            job_id: str | None = None,
        ) -> str:
            _ = job_id
            return "job"

        async def search_facts(self, *args, **kwargs) -> list:
            _ = args, kwargs
            return []

        async def get_fact(self, *args, **kwargs) -> None:
            _ = args, kwargs
            return None

        async def health_check(self) -> dict:
            return {"ready": True}

    settings = Settings(
        TM_STORE_RAW_EPISODE=False,
        TM_EPISODE_BODY_MAX_CHARS=50,
        TM_INGEST_ASYNC=False,
    )
    engine = TemporalMemoryEngine(_Store(), settings=settings)
    agent = MagicMock()
    agent.agent_id = "a1"
    ctx = AgentPluginContext(
        agent=agent,
        task={"task_id": "t1"},
        context={"session_id": "s1"},
        task_description="hello",
    )
    long_reply = "z" * 200
    await engine.ingest_from_task(ctx, {"final_response": long_reply})

    assert len(captured) == 1
    assert "body_sha256_prefix=" in captured[0].body
    assert len(captured[0].body) <= 50 + 80
