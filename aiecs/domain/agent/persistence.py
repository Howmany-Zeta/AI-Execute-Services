"""
Agent Persistence

Interfaces and implementations for saving/loading agent state.
"""

import logging
import json
from typing import Dict, Any, Optional, Protocol
from datetime import datetime
from collections import ChainMap
import asyncio
import queue
import dataclasses

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

    def __init__(self) -> None:
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
            # Convert any remaining datetime objects to ISO strings for JSON
            # serialization
            state = self._serialize_datetimes(state)
            file_path = self._get_file_path(agent.agent_id)

            data = {
                "state": state,
                "saved_at": datetime.utcnow().isoformat(),
            }

            with open(file_path, "w") as f:
                # default=str handles any remaining non-serializable objects
                json.dump(data, f, indent=2, default=str)

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
            with open(file_path, "r") as f:
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

    Handles complex types that need special serialization, including:
    - datetime objects
    - asyncio.Queue and queue.Queue
    - ChainMap
    - dataclasses
    - Other non-JSON-serializable types
    """

    @staticmethod
    def serialize(agent: BaseAIAgent) -> Dict[str, Any]:
        """
        Serialize agent to dictionary with sanitization.

        This method gets the agent state and sanitizes it to ensure
        all values are JSON-serializable.

        Args:
            agent: Agent to serialize

        Returns:
            Serialized state dictionary (JSON-safe)
        """
        state = agent.to_dict()
        return AgentStateSerializer._sanitize_checkpoint(state)

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

    @staticmethod
    def _sanitize_checkpoint(checkpoint_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize checkpoint data to ensure JSON serializability.

        This method recursively processes checkpoint data to convert
        non-serializable types to serializable representations.

        Args:
            checkpoint_data: Checkpoint data to sanitize

        Returns:
            Sanitized checkpoint data (JSON-safe)

        Example:
            data = {
                "timestamp": datetime.utcnow(),
                "queue": asyncio.Queue(),
                "config": {"nested": datetime.utcnow()}
            }
            sanitized = AgentStateSerializer._sanitize_checkpoint(data)
            # All datetime objects converted to ISO strings
            # Queue converted to placeholder
        """
        return AgentStateSerializer._sanitize_dict(checkpoint_data)

    @staticmethod
    def _sanitize_dict(obj: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize dictionary recursively.

        Args:
            obj: Dictionary to sanitize

        Returns:
            Sanitized dictionary
        """
        result = {}
        for key, value in obj.items():
            try:
                result[key] = AgentStateSerializer._make_json_serializable(value)
            except Exception as e:
                logger.warning(f"Failed to sanitize key '{key}': {e}. Using placeholder.")
                result[key] = f"<non-serializable: {type(value).__name__}>"
        return result

    @staticmethod
    def _sanitize_list(obj: list) -> list:
        """
        Sanitize list recursively.

        Args:
            obj: List to sanitize

        Returns:
            Sanitized list
        """
        result = []
        for i, item in enumerate(obj):
            try:
                result.append(AgentStateSerializer._make_json_serializable(item))
            except Exception as e:
                logger.warning(f"Failed to sanitize list item at index {i}: {e}. Using placeholder.")
                result.append(f"<non-serializable: {type(item).__name__}>")
        return result

    @staticmethod
    def _make_json_serializable(obj: Any) -> Any:
        """
        Convert object to JSON-serializable form.

        Handles common non-serializable types:
        - datetime -> ISO string
        - asyncio.Queue -> placeholder
        - queue.Queue -> placeholder
        - ChainMap -> dict
        - dataclasses -> dict
        - dict -> recursive sanitization
        - list -> recursive sanitization

        Args:
            obj: Object to convert

        Returns:
            JSON-serializable representation

        Raises:
            TypeError: If object cannot be made serializable
        """
        # Handle None, bool, int, float, str (already serializable)
        if obj is None or isinstance(obj, (bool, int, float, str)):
            return obj

        # Handle datetime
        if isinstance(obj, datetime):
            return obj.isoformat()

        # Handle asyncio.Queue
        if isinstance(obj, asyncio.Queue):
            logger.warning("asyncio.Queue detected in checkpoint data. " "Queues cannot be serialized. Using placeholder.")
            return "<asyncio.Queue: not serializable>"

        # Handle queue.Queue
        if isinstance(obj, queue.Queue):
            logger.warning("queue.Queue detected in checkpoint data. " "Queues cannot be serialized. Using placeholder.")
            return "<queue.Queue: not serializable>"

        # Handle ChainMap
        if isinstance(obj, ChainMap):
            logger.debug("Converting ChainMap to dict for serialization")
            return AgentStateSerializer._sanitize_dict(dict(obj))

        # Handle dataclasses
        if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
            logger.debug(f"Converting dataclass {type(obj).__name__} to dict for serialization")
            return AgentStateSerializer._sanitize_dict(dataclasses.asdict(obj))

        # Handle dictionaries
        if isinstance(obj, dict):
            return AgentStateSerializer._sanitize_dict(obj)

        # Handle lists and tuples
        if isinstance(obj, (list, tuple)):
            sanitized_list = AgentStateSerializer._sanitize_list(list(obj))
            return sanitized_list if isinstance(obj, list) else tuple(sanitized_list)

        # Handle sets
        if isinstance(obj, set):
            logger.debug("Converting set to list for serialization")
            return AgentStateSerializer._sanitize_list(list(obj))

        # Handle bytes
        if isinstance(obj, bytes):
            logger.debug("Converting bytes to base64 string for serialization")
            import base64

            return base64.b64encode(obj).decode("utf-8")

        # Try to convert using __dict__ for custom objects
        if hasattr(obj, "__dict__"):
            logger.warning(f"Converting custom object {type(obj).__name__} using __dict__. " "This may not preserve all state.")
            return AgentStateSerializer._sanitize_dict(obj.__dict__)

        # Last resort: convert to string
        logger.warning(f"Object of type {type(obj).__name__} is not directly serializable. " "Converting to string representation.")
        return str(obj)


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
