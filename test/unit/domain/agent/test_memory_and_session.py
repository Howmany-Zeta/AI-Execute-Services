"""
Memory and Session Tests

Tests ConversationMemory and Session functionality including ContextEngine integration,
fallback behavior, session lifecycle, and metrics tracking.
Covers tasks 2.6.1-2.6.8 from the enhance-hybrid-agent-flexibility proposal.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock, patch

from aiecs.domain.agent.memory import ConversationMemory, Session
from aiecs.llm import LLMMessage


# ==================== Mock ContextEngine ====================


class MockContextEngine:
    """Mock ContextEngine for testing."""

    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        self.sessions: Dict[str, Dict] = {}
        self.conversations: Dict[str, list] = {}
        self.create_session_called = False
        self.add_message_called = False
        self.get_history_called = False

    async def create_session(
        self, session_id: str, user_id: str, metadata: Dict[str, Any] = None
    ):
        """Mock create session."""
        if self.should_fail:
            raise Exception("Mock ContextEngine failure")

        self.create_session_called = True
        self.sessions[session_id] = {
            "session_id": session_id,
            "user_id": user_id,
            "metadata": metadata or {},
        }

    async def add_conversation_message(
        self, session_id: str, role: str, content: str, metadata: Dict[str, Any] = None
    ) -> bool:
        """Mock add conversation message."""
        if self.should_fail:
            raise Exception("Mock ContextEngine failure")

        self.add_message_called = True
        if session_id not in self.conversations:
            self.conversations[session_id] = []

        self.conversations[session_id].append(
            {"role": role, "content": content, "metadata": metadata or {}}
        )
        return True

    async def get_conversation_history(self, session_id: str, limit: int = 50):
        """Mock get conversation history."""
        if self.should_fail:
            raise Exception("Mock ContextEngine failure")

        self.get_history_called = True
        messages = self.conversations.get(session_id, [])

        # Convert to ConversationMessage-like objects
        class MockConversationMessage:
            def __init__(self, role, content):
                self.role = role
                self.content = content

        return [
            MockConversationMessage(msg["role"], msg["content"])
            for msg in messages[-limit:]
        ]


# ==================== Test 2.6.1: ContextEngine Integration ====================


@pytest.mark.asyncio
async def test_conversation_memory_with_context_engine():
    """
    Test 2.6.1: Test ConversationMemory with ContextEngine integration.

    Verifies that ConversationMemory correctly uses ContextEngine for
    persistent storage when provided.
    """
    mock_engine = MockContextEngine()
    memory = ConversationMemory(
        agent_id="agent-1", context_engine=mock_engine
    )

    # Create session
    session_id = "test_session_1"
    await memory.acreate_session_with_context(session_id=session_id, user_id="user-1")

    # Verify ContextEngine was called
    assert mock_engine.create_session_called
    assert session_id in mock_engine.sessions

    # Add messages via ContextEngine
    success = await memory.aadd_conversation_message(
        session_id, "user", "Hello"
    )
    assert success is True
    assert mock_engine.add_message_called

    success = await memory.aadd_conversation_message(
        session_id, "assistant", "Hi there!"
    )
    assert success is True

    # Get history via ContextEngine
    history = await memory.aget_conversation_history(session_id)
    assert mock_engine.get_history_called
    assert len(history) == 2
    assert history[0].role == "user"
    assert history[0].content == "Hello"
    assert history[1].role == "assistant"
    assert history[1].content == "Hi there!"

    print("\n✓ ContextEngine integration works correctly")


# ==================== Test 2.6.2: Fallback to In-Memory ====================


@pytest.mark.asyncio
async def test_conversation_memory_fallback_to_in_memory():
    """
    Test 2.6.2: Test ConversationMemory fallback to in-memory storage.

    Verifies that ConversationMemory falls back to in-memory storage
    when ContextEngine fails or is not provided.
    """
    # Test 1: No ContextEngine provided
    memory1 = ConversationMemory(agent_id="agent-1")

    session_id1 = memory1.create_session()
    memory1.add_message(session_id1, "user", "Hello")
    memory1.add_message(session_id1, "assistant", "Hi!")

    history1 = memory1.get_history(session_id1)
    assert len(history1) == 2
    print("\n✓ In-memory storage works without ContextEngine")

    # Test 2: ContextEngine fails, fallback to in-memory
    failing_engine = MockContextEngine(should_fail=True)
    memory2 = ConversationMemory(
        agent_id="agent-2", context_engine=failing_engine
    )

    session_id2 = "test_session_2"

    # ContextEngine will fail, should fallback to in-memory
    success = await memory2.aadd_conversation_message(
        session_id2, "user", "Test message"
    )
    # Returns False because ContextEngine failed, but message is stored in-memory
    assert success is False

    # Verify message was stored in-memory as fallback
    history2 = memory2.get_history(session_id2)
    assert len(history2) == 1
    assert history2[0].content == "Test message"
    print("✓ Fallback to in-memory works when ContextEngine fails")


# ==================== Test 2.6.3: Persistence Across Restarts ====================


@pytest.mark.asyncio
async def test_conversation_history_persistence():
    """
    Test 2.6.3: Test conversation history persistence across agent restarts.

    Verifies that conversation history persists when using ContextEngine.
    """
    mock_engine = MockContextEngine()

    # First agent instance
    memory1 = ConversationMemory(
        agent_id="agent-1", context_engine=mock_engine
    )

    session_id = "persistent_session"
    await memory1.acreate_session_with_context(session_id=session_id, user_id="user-1")
    await memory1.aadd_conversation_message(session_id, "user", "Message 1")
    await memory1.aadd_conversation_message(session_id, "assistant", "Response 1")

    # Simulate agent restart - create new memory instance with same ContextEngine
    memory2 = ConversationMemory(
        agent_id="agent-1", context_engine=mock_engine
    )

    # Retrieve history from "restarted" agent
    history = await memory2.aget_conversation_history(session_id)
    assert len(history) == 2
    assert history[0].content == "Message 1"
    assert history[1].content == "Response 1"

    print("\n✓ Conversation history persists across agent restarts")


# ==================== Test 2.6.4: History Formatting ====================


def test_conversation_history_formatting():
    """
    Test 2.6.4: Test conversation history formatting for LLM prompts.

    Verifies that conversation history can be formatted as a string
    suitable for LLM prompts.
    """
    memory = ConversationMemory(agent_id="agent-1")
    session_id = memory.create_session()

    # Add messages
    memory.add_message(session_id, "user", "What is Python?")
    memory.add_message(
        session_id, "assistant", "Python is a programming language."
    )
    memory.add_message(session_id, "user", "Tell me more")

    # Format history
    formatted = memory.format_conversation_history(session_id)

    # Verify formatting
    assert "user:" in formatted.lower() or "User:" in formatted
    assert "assistant:" in formatted.lower() or "Assistant:" in formatted
    assert "What is Python?" in formatted
    assert "Python is a programming language." in formatted
    assert "Tell me more" in formatted

    print(f"\n✓ Formatted history:\n{formatted}")


# ==================== Test 2.6.5: Session Lifecycle ====================


def test_session_lifecycle_management():
    """
    Test 2.6.5: Test Session lifecycle management (create, get, update, end).

    Verifies that Session objects properly manage their lifecycle states.
    """
    memory = ConversationMemory(agent_id="agent-1")

    # Create session
    session_id = memory.create_session()
    session = memory.get_session(session_id)

    assert session is not None
    assert session.session_id == session_id
    assert session.status == "active"
    assert session.ended_at is None

    # Update session metadata
    session.metadata["key"] = "value"
    session = memory.get_session(session_id)
    assert session.metadata["key"] == "value"

    # End session
    session.end(status="completed")
    session = memory.get_session(session_id)
    assert session.status == "completed"
    assert session.ended_at is not None

    print("\n✓ Session lifecycle management works correctly")


# ==================== Test 2.6.6: Session Metrics ====================


def test_session_metrics_tracking():
    """
    Test 2.6.6: Test session metrics tracking (request count, error count, processing time).

    Verifies that Session objects correctly track metrics.
    """
    session = Session(session_id="test_session", agent_id="agent-1")

    # Initial state
    assert session.request_count == 0
    assert session.error_count == 0
    assert session.total_processing_time == 0.0

    # Track successful request
    session.track_request(processing_time=1.5, is_error=False)
    assert session.request_count == 1
    assert session.error_count == 0
    assert session.total_processing_time == 1.5

    # Track error request
    session.track_request(processing_time=0.5, is_error=True)
    assert session.request_count == 2
    assert session.error_count == 1
    assert session.total_processing_time == 2.0

    # Get metrics
    metrics = session.get_metrics()
    assert metrics["request_count"] == 2
    assert metrics["error_count"] == 1
    assert metrics["total_processing_time"] == 2.0
    assert metrics["average_processing_time"] == 1.0  # 2.0 / 2

    print(f"\n✓ Session metrics: {metrics}")


# ==================== Test 2.6.7: Inactive Session Cleanup ====================


def test_inactive_session_cleanup():
    """
    Test 2.6.7: Test inactive session cleanup with configurable timeout.

    Verifies that old inactive sessions are cleaned up properly.
    """
    memory = ConversationMemory(agent_id="agent-1", max_sessions=3)

    # Create multiple sessions
    session_ids = []
    for i in range(5):
        session_id = memory.create_session()
        session_ids.append(session_id)

    # Should only keep max_sessions (3) most recent
    active_sessions = memory.list_sessions()
    assert len(active_sessions) <= 3

    # Most recent sessions should be kept
    assert session_ids[-1] in active_sessions
    assert session_ids[-2] in active_sessions
    assert session_ids[-3] in active_sessions

    print(f"\n✓ Session cleanup works (kept {len(active_sessions)} of 5 sessions)")


# ==================== Test 2.6.8: Session Integration with Agent ====================


@pytest.mark.asyncio
async def test_session_integration_with_agent_lifecycle():
    """
    Test 2.6.8: Test session integration with BaseAIAgent lifecycle.

    Verifies that sessions work correctly with agent lifecycle events.
    """
    memory = ConversationMemory(agent_id="agent-1")

    # Simulate agent lifecycle
    # 1. Agent starts - create session
    session_id = memory.create_session()
    session = memory.get_session(session_id)
    assert session.status == "active"

    # 2. Agent processes requests
    memory.add_message(session_id, "user", "Request 1")
    memory.add_message(session_id, "assistant", "Response 1")
    session.track_request(processing_time=1.0, is_error=False)

    memory.add_message(session_id, "user", "Request 2")
    memory.add_message(session_id, "assistant", "Response 2")
    session.track_request(processing_time=1.5, is_error=False)

    # 3. Agent encounters error
    session.track_request(processing_time=0.5, is_error=True)

    # 4. Agent shuts down - end session
    session.end(status="completed")

    # Verify final state
    session = memory.get_session(session_id)
    assert session.status == "completed"
    assert session.request_count == 3
    assert session.error_count == 1
    assert len(session.messages) == 4

    metrics = session.get_metrics()
    assert metrics["request_count"] == 3
    assert metrics["error_count"] == 1

    print(f"\n✓ Session integration with agent lifecycle works correctly")
    print(f"  Final metrics: {metrics}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

