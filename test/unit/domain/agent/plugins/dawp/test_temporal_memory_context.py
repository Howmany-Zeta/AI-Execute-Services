"""Tests for DAWP read-only temporal_memory.facts injection (D3-04)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from aiecs.domain.agent.plugins.context import AgentPluginContext
from aiecs.domain.agent.plugins.dawp.temporal_memory_context import (
    inject_temporal_memory_facts_into_messages,
)
from aiecs.domain.temporal_memory.constants import PLUGIN_STATE_FACTS_KEY
from aiecs.domain.temporal_memory.models import TemporalFact
from aiecs.llm import LLMMessage


def _ctx(plugin_state: dict | None = None) -> AgentPluginContext:
    return AgentPluginContext(
        agent=MagicMock(),
        task={},
        context={},
        task_description="test",
        plugin_state=plugin_state or {},
    )


@pytest.mark.unit
class TestTemporalMemoryFactsInjection:
    def test_no_facts_unchanged(self) -> None:
        messages = [LLMMessage(role="user", content="task")]
        ctx = _ctx({})
        result = inject_temporal_memory_facts_into_messages(messages, ctx)
        assert result is messages
        assert len(result) == 1

    def test_empty_facts_list_unchanged(self) -> None:
        messages = [LLMMessage(role="user", content="task")]
        ctx = _ctx({PLUGIN_STATE_FACTS_KEY: []})
        result = inject_temporal_memory_facts_into_messages(messages, ctx)
        assert result is messages

    def test_facts_appended_as_user_message(self) -> None:
        messages = [LLMMessage(role="user", content="task")]
        ctx = _ctx(
            {
                PLUGIN_STATE_FACTS_KEY: [
                    TemporalFact(
                        fact_id="f1",
                        text="User prefers concise answers",
                        group_id="g1",
                        source_episode_id="episode-1",
                    ),
                ]
            }
        )
        result = inject_temporal_memory_facts_into_messages(messages, ctx)
        assert len(result) == 2
        assert result[0].content == "task"
        assert "TEMPORAL MEMORY FACTS:" in (result[1].content or "")
        assert "concise answers" in (result[1].content or "")

    def test_without_temporal_memory_plugin_no_crash(self) -> None:
        """plugin_state without temporal_memory keys must not raise."""
        messages = [LLMMessage(role="user", content="task")]
        ctx = _ctx({"dawp.pending": []})
        result = inject_temporal_memory_facts_into_messages(messages, ctx)
        assert len(result) == 1

    def test_invalid_facts_type_no_crash(self) -> None:
        messages = [LLMMessage(role="user", content="task")]
        ctx = _ctx({PLUGIN_STATE_FACTS_KEY: "not-a-list"})
        result = inject_temporal_memory_facts_into_messages(messages, ctx)
        assert len(result) == 1
