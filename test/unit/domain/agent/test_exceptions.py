"""
Unit tests for agent exceptions.
"""

import pytest
from aiecs.domain.agent.exceptions import (
    AgentException,
    AgentNotFoundError,
    AgentAlreadyRegisteredError,
    InvalidStateTransitionError,
    ConfigurationError,
    TaskExecutionError,
    ToolAccessDeniedError,
    SerializationError,
    AgentInitializationError,
)


@pytest.mark.unit
class TestAgentExceptions:
    """Test agent exception classes."""

    def test_agent_exception(self):
        """Test base AgentException."""
        exc = AgentException("Test error")
        assert str(exc) == "Test error"
        assert isinstance(exc, Exception)

    def test_agent_not_found_error(self):
        """Test AgentNotFoundError."""
        exc = AgentNotFoundError("agent-1")
        assert "agent-1" in str(exc)
        assert isinstance(exc, AgentException)

    def test_agent_already_registered_error(self):
        """Test AgentAlreadyRegisteredError."""
        exc = AgentAlreadyRegisteredError("agent-1")
        assert "agent-1" in str(exc)
        assert isinstance(exc, AgentException)

    def test_invalid_state_transition_error(self):
        """Test InvalidStateTransitionError."""
        exc = InvalidStateTransitionError("created", "active", "agent-1")
        assert "created" in str(exc)
        assert "active" in str(exc)
        assert isinstance(exc, AgentException)

    def test_task_execution_error(self):
        """Test TaskExecutionError."""
        exc = TaskExecutionError("Task failed", agent_id="agent-1", task_id="task-1")
        assert "Task failed" in str(exc)
        assert exc.agent_id == "agent-1"
        assert exc.task_id == "task-1"
        assert isinstance(exc, AgentException)

    def test_tool_access_denied_error(self):
        """Test ToolAccessDeniedError."""
        exc = ToolAccessDeniedError("agent-1", "tool-1")
        assert "agent-1" in str(exc)
        assert "tool-1" in str(exc)
        assert isinstance(exc, AgentException)

    def test_serialization_error(self):
        """Test SerializationError."""
        exc = SerializationError("Serialization failed")
        assert "Serialization failed" in str(exc)
        assert isinstance(exc, AgentException)

    def test_agent_initialization_error(self):
        """Test AgentInitializationError."""
        exc = AgentInitializationError("Init failed", agent_id="agent-1")
        assert "Init failed" in str(exc)
        assert exc.agent_id == "agent-1"
        assert isinstance(exc, AgentException)

