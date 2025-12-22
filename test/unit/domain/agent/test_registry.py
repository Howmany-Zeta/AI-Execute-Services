"""
Unit tests for AgentRegistry.
"""

import pytest
from aiecs.domain.agent.registry import AgentRegistry, get_global_registry, reset_global_registry
from aiecs.domain.agent.models import AgentState, AgentType
from aiecs.domain.agent.exceptions import AgentNotFoundError, AgentAlreadyRegisteredError
from .test_base_agent import MockAgent
from aiecs.domain.agent.models import AgentConfiguration


@pytest.mark.unit
class TestAgentRegistry:
    """Test AgentRegistry functionality."""

    @pytest.fixture
    def registry(self):
        """Create test registry."""
        return AgentRegistry()

    @pytest.fixture
    def agent(self):
        """Create test agent."""
        config = AgentConfiguration()
        return MockAgent(
            agent_id="test-agent-1",
            name="Test Agent",
            agent_type=AgentType.CONVERSATIONAL,
            config=config
        )

    def test_register_agent(self, registry, agent):
        """Test agent registration."""
        registry.register(agent)
        assert registry.exists(agent.agent_id)
        assert registry.count() == 1

    def test_unregister_agent(self, registry, agent):
        """Test agent unregistration."""
        registry.register(agent)
        registry.unregister(agent.agent_id)
        assert not registry.exists(agent.agent_id)
        assert registry.count() == 0

    def test_get_agent(self, registry, agent):
        """Test getting agent by ID."""
        registry.register(agent)
        retrieved = registry.get(agent.agent_id)
        assert retrieved.agent_id == agent.agent_id

    def test_get_nonexistent_agent(self, registry):
        """Test getting nonexistent agent raises error."""
        with pytest.raises(AgentNotFoundError):
            registry.get("nonexistent-agent")

    def test_duplicate_registration(self, registry, agent):
        """Test duplicate registration raises error."""
        registry.register(agent)
        with pytest.raises(AgentAlreadyRegisteredError):
            registry.register(agent)

    def test_list_all_agents(self, registry):
        """Test listing all agents."""
        config = AgentConfiguration()
        agent1 = MockAgent("agent-1", "Agent 1", AgentType.CONVERSATIONAL, config)
        agent2 = MockAgent("agent-2", "Agent 2", AgentType.TASK_EXECUTOR, config)
        
        registry.register(agent1)
        registry.register(agent2)
        
        agents = registry.list_all()
        assert len(agents) == 2

    def test_list_by_type(self, registry):
        """Test listing agents by type."""
        config = AgentConfiguration()
        agent1 = MockAgent("agent-1", "Agent 1", AgentType.CONVERSATIONAL, config)
        agent2 = MockAgent("agent-2", "Agent 2", AgentType.TASK_EXECUTOR, config)
        
        registry.register(agent1)
        registry.register(agent2)
        
        conversational = registry.list_by_type(AgentType.CONVERSATIONAL)
        assert len(conversational) == 1
        assert conversational[0].agent_id == "agent-1"

    def test_list_by_state(self, registry, agent):
        """Test listing agents by state."""
        registry.register(agent)
        
        created = registry.list_by_state(AgentState.CREATED)
        assert len(created) == 1

    def test_update_state_index(self, registry, agent):
        """Test state index update."""
        registry.register(agent)
        old_state = AgentState.CREATED
        new_state = AgentState.ACTIVE
        
        registry.update_state_index(agent.agent_id, old_state, new_state)
        
        active = registry.list_by_state(new_state)
        assert len(active) == 1

    def test_get_stats(self, registry):
        """Test registry statistics."""
        config = AgentConfiguration()
        agent1 = MockAgent("agent-1", "Agent 1", AgentType.CONVERSATIONAL, config)
        agent2 = MockAgent("agent-2", "Agent 2", AgentType.TASK_EXECUTOR, config)
        
        registry.register(agent1)
        registry.register(agent2)
        
        stats = registry.get_stats()
        assert stats["total_agents"] == 2
        assert "by_type" in stats
        assert "by_state" in stats

    def test_clear_registry(self, registry, agent):
        """Test clearing registry."""
        registry.register(agent)
        registry.clear()
        assert registry.count() == 0


@pytest.mark.unit
class TestGlobalRegistry:
    """Test global registry functions."""

    def test_get_global_registry(self):
        """Test getting global registry."""
        reset_global_registry()
        registry = get_global_registry()
        assert registry is not None
        assert isinstance(registry, AgentRegistry)

    def test_global_registry_singleton(self):
        """Test global registry is singleton."""
        reset_global_registry()
        registry1 = get_global_registry()
        registry2 = get_global_registry()
        assert registry1 is registry2

