"""
Agent Domain Exceptions

Defines agent-specific exceptions for the base AI agent model.
"""

from typing import Optional


class AgentException(Exception):
    """Base exception for agent-related errors."""

    def __init__(self, message: str, agent_id: Optional[str] = None):
        super().__init__(message)
        self.agent_id = agent_id
        self.message = message


class AgentNotFoundError(AgentException):
    """Raised when an agent cannot be found."""

    def __init__(self, agent_id: str, message: Optional[str] = None):
        msg = message or f"Agent with ID '{agent_id}' not found"
        super().__init__(msg, agent_id)


class AgentAlreadyRegisteredError(AgentException):
    """Raised when attempting to register an agent with an existing ID."""

    def __init__(self, agent_id: str):
        msg = f"Agent with ID '{agent_id}' is already registered"
        super().__init__(msg, agent_id)


class InvalidStateTransitionError(AgentException):
    """Raised when an invalid agent state transition is attempted."""

    def __init__(
        self,
        agent_id: str,
        current_state: str,
        attempted_state: str,
        message: Optional[str] = None,
    ):
        msg = message or f"Invalid state transition for agent '{agent_id}': " f"cannot transition from '{current_state}' to '{attempted_state}'"
        super().__init__(msg, agent_id)
        self.current_state = current_state
        self.attempted_state = attempted_state


class ConfigurationError(AgentException):
    """Raised when agent configuration is invalid."""

    def __init__(
        self,
        message: str,
        agent_id: Optional[str] = None,
        field: Optional[str] = None,
    ):
        super().__init__(message, agent_id)
        self.field = field


class TaskExecutionError(AgentException):
    """Raised when task execution fails."""

    def __init__(
        self,
        message: str,
        agent_id: Optional[str] = None,
        task_id: Optional[str] = None,
        retry_count: Optional[int] = None,
    ):
        super().__init__(message, agent_id)
        self.task_id = task_id
        self.retry_count = retry_count


class ToolAccessDeniedError(AgentException):
    """Raised when an agent attempts to use a tool it doesn't have access to."""

    def __init__(self, agent_id: str, tool_name: str):
        msg = f"Agent '{agent_id}' does not have access to tool '{tool_name}'"
        super().__init__(msg, agent_id)
        self.tool_name = tool_name


class SerializationError(AgentException):
    """Raised when agent serialization/deserialization fails."""

    def __init__(self, message: str, agent_id: Optional[str] = None):
        super().__init__(message, agent_id)


class AgentInitializationError(AgentException):
    """Raised when agent initialization fails."""

    def __init__(self, message: str, agent_id: Optional[str] = None):
        super().__init__(message, agent_id)
