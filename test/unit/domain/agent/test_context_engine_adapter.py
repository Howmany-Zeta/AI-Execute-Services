"""
Unit tests for ContextEngineAdapter.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from aiecs.domain.agent.integration.context_engine_adapter import ContextEngineAdapter
from aiecs.domain.agent.models import AgentState, AgentType, AgentConfiguration
from .test_base_agent import MockAgent


@pytest.mark.unit
@pytest.mark.asyncio
class TestContextEngineAdapter:
    """Test ContextEngineAdapter functionality."""

    @pytest.fixture
    def mock_context_engine(self):
        """Create mock ContextEngine."""
        engine = MagicMock()
        engine.store_checkpoint = AsyncMock(return_value=True)
        engine.get_checkpoint = AsyncMock(return_value=None)
        engine.list_checkpoints = AsyncMock(return_value=[])
        engine.create_session = AsyncMock(return_value=MagicMock())
        engine.get_session = AsyncMock(return_value=None)
        engine.add_conversation_message = AsyncMock(return_value=True)
        engine.get_conversation_history = AsyncMock(return_value=[])
        return engine

    @pytest.fixture
    def adapter(self, mock_context_engine):
        """Create ContextEngineAdapter."""
        return ContextEngineAdapter(context_engine=mock_context_engine, user_id="test_user")

    def test_init_requires_context_engine(self):
        """Test that adapter requires ContextEngine instance."""
        with pytest.raises(ValueError, match="ContextEngine instance is required"):
            ContextEngineAdapter(context_engine=None)

    def test_init_success(self, mock_context_engine):
        """Test successful initialization."""
        adapter = ContextEngineAdapter(context_engine=mock_context_engine)
        assert adapter.context_engine == mock_context_engine
        assert adapter.user_id == "system"

    @pytest.mark.asyncio
    async def test_save_agent_state(self, adapter, mock_context_engine):
        """Test saving agent state."""
        agent_id = "test-agent-1"
        state = {"agent_id": agent_id, "name": "Test Agent", "state": "active"}

        version = await adapter.save_agent_state(agent_id, state)

        assert version is not None
        mock_context_engine.store_checkpoint.assert_called_once()
        call_args = mock_context_engine.store_checkpoint.call_args
        assert call_args[1]["thread_id"] == agent_id
        assert "checkpoint_id" in call_args[1]

    @pytest.mark.asyncio
    async def test_save_agent_state_with_version(self, adapter, mock_context_engine):
        """Test saving agent state with explicit version."""
        agent_id = "test-agent-1"
        state = {"agent_id": agent_id, "name": "Test Agent"}
        version = "v1.0"

        result_version = await adapter.save_agent_state(agent_id, state, version=version)

        assert result_version == version
        mock_context_engine.store_checkpoint.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_agent_state(self, adapter, mock_context_engine):
        """Test loading agent state."""
        agent_id = "test-agent-1"
        state = {"agent_id": agent_id, "name": "Test Agent"}
        
        # Mock checkpoint with state
        mock_context_engine.get_checkpoint = AsyncMock(return_value={
            "data": {
                "agent_id": agent_id,
                "state": state,
                "version": "v1",
                "timestamp": "2024-01-01T00:00:00"
            },
            "metadata": {"type": "agent_state"}
        })

        loaded_state = await adapter.load_agent_state(agent_id)

        assert loaded_state == state
        mock_context_engine.get_checkpoint.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_agent_state_not_found(self, adapter, mock_context_engine):
        """Test loading non-existent agent state."""
        mock_context_engine.get_checkpoint = AsyncMock(return_value=None)

        loaded_state = await adapter.load_agent_state("nonexistent-agent")

        assert loaded_state is None

    @pytest.mark.asyncio
    async def test_list_agent_versions(self, adapter, mock_context_engine):
        """Test listing agent versions."""
        agent_id = "test-agent-1"
        mock_context_engine.list_checkpoints = AsyncMock(return_value=[
            {
                "data": {
                    "version": "v1",
                    "timestamp": "2024-01-02T00:00:00"
                },
                "metadata": {"type": "agent_state"}
            },
            {
                "data": {
                    "version": "v2",
                    "timestamp": "2024-01-01T00:00:00"
                },
                "metadata": {"type": "agent_state"}
            }
        ])

        versions = await adapter.list_agent_versions(agent_id)

        assert len(versions) == 2
        assert versions[0]["version"] == "v1"  # Sorted by timestamp descending
        assert versions[1]["version"] == "v2"

    @pytest.mark.asyncio
    async def test_save_conversation_history(self, adapter, mock_context_engine):
        """Test saving conversation history."""
        session_id = "session-1"
        messages = [
            {"role": "user", "content": "Hello", "metadata": {}},
            {"role": "assistant", "content": "Hi there!", "metadata": {}}
        ]

        await adapter.save_conversation_history(session_id, messages)

        # Should create session if doesn't exist
        mock_context_engine.get_session.assert_called_once_with(session_id)
        # Should add each message
        assert mock_context_engine.add_conversation_message.call_count == 2

    @pytest.mark.asyncio
    async def test_load_conversation_history(self, adapter, mock_context_engine):
        """Test loading conversation history."""
        from aiecs.domain.context.context_engine import ConversationMessage
        from datetime import datetime

        session_id = "session-1"
        messages = [
            ConversationMessage(
                role="user",
                content="Hello",
                timestamp=datetime.utcnow(),
                metadata={}
            ),
            ConversationMessage(
                role="assistant",
                content="Hi there!",
                timestamp=datetime.utcnow(),
                metadata={}
            )
        ]
        mock_context_engine.get_conversation_history = AsyncMock(return_value=messages)

        loaded_messages = await adapter.load_conversation_history(session_id, limit=50)

        assert len(loaded_messages) == 2
        assert loaded_messages[0]["role"] == "user"
        assert loaded_messages[0]["content"] == "Hello"
        assert loaded_messages[1]["role"] == "assistant"
        assert loaded_messages[1]["content"] == "Hi there!"

    @pytest.mark.asyncio
    async def test_delete_agent_state(self, adapter, mock_context_engine):
        """Test deleting agent state."""
        agent_id = "test-agent-1"
        version = "v1.0"

        await adapter.delete_agent_state(agent_id, version=version)

        mock_context_engine.store_checkpoint.assert_called_once()
        call_args = mock_context_engine.store_checkpoint.call_args
        assert f"{version}_deleted" in call_args[1]["checkpoint_id"]

    @pytest.mark.asyncio
    async def test_save_load_agent_persistence_protocol(self, adapter, mock_context_engine):
        """Test AgentPersistence protocol implementation."""
        config = AgentConfiguration()
        agent = MockAgent(
            agent_id="test-agent-1",
            name="Test Agent",
            agent_type=AgentType.CONVERSATIONAL,
            config=config
        )

        # Mock checkpoint for load
        mock_context_engine.get_checkpoint = AsyncMock(return_value={
            "data": {
                "agent_id": agent.agent_id,
                "state": agent.to_dict(),
                "version": "v1"
            }
        })

        # Test save
        await adapter.save(agent)
        mock_context_engine.store_checkpoint.assert_called()

        # Test exists
        exists = await adapter.exists(agent.agent_id)
        assert exists is True

        # Test load
        loaded_state = await adapter.load(agent.agent_id)
        assert loaded_state is not None
        assert loaded_state["agent_id"] == agent.agent_id

    @pytest.mark.asyncio
    async def test_load_nonexistent_agent(self, adapter, mock_context_engine):
        """Test loading non-existent agent raises KeyError."""
        mock_context_engine.get_checkpoint = AsyncMock(return_value=None)

        with pytest.raises(KeyError, match="not found in storage"):
            await adapter.load("nonexistent-agent")

