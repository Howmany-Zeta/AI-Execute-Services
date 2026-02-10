"""
Storage interfaces for the middleware architecture.

This module defines the core storage abstractions following the same pattern
as other core interfaces, enabling dependency inversion and clean architecture.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List


class ISessionStorage(ABC):
    """Session storage interface - Domain layer abstraction"""

    @abstractmethod
    async def create_session(self, session_id: str, user_id: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a new session."""

    @abstractmethod
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID."""

    @abstractmethod
    async def update_session(
        self,
        session_id: str,
        updates: Optional[Dict[str, Any]] = None,
        increment_requests: bool = False,
        add_processing_time: float = 0.0,
        mark_error: bool = False,
    ) -> bool:
        """Update session with activity and metrics."""

    @abstractmethod
    async def end_session(self, session_id: str, status: str = "completed") -> bool:
        """End a session and update metrics."""


class IConversationStorage(ABC):
    """Conversation storage interface - Domain layer abstraction"""

    @abstractmethod
    async def add_conversation_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Add message to conversation history."""

    @abstractmethod
    async def get_conversation_history(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get conversation history for a session."""


class ICheckpointStorage(ABC):
    """Checkpoint storage interface - Domain layer abstraction"""

    @abstractmethod
    async def store_checkpoint(
        self,
        thread_id: str,
        checkpoint_id: str,
        checkpoint_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Store checkpoint data."""

    @abstractmethod
    async def get_checkpoint(self, thread_id: str, checkpoint_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get checkpoint data. If checkpoint_id is None, get the latest."""

    @abstractmethod
    async def list_checkpoints(self, thread_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """List checkpoints for a thread, ordered by creation time."""


class ITaskContextStorage(ABC):
    """Task context storage interface - Domain layer abstraction"""

    @abstractmethod
    async def get_task_context(self, session_id: str) -> Optional[Any]:
        """Get TaskContext for a session."""

    @abstractmethod
    async def store_task_context(self, session_id: str, context: Any) -> bool:
        """Store TaskContext for a session."""


class IStorageBackend(
    ISessionStorage,
    IConversationStorage,
    ICheckpointStorage,
    ITaskContextStorage,
):
    """
    Unified storage backend interface - Domain layer abstraction

    This interface combines all storage capabilities and follows the same
    pattern as other core interfaces in the middleware architecture.
    """

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the storage backend."""

    @abstractmethod
    async def close(self):
        """Close the storage backend."""

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""

    @abstractmethod
    async def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive metrics."""

    @abstractmethod
    async def cleanup_expired_sessions(self, max_idle_hours: int = 24) -> int:
        """Clean up expired sessions and associated data."""


class IPermanentStorageBackend(ABC):
    """
    Permanent storage backend interface for disk-based cold archive.

    Used for dual-write alongside Redis (hot cache). Append-only semantics,
    optimized for analytics and long-term retention. Typical implementation:
    ClickHouse, PostgreSQL, etc.

    All methods are fire-and-forget: failures should not block the primary
    Redis write path. Implementations should handle errors internally.
    """

    @abstractmethod
    async def append_session_event(
        self,
        session_id: str,
        user_id: str,
        event_type: str,
        payload: Dict[str, Any],
        created_at: Optional[str] = None,
    ) -> bool:
        """Append session create/update/end event for audit/analytics."""

    @abstractmethod
    async def append_conversation_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        created_at: Optional[str] = None,
    ) -> bool:
        """Append conversation message (append-only)."""

    @abstractmethod
    async def append_checkpoint(
        self,
        thread_id: str,
        checkpoint_id: str,
        checkpoint_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        created_at: Optional[str] = None,
    ) -> bool:
        """Append checkpoint data."""

    @abstractmethod
    async def append_checkpoint_writes(
        self,
        thread_id: str,
        checkpoint_id: str,
        task_id: str,
        writes_data: List[tuple],
        created_at: Optional[str] = None,
    ) -> bool:
        """Append checkpoint writes."""

    @abstractmethod
    async def append_conversation_session(
        self,
        session_key: str,
        session_data: Dict[str, Any],
        created_at: Optional[str] = None,
    ) -> bool:
        """Append conversation session metadata."""

    @abstractmethod
    async def append_task_context_snapshot(
        self,
        session_id: str,
        context_data: Dict[str, Any],
        created_at: Optional[str] = None,
    ) -> bool:
        """Append task context snapshot (versioned)."""

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the permanent storage backend."""

    @abstractmethod
    async def close(self) -> None:
        """Close the permanent storage backend."""


class ICheckpointerBackend(ABC):
    """
    Checkpointer backend interface for LangGraph integration.

    This interface defines the minimal contract needed by BaseServiceCheckpointer
    to work with any storage backend, following dependency inversion principle.
    """

    @abstractmethod
    async def put_checkpoint(
        self,
        thread_id: str,
        checkpoint_id: str,
        checkpoint_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Store a checkpoint for LangGraph workflows."""

    @abstractmethod
    async def get_checkpoint(self, thread_id: str, checkpoint_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Retrieve a checkpoint for LangGraph workflows."""

    @abstractmethod
    async def list_checkpoints(self, thread_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """List checkpoints for LangGraph workflows."""

    @abstractmethod
    async def put_writes(
        self,
        thread_id: str,
        checkpoint_id: str,
        task_id: str,
        writes_data: List[tuple],
    ) -> bool:
        """Store intermediate writes for a checkpoint."""

    @abstractmethod
    async def get_writes(self, thread_id: str, checkpoint_id: str) -> List[tuple]:
        """Get intermediate writes for a checkpoint."""
