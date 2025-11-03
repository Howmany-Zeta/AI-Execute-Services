"""
ContextEngine Adapter

Adapter for integrating agent persistence with AIECS ContextEngine.
"""

import logging
import json
import uuid
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from aiecs.domain.context.context_engine import ContextEngine

from aiecs.domain.agent.persistence import AgentPersistence
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
        version: Optional[str] = None
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
            "version": version
        }

        # Store as checkpoint (thread_id = agent_id)
        await self.context_engine.store_checkpoint(
            thread_id=agent_id,
            checkpoint_id=version,
            checkpoint_data=checkpoint_data,
            metadata={"type": "agent_state", "agent_id": agent_id}
        )

        logger.debug(f"Saved agent {agent_id} state version {version} to ContextEngine")
        return version

    async def load_agent_state(
        self,
        agent_id: str,
        version: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Load agent state from ContextEngine.

        Args:
            agent_id: Agent identifier
            version: Optional version identifier (loads latest if None)

        Returns:
            Agent state dictionary or None
        """
        checkpoint = await self.context_engine.get_checkpoint(
            thread_id=agent_id,
            checkpoint_id=version
        )

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
            # list_checkpoints returns dicts with "data" key containing checkpoint_data
            if isinstance(checkpoint, dict):
                data = checkpoint.get("data", {})
                if isinstance(data, dict) and "version" in data:
                    versions.append({
                        "version": data["version"],
                        "timestamp": data.get("timestamp"),
                        "metadata": checkpoint.get("metadata", {})
                    })

        # Sort by timestamp descending
        versions.sort(key=lambda v: v.get("timestamp", ""), reverse=True)
        return versions

    async def save_conversation_history(
        self,
        session_id: str,
        messages: List[Dict[str, Any]]
    ) -> None:
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
                metadata={"type": "agent_conversation"}
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
                metadata=metadata
            )

        logger.debug(f"Saved {len(messages)} messages to session {session_id}")

    async def load_conversation_history(
        self,
        session_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Load conversation history from ContextEngine.

        Args:
            session_id: Session identifier
            limit: Maximum number of messages to retrieve

        Returns:
            List of message dictionaries
        """
        messages = await self.context_engine.get_conversation_history(
            session_id=session_id,
            limit=limit
        )

        # Convert ConversationMessage objects to dictionaries
        result = []
        for msg in messages:
            result.append({
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat() if hasattr(msg.timestamp, 'isoformat') else str(msg.timestamp),
                "metadata": msg.metadata
            })

        logger.debug(f"Loaded {len(result)} messages from session {session_id}")
        return result

    async def delete_agent_state(
        self,
        agent_id: str,
        version: Optional[str] = None
    ) -> None:
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
                metadata={"type": "deletion_marker"}
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

