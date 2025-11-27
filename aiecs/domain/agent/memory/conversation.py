"""
Conversation Memory

Multi-turn conversation handling with session management.
"""

import logging
from typing import Dict, List, Optional, TYPE_CHECKING, Any
from datetime import datetime
from dataclasses import dataclass, field

from aiecs.llm import LLMMessage

if TYPE_CHECKING:
    from aiecs.domain.context.context_engine import ContextEngine

logger = logging.getLogger(__name__)


@dataclass
class Session:
    """
    Conversation session with lifecycle management and metrics tracking.

    Supports both in-memory and ContextEngine-backed storage for session state.

    **Lifecycle States:**
    - active: Session is active and receiving requests
    - completed: Session ended successfully
    - failed: Session ended due to error
    - expired: Session expired due to inactivity

    **Metrics Tracking:**
    - request_count: Number of requests processed
    - error_count: Number of errors encountered
    - total_processing_time: Total processing time in seconds
    - message_count: Number of messages in conversation

    Examples:
        # Example 1: Basic session creation and usage
        session = Session(
            session_id="session-123",
            agent_id="agent-1"
        )

        # Add messages
        session.add_message("user", "Hello")
        session.add_message("assistant", "Hi there!")

        # Track request
        session.track_request(processing_time=1.5, is_error=False)

        # Get metrics
        metrics = session.get_metrics()
        print(f"Request count: {metrics['request_count']}")
        print(f"Message count: {metrics['message_count']}")

        # Example 2: Session lifecycle management
        session = Session(
            session_id="session-123",
            agent_id="agent-1"
        )

        # Session starts as active
        assert session.is_active()  # True
        assert session.status == "active"

        # Process requests
        for i in range(5):
            session.track_request(processing_time=0.5, is_error=False)

        # Track an error
        session.track_request(processing_time=0.1, is_error=True)

        # Get metrics
        metrics = session.get_metrics()
        print(f"Total requests: {metrics['request_count']}")  # 6
        print(f"Errors: {metrics['error_count']}")  # 1
        print(f"Average processing time: {metrics['average_processing_time']}s")

        # End session
        session.end(status="completed")
        assert session.status == "completed"
        assert not session.is_active()  # False

        # Example 3: Session expiration checking
        session = Session(
            session_id="session-123",
            agent_id="agent-1"
        )

        # Check if expired (default: 30 minutes idle)
        if session.is_expired(max_idle_seconds=1800):
            session.end(status="expired")
            print("Session expired due to inactivity")

        # Example 4: Session with ContextEngine integration
        from aiecs.domain.context import ContextEngine

        context_engine = ContextEngine()
        await context_engine.initialize()

        # Create session via ContextEngine
        session_metrics = await context_engine.create_session(
            session_id="session-123",
            user_id="user-456",
            metadata={"source": "web"}
        )

        # Update session metrics
        await context_engine.update_session(
            session_id="session-123",
            increment_requests=True,
            add_processing_time=1.5,
            mark_error=False
        )

        # Get session from ContextEngine
        session_metrics = await context_engine.get_session("session-123")
        if session_metrics:
            print(f"Request count: {session_metrics.request_count}")
            print(f"Error count: {session_metrics.error_count}")

        # End session
        await context_engine.end_session("session-123", status="completed")

        # Example 5: Session metrics aggregation
        session = Session(
            session_id="session-123",
            agent_id="agent-1"
        )

        # Simulate multiple requests
        processing_times = [0.5, 0.8, 1.2, 0.3, 0.9]
        for time in processing_times:
            session.track_request(processing_time=time, is_error=False)

        # Track one error
        session.track_request(processing_time=0.1, is_error=True)

        # Get comprehensive metrics
        metrics = session.get_metrics()
        print(f"Total requests: {metrics['request_count']}")  # 6
        print(f"Errors: {metrics['error_count']}")  # 1
        print(f"Total processing time: {metrics['total_processing_time']}s")
        print(f"Average processing time: {metrics['average_processing_time']}s")
        print(f"Duration: {metrics['duration_seconds']}s")
        print(f"Status: {metrics['status']}")

        # Example 6: Session cleanup based on expiration
        sessions = [
            Session(session_id=f"session-{i}", agent_id="agent-1")
            for i in range(10)
        ]

        # Mark some sessions as expired
        expired_sessions = []
        for session in sessions:
            if session.is_expired(max_idle_seconds=1800):
                session.end(status="expired")
                expired_sessions.append(session)

        print(f"Found {len(expired_sessions)} expired sessions")

        # Example 7: Session with message history
        session = Session(
            session_id="session-123",
            agent_id="agent-1"
        )

        # Add conversation messages
        session.add_message("user", "What's the weather?")
        session.add_message("assistant", "It's sunny and 72°F.")
        session.add_message("user", "What about tomorrow?")
        session.add_message("assistant", "Tomorrow will be partly cloudy, 68°F.")

        # Get recent messages
        recent = session.get_recent_messages(limit=2)
        print(f"Recent messages: {len(recent)}")  # 2

        # Get all messages
        all_messages = session.get_recent_messages(limit=None)
        print(f"Total messages: {len(all_messages)}")  # 4

        # Clear messages
        session.clear()
        assert len(session.messages) == 0
    """

    session_id: str
    agent_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    messages: List[LLMMessage] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

    # Lifecycle management fields
    status: str = field(default="active")  # active, completed, failed, expired
    ended_at: Optional[datetime] = field(default=None)

    # Session metrics fields
    request_count: int = field(default=0)
    error_count: int = field(default=0)
    total_processing_time: float = field(default=0.0)  # in seconds

    def add_message(self, role: str, content: str) -> None:
        """Add message to session."""
        self.messages.append(LLMMessage(role=role, content=content))
        self.last_activity = datetime.utcnow()

    def get_recent_messages(self, limit: int) -> List[LLMMessage]:
        """Get recent messages."""
        return self.messages[-limit:] if limit else self.messages

    def clear(self) -> None:
        """Clear session messages."""
        self.messages.clear()

    def track_request(self, processing_time: float = 0.0, is_error: bool = False) -> None:
        """
        Track a request in this session.

        Args:
            processing_time: Processing time in seconds
            is_error: Whether the request resulted in an error
        """
        self.request_count += 1
        self.total_processing_time += processing_time
        if is_error:
            self.error_count += 1
        self.last_activity = datetime.utcnow()

    def end(self, status: str = "completed") -> None:
        """
        End the session.

        Args:
            status: Final session status (completed, failed, expired)
        """
        self.status = status
        self.ended_at = datetime.utcnow()

    def get_metrics(self) -> Dict:
        """
        Get session metrics.

        Returns:
            Dictionary with session metrics
        """
        duration = ((self.ended_at or datetime.utcnow()) - self.created_at).total_seconds()
        avg_processing_time = self.total_processing_time / self.request_count if self.request_count > 0 else 0.0

        return {
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "status": self.status,
            "request_count": self.request_count,
            "error_count": self.error_count,
            "total_processing_time": self.total_processing_time,
            "average_processing_time": avg_processing_time,
            "duration_seconds": duration,
            "message_count": len(self.messages),
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
        }

    def is_active(self) -> bool:
        """Check if session is active."""
        return self.status == "active"

    def is_expired(self, max_idle_seconds: int = 1800) -> bool:
        """
        Check if session has expired due to inactivity.

        Args:
            max_idle_seconds: Maximum idle time in seconds (default: 30 minutes)

        Returns:
            True if session is expired, False otherwise
        """
        if not self.is_active():
            return False

        idle_time = (datetime.utcnow() - self.last_activity).total_seconds()
        return idle_time > max_idle_seconds


