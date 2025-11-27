"""
ContextEngine Adapter

Adapter for integrating agent persistence with AIECS ContextEngine.
"""

import logging
import uuid
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from aiecs.domain.context.context_engine import ContextEngine

from aiecs.domain.agent.base_agent import BaseAIAgent

logger = logging.getLogger(__name__)


class ContextEngineAdapter:
    """
    Adapter for persisting agent state to ContextEngine.

    Uses ContextEngine's checkpoint system for versioned state storage
    and TaskContext for session-based state management.
    """

    def __init__(self, context_engine: "ContextEngine", user_id: str = "system"):
        """
        Initialize adapter.

        Args:
            context_engine: ContextEngine instance
            user_id: User identifier for session management
        """
        if context_engine is None:
            raise ValueError("ContextEngine instance is required")

        self.context_engine = context_engine
        self.user_id = user_id
        self._agent_state_prefix = "agent_state"
        self._agent_conversation_prefix = "agent_conversation"
        logger.info("ContextEngineAdapter initialized")

    async def save_agent_state(
        self,
        agent_id: str,
        state: Dict[str, Any],
        version: Optional[str] = None,
    ) -> str:
        """
        Save agent state to ContextEngine using checkpoint system.

        Args:
            agent_id: Agent identifier
            state: Agent state dictionary
            version: Optional version identifier (auto-generated if None)

        Returns:
            Version identifier
        """
        if version is None:
            version = str(uuid.uuid4())

        checkpoint_data = {
            "agent_id": agent_id,
            "state": state,
            "timestamp": datetime.utcnow().isoformat(),
            "version": version,
        }

        # Store as checkpoint (thread_id = agent_id)
        await self.context_engine.store_checkpoint(
            thread_id=agent_id,
            checkpoint_id=version,
            checkpoint_data=checkpoint_data,
            metadata={"type": "agent_state", "agent_id": agent_id},
        )

        logger.debug(f"Saved agent {agent_id} state version {version} to ContextEngine")
        return version

    async def load_agent_state(self, agent_id: str, version: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Load agent state from ContextEngine.

        Args:
            agent_id: Agent identifier
            version: Optional version identifier (loads latest if None)

        Returns:
            Agent state dictionary or None
        """
        if version is None:
            return None
        checkpoint = await self.context_engine.get_checkpoint(thread_id=agent_id, checkpoint_id=version)

        if checkpoint and "data" in checkpoint:
            checkpoint_data = checkpoint["data"]
            if isinstance(checkpoint_data, dict) and "state" in checkpoint_data:
                logger.debug(f"Loaded agent {agent_id} state version {version or 'latest'}")
                return checkpoint_data["state"]

        logger.debug(f"No state found for agent {agent_id} version {version or 'latest'}")
        return None

    async def list_agent_versions(self, agent_id: str) -> List[Dict[str, Any]]:
        """
        List all versions of an agent's state.

        Args:
            agent_id: Agent identifier

        Returns:
            List of version metadata dictionaries
        """
        checkpoints = await self.context_engine.list_checkpoints(thread_id=agent_id)
        if not checkpoints:
            return []

        versions = []
        for checkpoint in checkpoints:
            # list_checkpoints returns dicts with "data" key containing
            # checkpoint_data
            if isinstance(checkpoint, dict):
                data = checkpoint.get("data", {})
                if isinstance(data, dict) and "version" in data:
                    versions.append(
                        {
                            "version": data["version"],
                            "timestamp": data.get("timestamp"),
                            "metadata": checkpoint.get("metadata", {}),
                        }
                    )

        # Sort by timestamp descending
        versions.sort(key=lambda v: v.get("timestamp", ""), reverse=True)
        return versions

    async def save_conversation_history(self, session_id: str, messages: List[Dict[str, Any]]) -> None:
        """
        Save conversation history to ContextEngine.

        Args:
            session_id: Session identifier
            messages: List of message dictionaries with 'role' and 'content'
        """
        # Ensure session exists
        session = await self.context_engine.get_session(session_id)
        if not session:
            await self.context_engine.create_session(
                session_id=session_id,
                user_id=self.user_id,
                metadata={"type": "agent_conversation"},
            )

        # Store messages using ContextEngine's conversation API
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            metadata = msg.get("metadata", {})

            await self.context_engine.add_conversation_message(
                session_id=session_id,
                role=role,
                content=content,
                metadata=metadata,
            )

        logger.debug(f"Saved {len(messages)} messages to session {session_id}")

    async def load_conversation_history(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Load conversation history from ContextEngine.

        Args:
            session_id: Session identifier
            limit: Maximum number of messages to retrieve

        Returns:
            List of message dictionaries
        """
        messages = await self.context_engine.get_conversation_history(session_id=session_id, limit=limit)

        # Convert ConversationMessage objects to dictionaries
        # messages is List[Dict[str, Any]] from get_conversation_history
        result = []
        for msg in messages:
            if isinstance(msg, dict):
                result.append(msg)
            else:
                result.append(
                    {
                        "role": getattr(msg, "role", ""),
                        "content": getattr(msg, "content", ""),
                        "timestamp": (getattr(msg, "timestamp", "").isoformat() if hasattr(getattr(msg, "timestamp", None), "isoformat") else str(getattr(msg, "timestamp", ""))),
                        "metadata": getattr(msg, "metadata", {}),
                    }
                )

        logger.debug(f"Loaded {len(result)} messages from session {session_id}")
        return result

    async def delete_agent_state(self, agent_id: str, version: Optional[str] = None) -> None:
        """
        Delete agent state from ContextEngine.

        Args:
            agent_id: Agent identifier
            version: Optional version identifier (deletes all if None)
        """
        # Note: ContextEngine doesn't have explicit delete for checkpoints
        # We'll store a tombstone checkpoint or rely on TTL
        if version:
            # Store empty state as deletion marker
            await self.context_engine.store_checkpoint(
                thread_id=agent_id,
                checkpoint_id=f"{version}_deleted",
                checkpoint_data={"deleted": True, "original_version": version},
                metadata={"type": "deletion_marker"},
            )
        logger.debug(f"Marked agent {agent_id} state version {version or 'all'} for deletion")

    # AgentPersistence Protocol implementation
    async def save(self, agent: BaseAIAgent) -> None:
        """Save agent state (implements AgentPersistence protocol)."""
        state = agent.to_dict()
        await self.save_agent_state(agent.agent_id, state)

    async def load(self, agent_id: str) -> Dict[str, Any]:
        """Load agent state (implements AgentPersistence protocol)."""
        state = await self.load_agent_state(agent_id)
        if state is None:
            raise KeyError(f"Agent {agent_id} not found in storage")
        return state

    async def exists(self, agent_id: str) -> bool:
        """Check if agent state exists (implements AgentPersistence protocol)."""
        state = await self.load_agent_state(agent_id)
        return state is not None

    async def delete(self, agent_id: str) -> None:
        """Delete agent state (implements AgentPersistence protocol)."""
        await self.delete_agent_state(agent_id)

    # ==================== Session Management Methods ====================

    def create_session(
        self,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> str:
        """
        Create a new session (sync version - not recommended with ContextEngine).

        This is a synchronous wrapper that raises NotImplementedError.
        Use acreate_session() instead for ContextEngine integration.

        Args:
            session_id: Optional custom session ID
            user_id: Optional user ID
            metadata: Optional session metadata

        Raises:
            NotImplementedError: Sync version not supported with ContextEngine

        Note:
            ContextEngine operations are async. Use acreate_session() instead.
        """
        raise NotImplementedError("Synchronous create_session not supported with ContextEngine. " "Use acreate_session() instead.")

    async def acreate_session(
        self,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> str:
        """
        Create a new session (async version with ContextEngine integration).

        Args:
            session_id: Optional custom session ID (auto-generated if None)
            user_id: Optional user ID (defaults to adapter's user_id)
            metadata: Optional session metadata

        Returns:
            Session ID

        Example:
            adapter = ContextEngineAdapter(context_engine)
            session_id = await adapter.acreate_session(
                user_id="user-123",
                metadata={"source": "web", "language": "en"}
            )
        """
        if session_id is None:
            session_id = f"session_{uuid.uuid4()}"

        user_id = user_id or self.user_id
        metadata = metadata or {}

        await self.context_engine.create_session(session_id=session_id, user_id=user_id, metadata=metadata)

        logger.debug(f"Created session {session_id} via ContextEngine")
        return session_id

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session (sync version - not recommended with ContextEngine).

        This is a synchronous wrapper that raises NotImplementedError.
        Use aget_session() instead for ContextEngine integration.

        Args:
            session_id: Session ID

        Raises:
            NotImplementedError: Sync version not supported with ContextEngine

        Note:
            ContextEngine operations are async. Use aget_session() instead.
        """
        raise NotImplementedError("Synchronous get_session not supported with ContextEngine. " "Use aget_session() instead.")

    async def aget_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session (async version with ContextEngine integration).

        Args:
            session_id: Session ID

        Returns:
            Session data dictionary or None if not found

        Example:
            session = await adapter.aget_session(session_id)
            if session:
                print(f"Session status: {session.status}")
                print(f"Request count: {session.request_count}")
        """
        session = await self.context_engine.get_session(session_id)

        if session:
            logger.debug(f"Retrieved session {session_id} from ContextEngine")
            # session is already a dict from get_session()
            if isinstance(session, dict):
                return session
            # Convert SessionMetrics to dict if it's a dataclass
            elif hasattr(session, "to_dict"):
                return session.to_dict()  # type: ignore[attr-defined]
            else:
                # Fallback for dataclass
                from dataclasses import asdict, is_dataclass

                if is_dataclass(session):
                    return asdict(session)  # type: ignore[arg-type]
                # If it's already a dict or other type, return as-is
                return session  # type: ignore[return-value]

        logger.debug(f"Session {session_id} not found in ContextEngine")
        return None

    async def end_session(self, session_id: str, status: str = "completed") -> bool:
        """
        End a session.

        Args:
            session_id: Session ID
            status: Final session status (completed, failed, expired)

        Returns:
            True if session was ended successfully, False otherwise

        Example:
            success = await adapter.end_session(session_id, status="completed")
        """
        try:
            await self.context_engine.end_session(session_id, status=status)
            logger.debug(f"Ended session {session_id} with status: {status}")
            return True
        except Exception as e:
            logger.error(f"Failed to end session {session_id}: {e}")
            return False

    # ==================== Conversation Message Methods ====================

    def add_conversation_message(self, session_id: str, role: str, content: str, metadata: Optional[Dict] = None) -> None:
        """
        Add conversation message (sync version - not recommended with ContextEngine).

        This is a synchronous wrapper that raises NotImplementedError.
        Use aadd_conversation_message() instead for ContextEngine integration.

        Args:
            session_id: Session ID
            role: Message role (user, assistant, system)
            content: Message content
            metadata: Optional message metadata

        Raises:
            NotImplementedError: Sync version not supported with ContextEngine

        Note:
            ContextEngine operations are async. Use aadd_conversation_message() instead.
        """
        raise NotImplementedError("Synchronous add_conversation_message not supported with ContextEngine. " "Use aadd_conversation_message() instead.")

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

        Example:
            success = await adapter.aadd_conversation_message(
                session_id="session-123",
                role="user",
                content="Hello, how are you?",
                metadata={"source": "web"}
            )
        """
        try:
            await self.context_engine.add_conversation_message(session_id=session_id, role=role, content=content, metadata=metadata or {})
            logger.debug(f"Added message to session {session_id} (role={role})")
            return True
        except Exception as e:
            logger.error(f"Failed to add message to session {session_id}: {e}")
            return False

    def get_conversation_history(self, session_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get conversation history (sync version - not recommended with ContextEngine).

        This is a synchronous wrapper that raises NotImplementedError.
        Use aget_conversation_history() instead for ContextEngine integration.

        Args:
            session_id: Session ID
            limit: Optional limit on number of messages

        Raises:
            NotImplementedError: Sync version not supported with ContextEngine

        Note:
            ContextEngine operations are async. Use aget_conversation_history() instead.
        """
        raise NotImplementedError("Synchronous get_conversation_history not supported with ContextEngine. " "Use aget_conversation_history() instead.")

    async def aget_conversation_history(self, session_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get conversation history (async version with ContextEngine integration).

        Args:
            session_id: Session ID
            limit: Optional limit on number of messages (default: 50)

        Returns:
            List of message dictionaries

        Example:
            messages = await adapter.aget_conversation_history(
                session_id="session-123",
                limit=10
            )
            for msg in messages:
                print(f"{msg['role']}: {msg['content']}")
        """
        try:
            messages = await self.context_engine.get_conversation_history(session_id=session_id, limit=limit or 50)

            # Convert ConversationMessage objects to dictionaries
            result = []
            for msg in messages:
                # messages is List[Dict[str, Any]] from get_conversation_history
                if isinstance(msg, dict):
                    result.append(msg)
                else:
                    result.append(
                        {
                            "role": getattr(msg, "role", ""),
                            "content": getattr(msg, "content", ""),
                            "timestamp": (getattr(msg, "timestamp", "").isoformat() if hasattr(getattr(msg, "timestamp", None), "isoformat") else str(getattr(msg, "timestamp", ""))),
                            "metadata": getattr(msg, "metadata", {}),
                        }
                    )

            logger.debug(f"Retrieved {len(result)} messages from session {session_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to get conversation history for session {session_id}: {e}")
            return []

    # ==================== Checkpoint Methods ====================

    async def store_checkpoint(
        self,
        thread_id: str,
        checkpoint_id: str,
        checkpoint_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Store a checkpoint in ContextEngine.

        This is a convenience wrapper around ContextEngine.store_checkpoint()
        that provides consistent error handling and logging.

        Args:
            thread_id: Thread identifier (typically agent_id or session_id)
            checkpoint_id: Checkpoint identifier (version or timestamp)
            checkpoint_data: Checkpoint data to store
            metadata: Optional metadata for the checkpoint

        Returns:
            True if checkpoint was stored successfully, False otherwise

        Example:
            success = await adapter.store_checkpoint(
                thread_id="agent-123",
                checkpoint_id="v1.0",
                checkpoint_data={"state": agent_state},
                metadata={"type": "agent_state", "version": "1.0"}
            )
        """
        try:
            await self.context_engine.store_checkpoint(
                thread_id=thread_id,
                checkpoint_id=checkpoint_id,
                checkpoint_data=checkpoint_data,
                metadata=metadata or {},
            )
            logger.debug(f"Stored checkpoint {checkpoint_id} for thread {thread_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to store checkpoint {checkpoint_id} for thread {thread_id}: {e}")
            return False

    async def get_checkpoint(self, thread_id: str, checkpoint_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get a checkpoint from ContextEngine.

        This is a convenience wrapper around ContextEngine.get_checkpoint()
        that provides consistent error handling and logging.

        Args:
            thread_id: Thread identifier (typically agent_id or session_id)
            checkpoint_id: Optional checkpoint identifier (gets latest if None)

        Returns:
            Checkpoint data dictionary or None if not found

        Example:
            # Get latest checkpoint
            checkpoint = await adapter.get_checkpoint(thread_id="agent-123")

            # Get specific checkpoint
            checkpoint = await adapter.get_checkpoint(
                thread_id="agent-123",
                checkpoint_id="v1.0"
            )

            if checkpoint:
                data = checkpoint.get("data", {})
                metadata = checkpoint.get("metadata", {})
        """
        try:
            if checkpoint_id is None:
                return None
            checkpoint = await self.context_engine.get_checkpoint(thread_id=thread_id, checkpoint_id=checkpoint_id)

            if checkpoint:
                logger.debug(f"Retrieved checkpoint {checkpoint_id or 'latest'} for thread {thread_id}")
                return checkpoint

            logger.debug(f"Checkpoint {checkpoint_id or 'latest'} not found for thread {thread_id}")
            return None
        except Exception as e:
            logger.error(f"Failed to get checkpoint {checkpoint_id or 'latest'} for thread {thread_id}: {e}")
            return None
