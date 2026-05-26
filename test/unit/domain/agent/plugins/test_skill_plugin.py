"""
Unit tests for SkillPlugin business logic (§7.1, P2-02).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from aiecs.domain.agent.base_agent import BaseAIAgent
from aiecs.domain.agent.models import AgentConfiguration, AgentType
from aiecs.domain.agent.plugins.builtin.skill_plugin import (
    SKILL_SYSTEM_MESSAGE_PREFIX,
    SkillPlugin,
)
from aiecs.domain.agent.plugins.context import AgentPluginContext
from aiecs.domain.agent.plugins.errors import PluginErrorException, PluginInitError
from aiecs.domain.agent.plugins.manager import PluginManager
from aiecs.domain.agent.plugins.models import PluginConfig, PluginPhase
from aiecs.domain.agent.plugins.registry import PluginRegistry
from aiecs.domain.agent.skills.models import SkillDefinition, SkillMetadata, SkillResource
from aiecs.domain.agent.skills.registry import SkillRegistry
from aiecs.llm import LLMMessage


class SkillTestAgent(BaseAIAgent):
    """BaseAIAgent with skill registry for SkillPlugin tests."""

    async def _initialize(self) -> None:
        pass

    async def _shutdown(self) -> None:
        pass

    async def execute_task(self, task: dict, context: dict) -> dict:
        return {"success": True, "output": "ok"}

    async def process_message(self, message: str, sender_id: str | None = None) -> dict:
        return {"response": "ok"}


def _sample_skill() -> SkillDefinition:
    metadata = SkillMetadata(
        name="test-skill",
        description="A test skill for SkillPlugin unit tests",
        version="1.0.0",
    )
    return SkillDefinition(
        metadata=metadata,
        skill_path=Path("/path/to/test-skill"),
        body="Skill body for injection.",
        scripts={
            "validate": SkillResource(
                path="scripts/validate.py",
                type="script",
                executable=True,
                mode="native",
                description="Validate input",
            ),
        },
    )


@pytest.fixture
def skill_registry() -> SkillRegistry:
    SkillRegistry.reset_instance()
    registry = SkillRegistry()
    registry.register_skill(_sample_skill())
    yield registry
    SkillRegistry.reset_instance()


@pytest.fixture
def skill_test_agent(skill_registry: SkillRegistry) -> SkillTestAgent:
    config = AgentConfiguration(goal="Skill plugin test", skills_enabled=True)
    return SkillTestAgent(
        agent_id="skill-plugin-test",
        name="Skill Plugin Test",
        agent_type=AgentType.CONVERSATIONAL,
        config=config,
        tools=[],
        skill_registry=skill_registry,
    )


def _make_ctx(agent: SkillTestAgent, task_description: str = "write unit tests") -> AgentPluginContext:
    return AgentPluginContext(
        agent=agent,
        task={"description": task_description, "extra": "ignored"},
        context={},
        task_description=task_description,
    )


@pytest.mark.unit
@pytest.mark.asyncio
class TestSkillPluginAgentInit:
    async def test_attach_skills_on_init(self, skill_test_agent: SkillTestAgent) -> None:
        registry = PluginRegistry()
        registry.register("skill", SkillPlugin, origin="registry")
        manager = PluginManager(
            skill_test_agent,
            [
                PluginConfig(
                    name="skill",
                    enabled=True,
                    options={"skill_names": ["test-skill"]},
                ),
            ],
            registry=registry,
        )
        await manager.initialize()

        assert skill_test_agent.has_skill("test-skill")
        assert len(skill_test_agent._attached_skills) == 1

    async def test_missing_skills_raises_plugin_init_error(
        self, skill_test_agent: SkillTestAgent
    ) -> None:
        registry = PluginRegistry()
        registry.register("skill", SkillPlugin, origin="registry")
        manager = PluginManager(
            skill_test_agent,
            [
                PluginConfig(
                    name="skill",
                    enabled=True,
                    options={"skill_names": ["nonexistent-skill"]},
                ),
            ],
            registry=registry,
        )
        with pytest.raises(PluginErrorException) as exc_info:
            await manager.initialize()

        assert isinstance(exc_info.value.error, PluginInitError)


@pytest.mark.unit
@pytest.mark.asyncio
class TestSkillPluginBuildMessages:
    async def test_build_messages_appends_skill_system_message(
        self, skill_test_agent: SkillTestAgent
    ) -> None:
        registry = PluginRegistry()
        registry.register("skill", SkillPlugin, origin="registry")
        manager = PluginManager(
            skill_test_agent,
            [
                PluginConfig(
                    name="skill",
                    enabled=True,
                    options={"skill_names": ["test-skill"], "inject_script_paths": False},
                ),
            ],
            registry=registry,
        )
        await manager.initialize()

        ctx = _make_ctx(skill_test_agent, "write unit tests")
        messages = [LLMMessage(role="user", content="Task: write unit tests")]
        result = await manager.run_phase(
            PluginPhase.BUILD_MESSAGES,
            ctx=ctx,
            messages=messages,
        )

        system_messages = [m for m in result if m.role == "system"]
        assert len(system_messages) == 1
        assert system_messages[0].content.startswith(SKILL_SYSTEM_MESSAGE_PREFIX)
        assert "## Skill: test-skill" in system_messages[0].content
        assert "Skill body for injection." in system_messages[0].content

    async def test_get_skill_context_receives_task_description_string(
        self, skill_test_agent: SkillTestAgent
    ) -> None:
        registry = PluginRegistry()
        registry.register("skill", SkillPlugin, origin="registry")
        manager = PluginManager(
            skill_test_agent,
            [
                PluginConfig(
                    name="skill",
                    enabled=True,
                    options={"skill_names": ["test-skill"]},
                ),
            ],
            registry=registry,
        )
        await manager.initialize()

        ctx = _make_ctx(skill_test_agent, "parity task description string")
        messages = [LLMMessage(role="user", content="Task: parity")]

        with patch.object(
            skill_test_agent,
            "get_skill_context",
            return_value="mocked skill context",
        ) as mock_get_context:
            result = await manager.run_phase(
                PluginPhase.BUILD_MESSAGES,
                ctx=ctx,
                messages=messages,
            )

        mock_get_context.assert_called_once_with(
            request="parity task description string",
            include_all_skills=False,
        )
        assert mock_get_context.call_args.kwargs["request"] == ctx.task_description
        assert isinstance(mock_get_context.call_args.kwargs["request"], str)
        assert not isinstance(mock_get_context.call_args.kwargs["request"], dict)

        skill_msgs = [m for m in result if m.content and SKILL_SYSTEM_MESSAGE_PREFIX in m.content]
        assert len(skill_msgs) == 1
        assert skill_msgs[0].content == f"{SKILL_SYSTEM_MESSAGE_PREFIX}mocked skill context"


@pytest.mark.unit
@pytest.mark.asyncio
class TestSkillPluginShutdown:
    async def test_shutdown_detaches_all_skills(self, skill_test_agent: SkillTestAgent) -> None:
        registry = PluginRegistry()
        registry.register("skill", SkillPlugin, origin="registry")
        manager = PluginManager(
            skill_test_agent,
            [
                PluginConfig(
                    name="skill",
                    enabled=True,
                    options={"skill_names": ["test-skill"]},
                ),
            ],
            registry=registry,
        )
        await manager.initialize()
        assert skill_test_agent.has_skill("test-skill")

        await manager.shutdown()

        assert not skill_test_agent._attached_skills
