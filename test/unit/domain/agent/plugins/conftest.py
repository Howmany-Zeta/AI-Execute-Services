"""
Shared fixtures for agent plugin unit tests.
"""

import pytest

from aiecs.domain.agent.base_agent import BaseAIAgent
from aiecs.domain.agent.models import AgentConfiguration, AgentType


class MockPluginAgent(BaseAIAgent):
    """Minimal BaseAIAgent for plugin framework tests."""

    async def _initialize(self) -> None:
        pass

    async def _shutdown(self) -> None:
        pass

    async def execute_task(self, task: dict, context: dict) -> dict:
        return {"success": True, "output": "plugin test result"}

    async def process_message(self, message: str, sender_id: str | None = None) -> dict:
        return {"response": "plugin test response"}


@pytest.fixture
def plugin_agent_config() -> AgentConfiguration:
    """Default AgentConfiguration for plugin tests."""
    return AgentConfiguration(goal="Plugin test agent")


@pytest.fixture
def mock_agent(plugin_agent_config: AgentConfiguration) -> MockPluginAgent:
    """Minimal mock BaseAIAgent (empty tools list)."""
    agent = MockPluginAgent(
        agent_id="plugin-test-agent",
        name="Plugin Test Agent",
        agent_type=AgentType.CONVERSATIONAL,
        config=plugin_agent_config,
        tools=[],
    )
    agent._plugin_manager = None
    agent._hook_order = []
    return agent
