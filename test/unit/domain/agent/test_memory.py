"""
Unit tests for conversation memory.
"""

import pytest
from aiecs.domain.agent.memory import ConversationMemory, Session
from aiecs.llm import LLMMessage


@pytest.mark.unit
class TestConversationMemory:
    """Test ConversationMemory."""

    @pytest.fixture
    def memory(self):
        """Create conversation memory."""
        return ConversationMemory(agent_id="test-agent-1")

    def test_create_session(self, memory):
        """Test creating session."""
        session_id = memory.create_session()
        assert session_id is not None
        assert memory.get_session(session_id) is not None

    def test_create_session_with_id(self, memory):
        """Test creating session with custom ID."""
        session_id = memory.create_session("custom-session-1")
        assert session_id == "custom-session-1"

    def test_add_message(self, memory):
        """Test adding message."""
        session_id = memory.create_session()
        memory.add_message(session_id, "user", "Hello")
        history = memory.get_history(session_id)
        assert len(history) == 1
        assert history[0].role == "user"
        assert history[0].content == "Hello"

    def test_get_history(self, memory):
        """Test getting conversation history."""
        session_id = memory.create_session()
        memory.add_message(session_id, "user", "Hello")
        memory.add_message(session_id, "assistant", "Hi there!")
        
        history = memory.get_history(session_id)
        assert len(history) == 2

    def test_get_history_with_limit(self, memory):
        """Test getting history with limit."""
        session_id = memory.create_session()
        for i in range(5):
            memory.add_message(session_id, "user", f"Message {i}")
        
        history = memory.get_history(session_id, limit=2)
        assert len(history) == 2

    def test_format_history(self, memory):
        """Test formatting history."""
        session_id = memory.create_session()
        memory.add_message(session_id, "user", "Hello")
        memory.add_message(session_id, "assistant", "Hi!")
        
        formatted = memory.format_history(session_id)
        assert "Hello" in formatted
        assert "Hi!" in formatted

    def test_clear_session(self, memory):
        """Test clearing session."""
        session_id = memory.create_session()
        memory.add_message(session_id, "user", "Hello")
        memory.clear_session(session_id)
        assert len(memory.get_history(session_id)) == 0

    def test_delete_session(self, memory):
        """Test deleting session."""
        session_id = memory.create_session()
        memory.delete_session(session_id)
        assert memory.get_session(session_id) is None

    def test_list_sessions(self, memory):
        """Test listing sessions."""
        session1 = memory.create_session()
        session2 = memory.create_session()
        sessions = memory.list_sessions()
        assert len(sessions) == 2
        assert session1 in sessions
        assert session2 in sessions

    def test_session_cleanup(self, memory):
        """Test session cleanup when limit exceeded."""
        memory = ConversationMemory(agent_id="test-agent-1", max_sessions=2)
        session1 = memory.create_session()
        session2 = memory.create_session()
        session3 = memory.create_session()  # Should trigger cleanup
        
        sessions = memory.list_sessions()
        # At least one old session should be removed
        assert len(sessions) <= 2

    def test_get_stats(self, memory):
        """Test getting memory statistics."""
        session_id = memory.create_session()
        memory.add_message(session_id, "user", "Hello")
        memory.add_message(session_id, "assistant", "Hi!")
        
        stats = memory.get_stats()
        assert stats["total_sessions"] == 1
        assert stats["total_messages"] == 2


@pytest.mark.unit
class TestSession:
    """Test Session model."""

    def test_session_creation(self):
        """Test session creation."""
        session = Session(session_id="session-1", agent_id="agent-1")
        assert session.session_id == "session-1"
        assert session.agent_id == "agent-1"
        assert len(session.messages) == 0

    def test_add_message(self):
        """Test adding message to session."""
        session = Session(session_id="session-1", agent_id="agent-1")
        session.add_message("user", "Hello")
        assert len(session.messages) == 1
        assert session.messages[0].role == "user"
        assert session.messages[0].content == "Hello"

    def test_get_recent_messages(self):
        """Test getting recent messages."""
        session = Session(session_id="session-1", agent_id="agent-1")
        for i in range(5):
            session.add_message("user", f"Message {i}")
        
        recent = session.get_recent_messages(2)
        assert len(recent) == 2

    def test_clear_session(self):
        """Test clearing session."""
        session = Session(session_id="session-1", agent_id="agent-1")
        session.add_message("user", "Hello")
        session.clear()
        assert len(session.messages) == 0