class ConversationMemory:
    """
    Manages multi-turn conversations with session isolation.

    Supports optional ContextEngine integration for persistent conversation history
    across agent restarts. Falls back to in-memory storage when ContextEngine is not provided.

    **Storage Modes:**
    - In-memory: Default mode, sessions stored in memory (lost on restart)
    - ContextEngine: Persistent storage with Redis backend (survives restarts)

    **Key Features:**
    - Session lifecycle management (create, update, end)
    - Conversation history with ContextEngine persistence
    - Session metrics tracking (request count, errors, processing time)
    - Automatic cleanup of inactive sessions
    - Both sync and async methods for flexibility

    Examples:
        # Example 1: In-memory mode (default)
        memory = ConversationMemory(agent_id="agent-1")
        session_id = memory.create_session()
        memory.add_message(session_id, "user", "Hello")
        memory.add_message(session_id, "assistant", "Hi there!")
        history = memory.get_history(session_id)

        # Example 2: ContextEngine integration for persistent storage
        from aiecs.domain.context import ContextEngine

        context_engine = ContextEngine()
        await context_engine.initialize()

        memory = ConversationMemory(agent_id="agent-1", context_engine=context_engine)

        # Create session with ContextEngine (async)
        session_id = await memory.acreate_session_with_context(
            user_id="user-123",
            metadata={"source": "web"}
        )

        # Add messages with ContextEngine (async)
        await memory.aadd_conversation_message(
            session_id=session_id,
            role="user",
            content="Hello, I need help with my order"
        )

        await memory.aadd_conversation_message(
            session_id=session_id,
            role="assistant",
            content="I'd be happy to help! What's your order number?",
            metadata={"confidence": 0.95}
        )

        # Get conversation history from ContextEngine (async)
        history = await memory.aget_conversation_history(session_id, limit=50)

        # Format history for LLM prompts
        formatted = await memory.aformat_conversation_history(session_id)

        # Example 3: Session lifecycle management with ContextEngine
        memory = ConversationMemory(agent_id="agent-1", context_engine=context_engine)

        # Create session
        session_id = await memory.acreate_session_with_context(
            user_id="user-123"
        )

        # Track requests and metrics
        await memory.update_session_with_context(
            session_id=session_id,
            increment_requests=True,
            add_processing_time=1.5,
            mark_error=False
        )

        # Get session metrics
        session = await memory.aget_session_with_context(session_id)
        metrics = session.get_metrics()
        print(f"Request count: {metrics['request_count']}")
        print(f"Average processing time: {metrics['average_processing_time']}s")

        # End session
        await memory.end_session_with_context(session_id, status="completed")

        # Example 4: Automatic cleanup of inactive sessions
        memory = ConversationMemory(agent_id="agent-1", context_engine=context_engine)

        # Clean up sessions inactive for more than 30 minutes
        cleaned_count = await memory.cleanup_inactive_sessions(max_idle_seconds=1800)
        print(f"Cleaned up {cleaned_count} inactive sessions")

        # Example 5: Conversation history persistence across restarts
        # First run: Create agent with ContextEngine
        context_engine = ContextEngine()
        await context_engine.initialize()

        memory1 = ConversationMemory(agent_id="agent-1", context_engine=context_engine)
        session_id = await memory1.acreate_session_with_context(user_id="user-123")

        await memory1.aadd_conversation_message(
            session_id=session_id,
            role="user",
            content="What's the weather today?"
        )

        await memory1.aadd_conversation_message(
            session_id=session_id,
            role="assistant",
            content="It's sunny and 72°F."
        )

        # Agent restarts...

        # Second run: Conversation history persists!
        memory2 = ConversationMemory(agent_id="agent-1", context_engine=context_engine)

        # Retrieve existing session
        session = await memory2.aget_session_with_context(session_id)
        if session:
            # Get conversation history
            history = await memory2.aget_conversation_history(session_id)
            print(f"Retrieved {len(history)} messages from previous session")

        # Example 6: Using with agents
        from aiecs.domain.agent import HybridAgent

        context_engine = ContextEngine()
        await context_engine.initialize()

        agent = HybridAgent(
            agent_id="agent-1",
            name="My Agent",
            llm_client=OpenAIClient(),
            tools=["search"],
            config=config,
            context_engine=context_engine  # Agent uses ContextEngine
        )

        # Agent automatically uses ContextEngine for conversation history
        # when context_engine is provided

        # Example 7: Sync fallback methods (for compatibility)
        memory = ConversationMemory(agent_id="agent-1", context_engine=context_engine)

        # Sync methods fall back to in-memory storage
        # (logs warning if ContextEngine is configured)
        session_id = memory.create_session()  # Falls back to in-memory
        memory.add_message(session_id, "user", "Hello")  # Falls back to in-memory

        # Use async methods for ContextEngine integration
        session_id = await memory.acreate_session_with_context(user_id="user-123")
        await memory.aadd_conversation_message(session_id, "user", "Hello")
    """

    def __init__(
        self,
        agent_id: str,
        max_sessions: int = 100,
        context_engine: Optional["ContextEngine"] = None,
    ):
        """
        Initialize conversation memory.

        Args:
            agent_id: Agent identifier
            max_sessions: Maximum number of sessions to keep (for in-memory storage)
            context_engine: Optional ContextEngine instance for persistent storage.
                          If provided, conversation history will be stored persistently.
                          If None, falls back to in-memory storage.
        """
        self.agent_id = agent_id
        self.max_sessions = max_sessions
        self.context_engine = context_engine
        self._sessions: Dict[str, Session] = {}

        if context_engine:
            logger.info(f"ConversationMemory initialized for agent {agent_id} with ContextEngine integration")
        else:
            logger.info(f"ConversationMemory initialized for agent {agent_id} (in-memory mode)")

    def create_session(self, session_id: Optional[str] = None) -> str:
        """
        Create a new conversation session.

        Args:
            session_id: Optional custom session ID

        Returns:
            Session ID
        """
        if session_id is None:
            session_id = f"session_{datetime.utcnow().timestamp()}"

        if session_id in self._sessions:
            logger.warning(f"Session {session_id} already exists")
            return session_id

        self._sessions[session_id] = Session(session_id=session_id, agent_id=self.agent_id)

        # Cleanup old sessions if limit exceeded
        if len(self._sessions) > self.max_sessions:
            self._cleanup_old_sessions()

        logger.debug(f"Session {session_id} created")
        return session_id

    def add_message(self, session_id: str, role: str, content: str) -> None:
        """
        Add message to session.

        Args:
            session_id: Session ID
            role: Message role
            content: Message content
        """
        if session_id not in self._sessions:
            logger.warning(f"Session {session_id} not found, creating it")
            self.create_session(session_id)

        self._sessions[session_id].add_message(role, content)

    def get_history(self, session_id: str, limit: Optional[int] = None) -> List[LLMMessage]:
        """
        Get conversation history for session.

        Args:
            session_id: Session ID
            limit: Optional limit on number of messages

        Returns:
            List of messages
        """
        if session_id not in self._sessions:
            return []

        session = self._sessions[session_id]
        return session.get_recent_messages(limit) if limit else session.messages.copy()

    def format_history(self, session_id: str, limit: Optional[int] = None) -> str:
        """
        Format conversation history as string.

        Args:
            session_id: Session ID
            limit: Optional limit on number of messages

        Returns:
            Formatted history string
        """
        history = self.get_history(session_id, limit)
        lines = []
        for msg in history:
            lines.append(f"{msg.role.upper()}: {msg.content}")
        return "\n".join(lines)

    def clear_session(self, session_id: str) -> None:
        """
        Clear session messages.

        Args:
            session_id: Session ID
        """
        if session_id in self._sessions:
            self._sessions[session_id].clear()
            logger.debug(f"Session {session_id} cleared")

    def delete_session(self, session_id: str) -> None:
        """
        Delete session.

        Args:
            session_id: Session ID
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.debug(f"Session {session_id} deleted")

    def get_session(self, session_id: str) -> Optional[Session]:
        """
        Get session object.

        Args:
            session_id: Session ID

        Returns:
            Session or None
        """
        return self._sessions.get(session_id)

    def list_sessions(self) -> List[str]:
        """List all session IDs."""
        return list(self._sessions.keys())

    def _cleanup_old_sessions(self) -> None:
        """Remove oldest sessions to maintain limit."""
        # Sort by last activity
        sorted_sessions = sorted(self._sessions.items(), key=lambda x: x[1].last_activity)

        # Remove oldest sessions
        num_to_remove = len(self._sessions) - self.max_sessions
        for session_id, _ in sorted_sessions[:num_to_remove]:
            del self._sessions[session_id]
            logger.debug(f"Removed old session {session_id}")

    def get_stats(self) -> Dict:
        """Get memory statistics."""
        return {
            "agent_id": self.agent_id,
            "total_sessions": len(self._sessions),
            "total_messages": sum(len(s.messages) for s in self._sessions.values()),
        }

    # ==================== ContextEngine Integration Methods ====================

    def add_conversation_message(self, session_id: str, role: str, content: str, metadata: Optional[Dict] = None) -> None:
        """
        Add conversation message (sync version with ContextEngine fallback).

        This is a synchronous wrapper that falls back to in-memory storage.
        For ContextEngine integration, use aadd_conversation_message() instead.

        Args:
            session_id: Session ID
            role: Message role (user, assistant, system)
            content: Message content
            metadata: Optional message metadata

        Note:
            If ContextEngine is configured, this method will log a warning
            and fall back to in-memory storage. Use the async version
            aadd_conversation_message() for ContextEngine integration.
        """
        if self.context_engine:
            logger.warning("add_conversation_message called with ContextEngine configured. " "Use aadd_conversation_message() for persistent storage. " "Falling back to in-memory storage.")

        # Fall back to existing add_message method
        self.add_message(session_id, role, content)

    async def aadd_conversation_message(self, session_id: str, role: str, content: str, metadata: Optional[Dict] = None) -> bool:
        """
        Add conversation message (async version with ContextEngine integration).

        Args:
            session_id: Session ID
            role: Message role (user, assistant, system)
            content: Message content
            metadata: Optional message metadata

        Returns:
            True if message was added successfully, False otherwise
        """
        if self.context_engine:
            try:
                # Use ContextEngine for persistent storage
                success = await self.context_engine.add_conversation_message(session_id=session_id, role=role, content=content, metadata=metadata or {})
                logger.debug(f"Added message to session {session_id} via ContextEngine (role={role})")
                return success
            except Exception as e:
                logger.error(f"Failed to add message to ContextEngine for session {session_id}: {e}")
                logger.warning("Falling back to in-memory storage")
                # Fall back to in-memory
                self.add_message(session_id, role, content)
                return False
        else:
            # Use in-memory storage
            self.add_message(session_id, role, content)
            return True

    def get_conversation_history(self, session_id: str, limit: Optional[int] = None) -> List[LLMMessage]:
        """
        Get conversation history (sync version with ContextEngine fallback).

        This is a synchronous wrapper that falls back to in-memory storage.
        For ContextEngine integration, use aget_conversation_history() instead.

        Args:
            session_id: Session ID
            limit: Optional limit on number of messages

        Returns:
            List of LLM messages

        Note:
            If ContextEngine is configured, this method will log a warning
            and fall back to in-memory storage. Use the async version
            aget_conversation_history() for ContextEngine integration.
        """
        if self.context_engine:
            logger.warning("get_conversation_history called with ContextEngine configured. " "Use aget_conversation_history() for persistent storage. " "Falling back to in-memory storage.")

        # Fall back to existing get_history method
        return self.get_history(session_id, limit)

    async def aget_conversation_history(self, session_id: str, limit: Optional[int] = None) -> List[LLMMessage]:
        """
        Get conversation history (async version with ContextEngine integration).

        Args:
            session_id: Session ID
            limit: Optional limit on number of messages

        Returns:
            List of LLM messages
        """
        if self.context_engine:
            try:
                # Use ContextEngine for persistent storage
                messages = await self.context_engine.get_conversation_history(session_id=session_id, limit=limit or 50)

                # Convert ConversationMessage to LLMMessage
                llm_messages = []
                for msg in messages:
                    # messages is List[Dict[str, Any]] from ContextEngine
                    if isinstance(msg, dict):
                        llm_messages.append(LLMMessage(role=msg.get("role", "user"), content=msg.get("content", "")))
                    else:
                        # Fallback for ConversationMessage objects
                        llm_messages.append(LLMMessage(role=msg.role, content=msg.content))

                logger.debug(f"Retrieved {len(llm_messages)} messages from session {session_id} via ContextEngine")
                return llm_messages
            except Exception as e:
                logger.error(f"Failed to get conversation history from ContextEngine for session {session_id}: {e}")
                logger.warning("Falling back to in-memory storage")
                # Fall back to in-memory
                return self.get_history(session_id, limit)
        else:
            # Use in-memory storage
            return self.get_history(session_id, limit)

    def format_conversation_history(self, session_id: str, limit: Optional[int] = None) -> str:
        """
        Format conversation history as string for LLM prompt formatting.

        This is a synchronous wrapper that falls back to in-memory storage.
        For ContextEngine integration, use aformat_conversation_history() instead.

        Args:
            session_id: Session ID
            limit: Optional limit on number of messages

        Returns:
            Formatted history string

        Note:
            If ContextEngine is configured, this method will log a warning
            and fall back to in-memory storage. Use the async version
            aformat_conversation_history() for ContextEngine integration.
        """
        if self.context_engine:
            logger.warning("format_conversation_history called with ContextEngine configured. " "Use aformat_conversation_history() for persistent storage. " "Falling back to in-memory storage.")

        # Fall back to existing format_history method
        return self.format_history(session_id, limit)

    async def aformat_conversation_history(self, session_id: str, limit: Optional[int] = None) -> str:
        """
        Format conversation history as string (async version with ContextEngine integration).

        Args:
            session_id: Session ID
            limit: Optional limit on number of messages

        Returns:
            Formatted history string
        """
        # Get conversation history (uses ContextEngine if available)
        history = await self.aget_conversation_history(session_id, limit)

        # Format messages
        lines = []
        for msg in history:
            lines.append(f"{msg.role.upper()}: {msg.content}")

        return "\n".join(lines)

    async def clear_conversation_history(self, session_id: str) -> bool:
        """
        Clear conversation history with ContextEngine cleanup.

        This method clears both in-memory and ContextEngine storage.

        Args:
            session_id: Session ID

        Returns:
            True if cleared successfully, False otherwise
        """
        success = True

        # Clear in-memory storage
        self.clear_session(session_id)

        # Clear ContextEngine storage if available
        if self.context_engine:
            try:
                # ContextEngine doesn't have a direct clear_conversation method,
                # so we'll need to end the session which will clean up associated data
                await self.context_engine.end_session(session_id, status="cleared")
                logger.debug(f"Cleared conversation history for session {session_id} in ContextEngine")
            except Exception as e:
                logger.error(f"Failed to clear conversation history in ContextEngine for session {session_id}: {e}")
                success = False

        return success

    # ==================== Session Management Methods ====================

    def create_session_with_context(
        self,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> str:
        """
        Create a new session (sync version with ContextEngine fallback).

        This is a synchronous wrapper that falls back to in-memory storage.
        For ContextEngine integration, use acreate_session_with_context() instead.

        Args:
            session_id: Optional custom session ID
            user_id: Optional user ID for ContextEngine
            metadata: Optional session metadata

        Returns:
            Session ID

        Note:
            If ContextEngine is configured, this method will log a warning
            and fall back to in-memory storage. Use the async version
            acreate_session_with_context() for ContextEngine integration.
        """
        if self.context_engine:
            logger.warning("create_session_with_context called with ContextEngine configured. " "Use acreate_session_with_context() for persistent storage. " "Falling back to in-memory storage.")

        # Fall back to existing create_session method
        return self.create_session(session_id)

    async def acreate_session_with_context(
        self,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> str:
        """
        Create a new session (async version with ContextEngine integration).

        Args:
            session_id: Optional custom session ID
            user_id: Optional user ID for ContextEngine (defaults to agent_id)
            metadata: Optional session metadata

        Returns:
            Session ID
        """
        if session_id is None:
            session_id = f"session_{datetime.utcnow().timestamp()}"

        if self.context_engine:
            try:
                # Use ContextEngine for persistent storage
                user_id = user_id or self.agent_id
                await self.context_engine.create_session(session_id=session_id, user_id=user_id, metadata=metadata or {})
                logger.debug(f"Created session {session_id} via ContextEngine")

                # Also create in-memory session for compatibility
                if session_id not in self._sessions:
                    self._sessions[session_id] = Session(session_id=session_id, agent_id=self.agent_id, metadata=metadata or {})
            except Exception as e:
                logger.error(f"Failed to create session in ContextEngine: {e}")
                logger.warning("Falling back to in-memory storage")
                # Fall back to in-memory
                return self.create_session(session_id)
        else:
            # Use in-memory storage
            return self.create_session(session_id)

        return session_id

    def get_session_with_context(self, session_id: str) -> Optional[Session]:
        """
        Get session (sync version with ContextEngine fallback).

        This is a synchronous wrapper that falls back to in-memory storage.
        For ContextEngine integration, use aget_session_with_context() instead.

        Args:
            session_id: Session ID

        Returns:
            Session object or None

        Note:
            If ContextEngine is configured, this method will log a warning
            and fall back to in-memory storage. Use the async version
            aget_session_with_context() for ContextEngine integration.
        """
        if self.context_engine:
            logger.warning("get_session_with_context called with ContextEngine configured. " "Use aget_session_with_context() for persistent storage. " "Falling back to in-memory storage.")

        # Fall back to existing get_session method
        return self.get_session(session_id)

    async def aget_session_with_context(self, session_id: str) -> Optional[Session]:
        """
        Get session (async version with ContextEngine integration).

        Args:
            session_id: Session ID

        Returns:
            Session object or None
        """
        if self.context_engine:
            try:
                # Get from ContextEngine
                session_metrics = await self.context_engine.get_session(session_id)

                if session_metrics:
                    # session_metrics is Dict[str, Any] from ContextEngine
                    # Check if we have it in memory
                    if session_id in self._sessions:
                        # Update in-memory session with ContextEngine metrics
                        session = self._sessions[session_id]
                        if isinstance(session_metrics, dict):
                            session.request_count = session_metrics.get("request_count", 0)
                            session.error_count = session_metrics.get("error_count", 0)
                            session.total_processing_time = session_metrics.get("total_processing_time", 0.0)
                            session.status = session_metrics.get("status", "active")
                        else:
                            session.request_count = session_metrics.request_count
                            session.error_count = session_metrics.error_count
                            session.total_processing_time = session_metrics.total_processing_time
                            session.status = session_metrics.status
                        return session
                    else:
                        # Create in-memory session from ContextEngine data
                        if isinstance(session_metrics, dict):
                            # Convert datetime strings to datetime objects if needed
                            created_at_val = session_metrics.get("created_at")
                            if isinstance(created_at_val, str):
                                try:
                                    created_at_val = datetime.fromisoformat(created_at_val.replace("Z", "+00:00"))
                                except (ValueError, AttributeError):
                                    created_at_val = datetime.utcnow()
                            elif created_at_val is None:
                                created_at_val = datetime.utcnow()
                            
                            last_activity_val = session_metrics.get("last_activity")
                            if isinstance(last_activity_val, str):
                                try:
                                    last_activity_val = datetime.fromisoformat(last_activity_val.replace("Z", "+00:00"))
                                except (ValueError, AttributeError):
                                    last_activity_val = datetime.utcnow()
                            elif last_activity_val is None:
                                last_activity_val = datetime.utcnow()
                            
                            session = Session(
                                session_id=session_id,
                                agent_id=self.agent_id,
                                created_at=created_at_val if isinstance(created_at_val, datetime) else datetime.utcnow(),
                                last_activity=last_activity_val if isinstance(last_activity_val, datetime) else datetime.utcnow(),
                                status=session_metrics.get("status", "active"),
                                request_count=session_metrics.get("request_count", 0),
                                error_count=session_metrics.get("error_count", 0),
                                total_processing_time=session_metrics.get("total_processing_time", 0.0),
                            )
                        else:
                            session = Session(
                                session_id=session_id,
                                agent_id=self.agent_id,
                                created_at=session_metrics.created_at,
                                last_activity=session_metrics.last_activity,
                                status=session_metrics.status,
                                request_count=session_metrics.request_count,
                                error_count=session_metrics.error_count,
                                total_processing_time=session_metrics.total_processing_time,
                            )
                        self._sessions[session_id] = session
                        return session

                logger.debug(f"Session {session_id} not found in ContextEngine")
                return None
            except Exception as e:
                logger.error(f"Failed to get session from ContextEngine: {e}")
                logger.warning("Falling back to in-memory storage")
                # Fall back to in-memory
                return self.get_session(session_id)
        else:
            # Use in-memory storage
            return self.get_session(session_id)

    async def update_session_with_context(
        self,
        session_id: str,
        increment_requests: bool = False,
        add_processing_time: float = 0.0,
        mark_error: bool = False,
        updates: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Update session with activity and metrics.

        Args:
            session_id: Session ID
            increment_requests: Whether to increment request count
            add_processing_time: Processing time to add (in seconds)
            mark_error: Whether to mark an error
            updates: Optional dictionary of additional updates

        Returns:
            True if updated successfully, False otherwise
        """
        # Update in-memory session
        session = self.get_session(session_id)
        if session:
            if increment_requests or add_processing_time > 0 or mark_error:
                session.track_request(processing_time=add_processing_time, is_error=mark_error)

            # Apply custom updates
            if updates:
                for key, value in updates.items():
                    if hasattr(session, key):
                        setattr(session, key, value)

        # Update ContextEngine if available
        if self.context_engine:
            try:
                await self.context_engine.update_session(
                    session_id=session_id,
                    increment_requests=increment_requests,
                    add_processing_time=add_processing_time,
                    mark_error=mark_error,
                    updates=updates or {},
                )
                logger.debug(f"Updated session {session_id} in ContextEngine")
                return True
            except Exception as e:
                logger.error(f"Failed to update session in ContextEngine: {e}")
                return False

        return session is not None

    async def end_session_with_context(self, session_id: str, status: str = "completed") -> bool:
        """
        End a session and update metrics.

        Args:
            session_id: Session ID
            status: Final session status (completed, failed, expired)

        Returns:
            True if ended successfully, False otherwise
        """
        # End in-memory session
        session = self.get_session(session_id)
        if session:
            session.end(status=status)

        # End ContextEngine session if available
        if self.context_engine:
            try:
                await self.context_engine.end_session(session_id, status=status)
                logger.debug(f"Ended session {session_id} in ContextEngine with status: {status}")
                return True
            except Exception as e:
                logger.error(f"Failed to end session in ContextEngine: {e}")
                return False

        return session is not None

    def track_session_request(self, session_id: str, processing_time: float = 0.0, is_error: bool = False) -> None:
        """
        Track a request in a session.

        Args:
            session_id: Session ID
            processing_time: Processing time in seconds
            is_error: Whether the request resulted in an error
        """
        session = self.get_session(session_id)
        if session:
            session.track_request(processing_time=processing_time, is_error=is_error)
        else:
            logger.warning(f"Session {session_id} not found for request tracking")

    def get_session_metrics(self, session_id: str) -> Optional[Dict]:
        """
        Get aggregated metrics for a session.

        Args:
            session_id: Session ID

        Returns:
            Dictionary with session metrics or None if session not found
        """
        session = self.get_session(session_id)
        if session:
            return session.get_metrics()
        return None

    async def cleanup_inactive_sessions(self, max_idle_seconds: int = 1800) -> int:
        """
        Clean up inactive sessions.

        Args:
            max_idle_seconds: Maximum idle time in seconds (default: 30 minutes)

        Returns:
            Number of sessions cleaned up
        """
        cleaned_count = 0

        # Find expired sessions
        expired_sessions = []
        for session_id, session in list(self._sessions.items()):
            if session.is_expired(max_idle_seconds):
                expired_sessions.append(session_id)

        # End and remove expired sessions
        for session_id in expired_sessions:
            # End session with expired status
            await self.end_session_with_context(session_id, status="expired")

            # Remove from in-memory storage
            if session_id in self._sessions:
                del self._sessions[session_id]
                cleaned_count += 1
                logger.debug(f"Cleaned up expired session {session_id}")

        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} inactive sessions")

        return cleaned_count
