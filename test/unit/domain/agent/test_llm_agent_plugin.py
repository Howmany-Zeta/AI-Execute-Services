"""
LLMAgent plugin integration tests (P3-02, §8.2 simplified kernel).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from aiecs.domain.agent.llm_agent import LLMAgent
from aiecs.domain.agent.models import AgentConfiguration
from aiecs.domain.agent.plugins.models import PluginConfig, PluginPhase
from aiecs.domain.agent.plugins.testing.normalize import (
    normalize_execute_task_response,
    normalize_messages,
)
from aiecs.llm import BaseLLMClient, LLMMessage, LLMResponse

_REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURES_DIR = _REPO_ROOT / "tests" / "fixtures" / "plugin_parity"


class ParityMockLLMClient(BaseLLMClient):
    """Mock LLM returning scripted outputs for multiturn parity."""

    def __init__(self, outputs: list[str] | None = None):
        super().__init__(provider_name="openai")
        self._outputs = outputs or ["Parity LLM response."]
        self._call_index = 0
        self.last_messages: list[LLMMessage] = []

    def _next_output(self) -> str:
        idx = min(self._call_index, len(self._outputs) - 1)
        self._call_index += 1
        return self._outputs[idx]

    async def generate_text(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        self.last_messages = list(messages)
        return LLMResponse(
            content=self._next_output(),
            provider="openai",
            model=model or "parity-mock",
            tokens_used=42,
        )

    async def stream_text(self, *args: Any, **kwargs: Any):
        for token in self._next_output().split():
            yield token

    async def close(self) -> None:
        pass


def _load_fixture(name: str) -> dict[str, Any]:
    return yaml.safe_load((FIXTURES_DIR / name).read_text(encoding="utf-8"))


async def _llm_agent_from_fixture(
    spec: dict[str, Any],
    *,
    client: ParityMockLLMClient | None = None,
) -> tuple[LLMAgent, dict[str, Any], dict[str, Any], str]:
    raw_config = dict(spec.get("config") or {})
    config = AgentConfiguration(**raw_config)
    task = spec.get("task") or {"description": "Parity test task"}
    context = dict(spec.get("context") or {})
    task_description = str(
        task.get("description") or task.get("prompt") or task.get("task", "")
    )

    capture = spec.get("capture") or {}
    outputs: list[str] = []
    warmup = capture.get("warmup")
    if warmup:
        outputs.append(str(warmup.get("mock_output", "Warmup response.")))
    outputs.append(str(capture.get("mock_final_output", "Final response.")))

    llm_client = client or ParityMockLLMClient(outputs)

    agent = LLMAgent(
        agent_id="llm-plugin-test",
        name="LLM Plugin Test",
        llm_client=llm_client,
        config=config,
    )
    await agent.initialize()
    return agent, task, context, task_description


@pytest.mark.unit
@pytest.mark.asyncio
class TestLLMAgentPluginExecute:
    async def test_memory_multiturn_matches_p3_00_golden(self) -> None:
        spec = _load_fixture("llm_memory_multiturn.yaml")
        expect = spec["expect"]
        agent, task, context, task_description = await _llm_agent_from_fixture(spec)

        warmup = spec["capture"]["warmup"]
        await agent.execute_task(warmup["task"], dict(warmup.get("context") or {}))

        plugin_ctx = agent._make_plugin_context(task, context, task_description)
        agent._apply_task_plugin_configs(task=task, context=context)
        await agent._plugin_manager.run_phase(PluginPhase.PRE_TASK, ctx=plugin_ctx)
        messages = await agent._build_messages_via_plugins(
            task_description,
            context,
            plugin_ctx,
        )

        assert normalize_messages(messages) == expect["messages_normalized"]

        result = await agent.execute_task(task, context)
        assert normalize_execute_task_response(result) == expect["execute_task_response"]

    async def test_plugins_empty_derived_memory_matches_legacy_messages(self) -> None:
        """``plugins=[]`` derives memory plugin; messages match legacy ``_build_messages``."""
        spec = _load_fixture("llm_memory_disabled.yaml")
        agent, task, context, task_description = await _llm_agent_from_fixture(spec)

        plugin_ctx = agent._make_plugin_context(task, context, task_description)
        agent._apply_task_plugin_configs(task=task, context=context)
        await agent._plugin_manager.run_phase(PluginPhase.PRE_TASK, ctx=plugin_ctx)
        plugin_messages = await agent._build_messages_via_plugins(
            task_description,
            context,
            plugin_ctx,
        )
        legacy_messages = agent._build_messages(task_description, context)

        assert normalize_messages(plugin_messages) == normalize_messages(legacy_messages)

        result = await agent.execute_task(task, context)
        assert result["success"] is True
        assert result["output"] == spec["capture"]["mock_final_output"]

    async def test_process_message_uses_plugin_memory_path(self) -> None:
        config = AgentConfiguration(
            goal="LLM plugin message test",
            llm_model="parity-mock",
            system_prompt="You are a test agent.",
            memory_enabled=True,
            plugins=[],
        )
        client = ParityMockLLMClient(["First reply.", "Second reply."])
        agent = LLMAgent(
            agent_id="llm-process-msg",
            name="Process Message Test",
            llm_client=client,
            config=config,
        )
        await agent.initialize()

        await agent.process_message("Hello")
        await agent.process_message("Follow up")

        assert len(agent._conversation_history) == 4
        assert agent._conversation_history[-2].content == "Follow up"
        assert agent._conversation_history[-1].content == "Second reply."

    async def test_execute_task_runs_pre_build_post_phases(self) -> None:
        config = AgentConfiguration(
            goal="Phase order test",
            llm_model="parity-mock",
            memory_enabled=True,
            plugins=[],
        )
        client = ParityMockLLMClient(["done"])
        agent = LLMAgent(
            agent_id="llm-phases",
            name="Phase Order Test",
            llm_client=client,
            config=config,
        )
        await agent.initialize()

        phases: list[str] = []
        original = agent._plugin_manager.run_phase

        async def tracking(phase: PluginPhase, **kwargs: Any) -> Any:
            phases.append(phase.value)
            return await original(phase, **kwargs)

        agent._plugin_manager.run_phase = tracking  # type: ignore[method-assign]

        await agent.execute_task({"description": "test task"}, {})

        assert phases == ["pre_task", "build_messages", "post_task"]

    async def test_skill_plugin_not_enabled_by_default(self) -> None:
        config = AgentConfiguration(
            goal="No skill default",
            llm_model="parity-mock",
            skills_enabled=False,
            plugins=[],
        )
        agent = LLMAgent(
            agent_id="llm-no-skill",
            name="No Skill",
            llm_client=ParityMockLLMClient(),
            config=config,
        )
        await agent.initialize()

        skill_plugin = agent._plugin_manager.get_plugin("skill")
        assert skill_plugin is None or agent._plugin_manager.is_enabled("skill") is False
