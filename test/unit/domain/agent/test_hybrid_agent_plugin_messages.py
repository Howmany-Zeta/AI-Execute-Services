"""
HybridAgent initial messages via BUILD_MESSAGES plugins (P2-08, §8.3).

Compares normalized messages to P2-00 parity fixtures.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from aiecs.domain.agent.hybrid_agent import HybridAgent
from aiecs.domain.agent.models import AgentConfiguration
from aiecs.domain.agent.plugins.models import PluginConfig
from aiecs.domain.agent.plugins.testing.normalize import normalize_messages
from aiecs.domain.agent.skills.models import SkillDefinition, SkillMetadata, SkillResource
from aiecs.domain.agent.skills.registry import SkillRegistry
from aiecs.llm import BaseLLMClient, LLMMessage, LLMResponse
from aiecs.tools.base_tool import BaseTool

_REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURES_DIR = _REPO_ROOT / "tests" / "fixtures" / "plugin_parity"


class ParityStubTool(BaseTool):
    async def run_async(self, operation: str, **kwargs: Any) -> dict[str, Any]:
        return {"status": "ok", "operation": operation}


class ParityMockLLMClient(BaseLLMClient):
    def __init__(self) -> None:
        super().__init__(provider_name="openai")

    async def generate_text(self, *args: Any, **kwargs: Any) -> LLMResponse:
        return LLMResponse(content="ok", provider="openai", model="parity-mock", tokens_used=1)

    async def stream_text(self, *args: Any, **kwargs: Any):
        yield "ok"

    async def close(self) -> None:
        pass


def _parity_skill() -> SkillDefinition:
    metadata = SkillMetadata(
        name="parity-test-skill",
        description="Minimal skill for plugin parity baseline",
        version="1.0.0",
        tags=["parity"],
    )
    return SkillDefinition(
        metadata=metadata,
        skill_path=Path("/parity/test-skill"),
        scripts={
            "run": SkillResource(
                path="scripts/run.py",
                type="script",
                executable=True,
                mode="native",
                description="Run parity skill",
            )
        },
    )


def _resolve_tools(spec: dict[str, Any]) -> dict[str, BaseTool] | list[str]:
    raw = spec.get("agent", {}).get("tools", [])
    if not raw:
        return []
    instances: dict[str, BaseTool] = {}
    for name in raw:
        if name in ("parity_search", "search"):
            key = "parity_search"
            if key not in instances:
                instances[key] = ParityStubTool(tool_name=key)
    return instances or list(raw)


def _load_fixture(name: str) -> dict[str, Any]:
    path = FIXTURES_DIR / name
    return yaml.safe_load(path.read_text(encoding="utf-8"))


async def _build_hybrid_from_fixture(
    spec: dict[str, Any],
    *,
    disable_memory_skill_plugins: bool = False,
) -> tuple[HybridAgent, str, dict[str, Any]]:
    raw_config = dict(spec.get("config") or {})
    if disable_memory_skill_plugins:
        raw_config["plugins"] = [
            PluginConfig(name="memory", enabled=False),
            PluginConfig(name="skill", enabled=False),
        ]
    config = AgentConfiguration(**raw_config)
    tools = _resolve_tools(spec)
    task = spec.get("task") or {"description": "Parity test task"}
    context = dict(spec.get("context") or {})
    task_description = str(
        task.get("description") or task.get("prompt") or task.get("task", "")
    )

    skill_registry = None
    if config.skills_enabled and not disable_memory_skill_plugins:
        skill_registry = SkillRegistry()
        parity_skill = _parity_skill()
        if skill_registry.get_skill(parity_skill.metadata.name) is None:
            skill_registry.register_skill(parity_skill)

    agent = HybridAgent(
        agent_id="plugin-messages-test",
        name="Plugin Messages Test",
        llm_client=ParityMockLLMClient(),
        tools=tools,
        config=config,
        max_iterations=3,
    )
    if skill_registry is not None:
        agent._skill_registry = skill_registry
    await agent.initialize()
    return agent, task_description, context


@pytest.mark.unit
@pytest.mark.asyncio
class TestHybridAgentPluginMessages:
    """BUILD_MESSAGES + async initial messages match P2-00 golden fixtures."""

    async def test_plugins_disabled_matches_baseline_fixture(self) -> None:
        spec = _load_fixture("hybrid_baseline.yaml")
        agent, task_description, context = await _build_hybrid_from_fixture(
            spec, disable_memory_skill_plugins=True
        )
        plugin_ctx = agent._make_plugin_context(
            task=spec.get("task") or {"description": task_description},
            context=context,
            task_description=task_description,
        )
        messages = await agent._build_initial_messages_async(
            task_description, context, plugin_ctx
        )
        assert normalize_messages(messages) == spec["expect"]["messages_normalized"]

    async def test_context_history_matches_fixture(self) -> None:
        spec = _load_fixture("hybrid_context_history.yaml")
        agent, task_description, context = await _build_hybrid_from_fixture(spec)
        plugin_ctx = agent._make_plugin_context(
            task=spec.get("task") or {"description": task_description},
            context=context,
            task_description=task_description,
        )
        messages = await agent._build_initial_messages_async(
            task_description, context, plugin_ctx
        )
        assert normalize_messages(messages) == spec["expect"]["messages_normalized"]

    async def test_skills_enabled_matches_fixture(self) -> None:
        spec = _load_fixture("hybrid_skills_enabled.yaml")
        agent, task_description, context = await _build_hybrid_from_fixture(spec)
        plugin_ctx = agent._make_plugin_context(
            task=spec.get("task") or {"description": task_description},
            context=context,
            task_description=task_description,
        )
        messages = await agent._build_initial_messages_async(
            task_description, context, plugin_ctx
        )
        assert normalize_messages(messages) == spec["expect"]["messages_normalized"]
