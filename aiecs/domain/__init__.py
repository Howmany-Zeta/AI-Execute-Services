"""Domain layer module

Contains business logic and domain models.
"""

from .execution.model import TaskStepResult, TaskStatus, ErrorCode
from .task.model import TaskContext, DSLStep
from .task.dsl_processor import DSLProcessor
from .context import (
    ContextEngine, SessionMetrics, ConversationMessage,
    ConversationParticipant, ConversationSession, AgentCommunicationMessage,
    create_session_key, validate_conversation_isolation_pattern
)

__all__ = [
    # Execution domain
    "TaskStepResult",
    "TaskStatus",
    "ErrorCode",

    # Task domain
    "TaskContext",
    "DSLStep",
    "DSLProcessor",

    # Context domain
    "ContextEngine",
    "SessionMetrics",
    "ConversationMessage",
    "ConversationParticipant",
    "ConversationSession",
    "AgentCommunicationMessage",
    "create_session_key",
    "validate_conversation_isolation_pattern",
]
