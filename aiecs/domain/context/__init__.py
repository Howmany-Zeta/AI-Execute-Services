"""
Context Management Domain

This module provides advanced context and session management capabilities
for the Python middleware application.

Components:
- ContextEngine: Advanced context and session management with Redis backend
- Integration with TaskContext for enhanced functionality
- Support for BaseServiceCheckpointer and LangGraph workflows

Usage:
    # For creating ContextEngine instances directly:
    from aiecs.domain.context import ContextEngine
    engine = ContextEngine(use_existing_redis=True)
    await engine.initialize()

    # For using the global singleton instance (recommended):
    from aiecs.infrastructure.persistence import (
        get_context_engine,
        initialize_context_engine,
        close_context_engine
    )

    # The global instance is automatically initialized in main.py lifespan
    context_engine = get_context_engine()
    if context_engine:
        await context_engine.add_conversation_message(...)

Architecture Note:
    - This package contains DOMAIN layer classes (business logic)
    - Global instance management is in INFRASTRUCTURE layer:
      aiecs.infrastructure.persistence.context_engine_client
    - This separation follows Clean Architecture / DDD principles
"""

from .context_engine import ContextEngine, SessionMetrics, ConversationMessage
from .conversation_models import (
    ConversationParticipant,
    ConversationSession,
    AgentCommunicationMessage,
    create_session_key,
    validate_conversation_isolation_pattern,
)
from .graph_memory import GraphMemoryMixin, ContextEngineWithGraph

__all__ = [
    "ContextEngine",
    "SessionMetrics",
    "ConversationMessage",
    "ConversationParticipant",
    "ConversationSession",
    "AgentCommunicationMessage",
    "create_session_key",
    "validate_conversation_isolation_pattern",
    "GraphMemoryMixin",
    "ContextEngineWithGraph",
]
