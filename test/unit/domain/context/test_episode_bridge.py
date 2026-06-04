"""Context episode_bridge metadata round-trip (TM-084)."""

from __future__ import annotations

from typing import Any

import pytest

from aiecs.domain.temporal_memory.constants import (
    METADATA_TEMPORAL_EPISODE_ID,
    METADATA_TEMPORAL_GROUP_ID,
    METADATA_TEMPORAL_INGEST_JOB_ID,
    PLUGIN_STATE_EPISODE_ID,
    PLUGIN_STATE_GROUP_ID,
    PLUGIN_STATE_INGEST_JOB_ID,
    build_l0_temporal_metadata,
)
from aiecs.domain.temporal_memory.episode_bridge import has_temporal_metadata


class _RecordingContextEngine:
    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []

    async def add_conversation_message(
        self,
        *,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        self.messages.append(
            {
                "session_id": session_id,
                "role": role,
                "content": content,
                "metadata": dict(metadata or {}),
            }
        )
        return True


@pytest.mark.asyncio
async def test_metadata_round_trip_via_context_engine() -> None:
    engine = _RecordingContextEngine()
    plugin_state = {
        PLUGIN_STATE_EPISODE_ID: "ep-ctx-1",
        PLUGIN_STATE_GROUP_ID: "aiecs:agent:sess",
        PLUGIN_STATE_INGEST_JOB_ID: "job-ctx-1",
    }
    meta = build_l0_temporal_metadata(plugin_state)
    await engine.add_conversation_message(
        session_id="sess-bridge",
        role="assistant",
        content="done",
        metadata=meta,
    )

    stored = engine.messages[0]["metadata"]
    assert stored[METADATA_TEMPORAL_EPISODE_ID] == "ep-ctx-1"
    assert stored[METADATA_TEMPORAL_GROUP_ID] == "aiecs:agent:sess"
    assert stored[METADATA_TEMPORAL_INGEST_JOB_ID] == "job-ctx-1"
    assert has_temporal_metadata(stored)


@pytest.mark.asyncio
async def test_no_temporal_keys_when_plugin_state_empty() -> None:
    engine = _RecordingContextEngine()
    meta = build_l0_temporal_metadata({})
    await engine.add_conversation_message(
        session_id="sess-plain",
        role="assistant",
        content="plain",
        metadata=meta,
    )
    assert engine.messages[0]["metadata"] == {}
    assert not has_temporal_metadata(engine.messages[0]["metadata"])
