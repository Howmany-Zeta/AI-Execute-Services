"""
Context Management Domain

This module provides advanced context and session management capabilities
for the Python middleware application.

Components:
- ContextEngine: Advanced context and session management with Redis backend
- Integration with TaskContext for enhanced functionality
- Support for BaseServiceCheckpointer and LangGraph workflows
"""

from .context_engine import ContextEngine, SessionMetrics, ConversationMessage
from .conversation_models import (
    ConversationParticipant, ConversationSession, AgentCommunicationMessage,
    create_session_key, validate_conversation_isolation_pattern
)

__all__ = [
    'ContextEngine',
    'SessionMetrics',
    'ConversationMessage',
    'ConversationParticipant',
    'ConversationSession',
    'AgentCommunicationMessage',
    'create_session_key',
    'validate_conversation_isolation_pattern'
]
