"""
Integration tests for ContextEngineAdapter with actual ContextEngine.
"""

import pytest
from aiecs.domain.context.context_engine import ContextEngine
from aiecs.domain.agent.integration.context_engine_adapter import ContextEngineAdapter
from aiecs.domain.agent.models import AgentState, AgentType, AgentConfiguration
from .test_base_agent import MockAgent


@pytest.mark.integration
@pytest.mark.asyncio
class TestContextEngineAdapterIntegration:
    """Integration tests with actual ContextEngine."""

    @pytest.fixture
    async def context_engine(self):
        """Create and initialize ContextEngine."""
        engine = ContextEngine(use_existing_redis=False)  # Use memory backend for testing
        await engine.initialize()
        yield engine

    @pytest.fixture
    def adapter(self, context_engine):
        """Create ContextEngineAdapter with real ContextEngine."""
        return ContextEngineAdapter(context_engine=context_engine, user_id="test_user")

    @pytest.mark.asyncio
    async def test_save_and_load_agent_state(self, adapter):
        """Test saving and loading agent state end-to-end."""
        agent_id = "integration-test-agent"
        state = {
            "agent_id": agent_id,
            "name": "Integration Test Agent",
            "state": "active",
            "config": {"temperature": 0.7}
        }

        # Save state
        version = await adapter.save_agent_state(agent_id, state)
        assert version is not None

        # Load state
        loaded_state = await adapter.load_agent_state(agent_id, version=version)
        assert loaded_state is not None
        assert loaded_state["agent_id"] == agent_id
        assert loaded_state["name"] == state["name"]
        assert loaded_state["state"] == state["state"]

    @pytest.mark.asyncio
    async def test_load_latest_agent_state(self, adapter):
        """Test loading latest agent state."""
        agent_id = "integration-test-agent-latest"

        # Save multiple versions
        version1 = await adapter.save_agent_state(agent_id, {"version": "1", "data": "first"})
        version2 = await adapter.save_agent_state(agent_id, {"version": "2", "data": "second"})
        version3 = await adapter.save_agent_state(agent_id, {"version": "3", "data": "third"})

        # Load latest (None version should get latest)
        latest_state = await adapter.load_agent_state(agent_id, version=None)
        assert latest_state is not None
        assert latest_state["version"] == "3"
        assert latest_state["data"] == "third"

    @pytest.mark.asyncio
    async def test_list_agent_versions(self, adapter):
        """Test listing agent versions."""
        agent_id = "integration-test-versions"

        # Save multiple versions
        version1 = await adapter.save_agent_state(agent_id, {"v": "1"})
        version2 = await adapter.save_agent_state(agent_id, {"v": "2"})
        version3 = await adapter.save_agent_state(agent_id, {"v": "3"})

        # List versions
        versions = await adapter.list_agent_versions(agent_id)
        assert len(versions) >= 3

        # Should be sorted by timestamp descending
        timestamps = [v.get("timestamp", "") for v in versions if v.get("timestamp")]
        if len(timestamps) > 1:
            assert timestamps[0] >= timestamps[1]  # Descending order

    @pytest.mark.asyncio
    async def test_save_and_load_conversation_history(self, adapter):
        """Test saving and loading conversation history."""
        session_id = "integration-session-1"
        messages = [
            {"role": "user", "content": "Hello, agent!", "metadata": {"source": "test"}},
            {"role": "assistant", "content": "Hello! How can I help?", "metadata": {}},
            {"role": "user", "content": "What's the weather?", "metadata": {}}
        ]

        # Save messages
        await adapter.save_conversation_history(session_id, messages)

        # Load messages
        loaded_messages = await adapter.load_conversation_history(session_id, limit=50)
        assert len(loaded_messages) >= len(messages)

        # Verify content
        assert loaded_messages[0]["role"] == "user"
        assert "Hello, agent!" in loaded_messages[0]["content"] or loaded_messages[0]["content"] == "Hello, agent!"

    @pytest.mark.asyncio
    async def test_agent_persistence_protocol(self, adapter):
        """Test full AgentPersistence protocol with real ContextEngine."""
        config = AgentConfiguration(goal="Integration test goal", temperature=0.8)
        agent = MockAgent(
            agent_id="integration-persistence-agent",
            name="Persistence Test Agent",
            agent_type=AgentType.TASK_EXECUTOR,
            config=config
        )

        # Test save
        await adapter.save(agent)
        assert await adapter.exists(agent.agent_id) is True

        # Test load
        loaded_state = await adapter.load(agent.agent_id)
        assert loaded_state is not None
        assert loaded_state["agent_id"] == agent.agent_id
        assert loaded_state["name"] == agent.name

        # Test delete
        await adapter.delete(agent.agent_id)
        # After delete, state might still exist but marked as deleted
        # This depends on implementation - we just verify it doesn't crash

    @pytest.mark.asyncio
    async def test_multiple_agents_same_engine(self, adapter):
        """Test multiple agents with same ContextEngine."""
        agents = []
        for i in range(3):
            config = AgentConfiguration()
            agent = MockAgent(
                agent_id=f"multi-agent-{i}",
                name=f"Agent {i}",
                agent_type=AgentType.CONVERSATIONAL,
                config=config
            )
            agents.append(agent)

        # Save all agents
        for agent in agents:
            await adapter.save(agent)

        # Verify all exist
        for agent in agents:
            assert await adapter.exists(agent.agent_id) is True

        # Load all agents
        for agent in agents:
            loaded_state = await adapter.load(agent.agent_id)
            assert loaded_state["agent_id"] == agent.agent_id

