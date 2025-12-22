"""
Unit tests for agent persistence.
"""

import pytest
import os
import tempfile
import shutil
from aiecs.domain.agent.persistence import (
    InMemoryPersistence,
    FilePersistence,
    AgentStateSerializer,
    get_global_persistence,
    set_global_persistence,
    reset_global_persistence
)
from aiecs.domain.agent.models import AgentState, AgentType, AgentConfiguration
from .test_base_agent import MockAgent


@pytest.mark.unit
@pytest.mark.asyncio
class TestInMemoryPersistence:
    """Test InMemoryPersistence."""

    @pytest.fixture
    def persistence(self):
        """Create in-memory persistence."""
        return InMemoryPersistence()

    @pytest.fixture
    def agent(self):
        """Create test agent."""
        config = AgentConfiguration()
        agent = MockAgent(
            agent_id="test-agent-1",
            name="Test Agent",
            agent_type=AgentType.CONVERSATIONAL,
            config=config
        )
        return agent

    async def test_save_and_load(self, persistence, agent):
        """Test saving and loading agent."""
        await persistence.save(agent)
        
        loaded = await persistence.load(agent.agent_id)
        assert loaded["agent_id"] == agent.agent_id
        assert loaded["name"] == agent.name

    async def test_exists(self, persistence, agent):
        """Test checking existence."""
        assert not await persistence.exists(agent.agent_id)
        await persistence.save(agent)
        assert await persistence.exists(agent.agent_id)

    async def test_delete(self, persistence, agent):
        """Test deleting agent."""
        await persistence.save(agent)
        await persistence.delete(agent.agent_id)
        assert not await persistence.exists(agent.agent_id)

    def test_clear(self, persistence, agent):
        """Test clearing persistence."""
        persistence._storage[agent.agent_id] = {"state": agent.to_dict()}
        persistence.clear()
        assert len(persistence._storage) == 0


@pytest.mark.unit
@pytest.mark.asyncio
class TestFilePersistence:
    """Test FilePersistence."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def persistence(self, temp_dir):
        """Create file persistence."""
        return FilePersistence(base_path=temp_dir)

    @pytest.fixture
    def agent(self):
        """Create test agent."""
        config = AgentConfiguration()
        agent = MockAgent(
            agent_id="test-agent-1",
            name="Test Agent",
            agent_type=AgentType.CONVERSATIONAL,
            config=config
        )
        return agent

    async def test_save_and_load(self, persistence, agent):
        """Test saving and loading agent."""
        await persistence.save(agent)
        
        loaded = await persistence.load(agent.agent_id)
        assert loaded["agent_id"] == agent.agent_id

    async def test_exists(self, persistence, agent):
        """Test checking existence."""
        assert not await persistence.exists(agent.agent_id)
        await persistence.save(agent)
        assert await persistence.exists(agent.agent_id)

    async def test_delete(self, persistence, agent):
        """Test deleting agent."""
        await persistence.save(agent)
        await persistence.delete(agent.agent_id)
        assert not await persistence.exists(agent.agent_id)

    async def test_load_nonexistent(self, persistence):
        """Test loading nonexistent agent."""
        with pytest.raises(KeyError):
            await persistence.load("nonexistent-agent")


@pytest.mark.unit
class TestAgentStateSerializer:
    """Test AgentStateSerializer."""

    def test_serialize(self):
        """Test serializing agent."""
        from aiecs.domain.agent.models import AgentConfiguration
        config = AgentConfiguration()
        agent = MockAgent(
            agent_id="test-agent-1",
            name="Test Agent",
            agent_type=AgentType.CONVERSATIONAL,
            config=config
        )
        
        data = AgentStateSerializer.serialize(agent)
        assert data["agent_id"] == agent.agent_id

    def test_deserialize(self):
        """Test deserializing agent state."""
        data = {
            "agent_id": "test-agent-1",
            "name": "Test Agent",
            "state": "created"
        }
        
        deserialized = AgentStateSerializer.deserialize(data)
        assert deserialized["agent_id"] == "test-agent-1"


@pytest.mark.unit
class TestGlobalPersistence:
    """Test global persistence functions."""

    def test_get_global_persistence(self):
        """Test getting global persistence."""
        reset_global_persistence()
        persistence = get_global_persistence()
        assert persistence is not None
        assert isinstance(persistence, InMemoryPersistence)

    def test_set_global_persistence(self):
        """Test setting global persistence."""
        reset_global_persistence()
        new_persistence = InMemoryPersistence()
        set_global_persistence(new_persistence)
        assert get_global_persistence() is new_persistence

