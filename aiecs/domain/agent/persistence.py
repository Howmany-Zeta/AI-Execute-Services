"""
Agent Persistence

Interfaces and implementations for saving/loading agent state.
"""

import logging
import json
from typing import Dict, Any, Optional, Protocol
from abc import ABC, abstractmethod
from datetime import datetime

from .base_agent import BaseAIAgent
from .exceptions import SerializationError

logger = logging.getLogger(__name__)


class AgentPersistence(Protocol):
    """Protocol for agent persistence implementations."""

    async def save(self, agent: BaseAIAgent) -> None:
        """
        Save agent state.

        Args:
            agent: Agent to save
        """
        ...

    async def load(self, agent_id: str) -> Dict[str, Any]:
        """
        Load agent state.

        Args:
            agent_id: Agent identifier

        Returns:
            Agent state dictionary
        """
        ...

    async def exists(self, agent_id: str) -> bool:
        """
        Check if agent state exists.

        Args:
            agent_id: Agent identifier

        Returns:
            True if exists
        """
        ...

    async def delete(self, agent_id: str) -> None:
        """
        Delete agent state.

        Args:
            agent_id: Agent identifier
        """
        ...


class InMemoryPersistence:
    """In-memory agent persistence (for testing/development)."""

    def __init__(self):
        """Initialize in-memory storage."""
        self._storage: Dict[str, Dict[str, Any]] = {}
        logger.info("InMemoryPersistence initialized")

    async def save(self, agent: BaseAIAgent) -> None:
        """Save agent state to memory."""
        try:
            state = agent.to_dict()
            # Convert any remaining datetime objects to ISO strings
            state = self._serialize_datetimes(state)
            self._storage[agent.agent_id] = {
                "state": state,
                "saved_at": datetime.utcnow().isoformat(),
            }
            logger.debug(f"Agent {agent.agent_id} saved to memory")
        except Exception as e:
            logger.error(f"Failed to save agent {agent.agent_id}: {e}")
            raise SerializationError(f"Failed to save agent: {str(e)}")

    def _serialize_datetimes(self, obj: Any) -> Any:
        """Recursively serialize datetime objects to ISO strings."""
        import json
        if isinstance(obj, dict):
            return {k: self._serialize_datetimes(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_datetimes(item) for item in obj]
        elif isinstance(obj, datetime):
            return obj.isoformat()
        else:
            return obj

    async def load(self, agent_id: str) -> Dict[str, Any]:
        """Load agent state from memory."""
        if agent_id not in self._storage:
            raise KeyError(f"Agent {agent_id} not found in storage")
        
        data = self._storage[agent_id]
        logger.debug(f"Agent {agent_id} loaded from memory")
        return data["state"]

    async def exists(self, agent_id: str) -> bool:
        """Check if agent exists in memory."""
        return agent_id in self._storage

    async def delete(self, agent_id: str) -> None:
        """Delete agent from memory."""
        if agent_id in self._storage:
            del self._storage[agent_id]
            logger.debug(f"Agent {agent_id} deleted from memory")

    def clear(self) -> None:
        """Clear all stored agents."""
        self._storage.clear()
        logger.info("InMemoryPersistence cleared")


class FilePersistence:
    """File-based agent persistence."""

    def __init__(self, base_path: str = "./agent_states"):
        """
        Initialize file-based storage.

        Args:
            base_path: Base directory for agent states
        """
        import os
        
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)
        logger.info(f"FilePersistence initialized with base_path: {base_path}")

    def _get_file_path(self, agent_id: str) -> str:
        """Get file path for agent."""
        import os
        # Sanitize agent_id for filesystem
        safe_id = agent_id.replace("/", "_").replace("\\", "_")
        return os.path.join(self.base_path, f"{safe_id}.json")

    async def save(self, agent: BaseAIAgent) -> None:
        """Save agent state to file."""
        try:
            state = agent.to_dict()
            # Convert any remaining datetime objects to ISO strings for JSON serialization
            state = self._serialize_datetimes(state)
            file_path = self._get_file_path(agent.agent_id)
            
            data = {
                "state": state,
                "saved_at": datetime.utcnow().isoformat(),
            }
            
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)  # default=str handles any remaining non-serializable objects
            
            logger.debug(f"Agent {agent.agent_id} saved to {file_path}")
        except Exception as e:
            logger.error(f"Failed to save agent {agent.agent_id}: {e}")
            raise SerializationError(f"Failed to save agent: {str(e)}")

    def _serialize_datetimes(self, obj: Any) -> Any:
        """Recursively serialize datetime objects to ISO strings."""
        if isinstance(obj, dict):
            return {k: self._serialize_datetimes(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_datetimes(item) for item in obj]
        elif isinstance(obj, datetime):
            return obj.isoformat()
        else:
            return obj

    async def load(self, agent_id: str) -> Dict[str, Any]:
        """Load agent state from file."""
        file_path = self._get_file_path(agent_id)
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            logger.debug(f"Agent {agent_id} loaded from {file_path}")
            return data["state"]
        except FileNotFoundError:
            raise KeyError(f"Agent {agent_id} not found in storage")
        except Exception as e:
            logger.error(f"Failed to load agent {agent_id}: {e}")
            raise SerializationError(f"Failed to load agent: {str(e)}")

    async def exists(self, agent_id: str) -> bool:
        """Check if agent file exists."""
        import os
        file_path = self._get_file_path(agent_id)
        return os.path.exists(file_path)

    async def delete(self, agent_id: str) -> None:
        """Delete agent file."""
        import os
        file_path = self._get_file_path(agent_id)
        
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.debug(f"Agent {agent_id} deleted from {file_path}")
        except Exception as e:
            logger.error(f"Failed to delete agent {agent_id}: {e}")
            raise


class AgentStateSerializer:
    """
    Helper class for serializing/deserializing agent state.
    
    Handles complex types that need special serialization.
    """

    @staticmethod
    def serialize(agent: BaseAIAgent) -> Dict[str, Any]:
        """
        Serialize agent to dictionary.

        Args:
            agent: Agent to serialize

        Returns:
            Serialized state dictionary
        """
        return agent.to_dict()

    @staticmethod
    def deserialize(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deserialize agent state.

        Args:
            data: Serialized state

        Returns:
            Deserialized state dictionary
        
        Note: This returns a state dictionary, not an agent instance.
        Agent reconstruction requires the appropriate agent class.
        """
        # In the future, this could handle type conversion, validation, etc.
        return data


# Global persistence instance
_global_persistence: Optional[AgentPersistence] = None


def get_global_persistence() -> AgentPersistence:
    """
    Get or create global persistence instance.

    Returns:
        Global persistence instance (defaults to InMemoryPersistence)
    """
    global _global_persistence
    if _global_persistence is None:
        _global_persistence = InMemoryPersistence()
    return _global_persistence


def set_global_persistence(persistence: AgentPersistence) -> None:
    """
    Set global persistence instance.

    Args:
        persistence: Persistence implementation to use
    """
    global _global_persistence
    _global_persistence = persistence
    logger.info(f"Global persistence set to {type(persistence).__name__}")


def reset_global_persistence() -> None:
    """Reset global persistence (primarily for testing)."""
    global _global_persistence
    _global_persistence = None

