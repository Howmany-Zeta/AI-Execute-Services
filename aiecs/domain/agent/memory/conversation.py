"""
Conversation Memory

Multi-turn conversation handling with session management.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, field

from aiecs.llm import LLMMessage

logger = logging.getLogger(__name__)


@dataclass
class Session:
    """Conversation session."""
    session_id: str
    agent_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    messages: List[LLMMessage] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

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


class ConversationMemory:
    """
    Manages multi-turn conversations with session isolation.

    Example:
        memory = ConversationMemory(agent_id="agent-1")
        session_id = memory.create_session()
        memory.add_message(session_id, "user", "Hello")
        memory.add_message(session_id, "assistant", "Hi there!")
        history = memory.get_history(session_id)
    """

    def __init__(self, agent_id: str, max_sessions: int = 100):
        """
        Initialize conversation memory.

        Args:
            agent_id: Agent identifier
            max_sessions: Maximum number of sessions to keep
        """
        self.agent_id = agent_id
        self.max_sessions = max_sessions
        self._sessions: Dict[str, Session] = {}
        logger.info(f"ConversationMemory initialized for agent {agent_id}")

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

        self._sessions[session_id] = Session(
            session_id=session_id,
            agent_id=self.agent_id
        )

        # Cleanup old sessions if limit exceeded
        if len(self._sessions) > self.max_sessions:
            self._cleanup_old_sessions()

        logger.debug(f"Session {session_id} created")
        return session_id

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str
    ) -> None:
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

    def get_history(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[LLMMessage]:
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

    def format_history(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> str:
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
        sorted_sessions = sorted(
            self._sessions.items(),
            key=lambda x: x[1].last_activity
        )

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

