"""
HybridAgent plugin delegation guards (P2-16, §2, §13).

Ensures HybridAgent does not duplicate skill/history paths handled by builtin plugins.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path
from unittest.mock import patch

import pytest

from aiecs.domain.agent.hybrid_agent import HybridAgent
from aiecs.domain.agent.models import AgentConfiguration
from aiecs.domain.agent.plugins.models import PluginConfig
from aiecs.domain.agent.skills.models import SkillDefinition, SkillMetadata, SkillResource
from aiecs.domain.agent.skills.registry import SkillRegistry
from aiecs.llm import BaseLLMClient, LLMResponse


class _MockLLM(BaseLLMClient):
    def __init__(self) -> None:
        super().__init__(provider_name="openai")

    async def generate_text(self, *args, **kwargs) -> LLMResponse:
        return LLMResponse(content="ok", provider="openai", model="test", tokens_used=1)

    async def stream_text(self, *args, **kwargs):
        yield "ok"

    async def close(self) -> None:
        pass


def _parity_skill() -> SkillDefinition:
    metadata = SkillMetadata(
        name="delegation-test-skill",
        version="1.0.0",
        description="P2-16 delegation test skill",
        tags=["parity"],
    )
    return SkillDefinition(
        metadata=metadata,
        skill_path=Path("/parity/delegation-skill"),
        scripts={
            "run": SkillResource(
                path="scripts/run.py",
                type="script",
                executable=True,
                mode="native",
                description="Run",
            )
        },
    )


@pytest.mark.unit
def test_hybrid_agent_module_has_no_direct_skill_context_calls() -> None:
    """HybridAgent must not call mixin skill APIs directly (docstrings excluded)."""
    hybrid_source = inspect.getsourcefile(HybridAgent)
    assert hybrid_source is not None
    tree = ast.parse(Path(hybrid_source).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in (
            "get_skill_context",
            "attach_skills",
        ):
            pytest.fail(
                f"HybridAgent must not call {func.attr}(); use SkillPlugin instead "
                f"(line {node.lineno})"
            )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_skill_attach_on_hybrid_init_only_via_skill_plugin() -> None:
    """``attach_skills`` runs once from SkillPlugin AGENT_INIT, not HybridAgent._initialize."""
    registry = SkillRegistry()
    skill = _parity_skill()
    if registry.get_skill(skill.metadata.name) is None:
        registry.register_skill(skill)

    config = AgentConfiguration(
        goal="delegation test",
        llm_model="test",
        skills_enabled=True,
        skill_names=["delegation-test-skill"],
        memory_enabled=False,
        plugins=[PluginConfig(name="memory", enabled=False)],
    )

    agent = HybridAgent(
        agent_id="hybrid-delegation-test",
        name="Delegation Test",
        llm_client=_MockLLM(),
        tools=[],
        config=config,
    )
    agent._skill_registry = registry

    with patch.object(agent, "_attach_skills_impl", wraps=agent._attach_skills_impl) as attach_mock:
        await agent.initialize()

    assert attach_mock.call_count == 1
    assert agent.has_skill("delegation-test-skill")
