"""
Example Checkpointer Implementations

This module demonstrates how to implement custom checkpointers for agent state persistence.
Checkpointers follow the CheckpointerProtocol interface and can use any storage backend.
"""

import json
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class InMemoryCheckpointer:
    """
    Simple in-memory checkpointer for testing and development.

    This checkpointer stores all checkpoints in memory and is useful for
    testing and development. Data is lost when the process terminates.

    Example:
        checkpointer = InMemoryCheckpointer()
        agent = HybridAgent(
            agent_id="agent-1",
            name="My Agent",
            agent_type=AgentType.HYBRID,
            config=config,
            checkpointer=checkpointer
        )

        # Save checkpoint
        checkpoint_id = await agent.save_checkpoint(session_id="session-1")

        # Load checkpoint
        success = await agent.load_checkpoint(session_id="session-1")
    """

    def __init__(self):
        """Initialize in-memory storage."""
        self._checkpoints: Dict[str, Dict[str, Any]] = {}
        logger.info("InMemoryCheckpointer initialized")

    async def save_checkpoint(
        self, agent_id: str, session_id: str, checkpoint_data: Dict[str, Any]
    ) -> str:
        """Save checkpoint to memory."""
        checkpoint_id = str(uuid.uuid4())
        key = f"{agent_id}:{session_id}:{checkpoint_id}"

        self._checkpoints[key] = {
            "checkpoint_id": checkpoint_id,
            "agent_id": agent_id,
            "session_id": session_id,
            "data": checkpoint_data,
            "created_at": datetime.utcnow().isoformat(),
        }

        logger.debug(f"Saved checkpoint {checkpoint_id} for agent {agent_id}")
        return checkpoint_id

    async def load_checkpoint(
        self, agent_id: str, session_id: str, checkpoint_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Load checkpoint from memory."""
        if checkpoint_id:
            # Load specific checkpoint
            key = f"{agent_id}:{session_id}:{checkpoint_id}"
            checkpoint = self._checkpoints.get(key)
            if checkpoint:
                logger.debug(f"Loaded checkpoint {checkpoint_id} for agent {agent_id}")
                return checkpoint["data"]
            return None
        else:
            # Load latest checkpoint for this agent/session
            matching = [
                cp
                for key, cp in self._checkpoints.items()
                if key.startswith(f"{agent_id}:{session_id}:")
            ]
            if matching:
                # Sort by created_at and get latest
                latest = max(matching, key=lambda x: x["created_at"])
                logger.debug(
                    f"Loaded latest checkpoint {latest['checkpoint_id']} for agent {agent_id}"
                )
                return latest["data"]
            return None

    async def list_checkpoints(self, agent_id: str, session_id: str) -> List[str]:
        """List all checkpoint IDs for an agent/session."""
        checkpoint_ids = [
            cp["checkpoint_id"]
            for key, cp in self._checkpoints.items()
            if key.startswith(f"{agent_id}:{session_id}:")
        ]
        return sorted(checkpoint_ids)


class FileCheckpointer:
    """
    File-based checkpointer for persistent storage.

    This checkpointer stores checkpoints as JSON files in a directory structure.
    Suitable for development and small-scale production deployments.

    Example:
        checkpointer = FileCheckpointer(base_dir="./checkpoints")
        agent = HybridAgent(
            agent_id="agent-1",
            name="My Agent",
            agent_type=AgentType.HYBRID,
            config=config,
            checkpointer=checkpointer
        )
    """

    def __init__(self, base_dir: str = "./checkpoints"):
        """
        Initialize file-based checkpointer.

        Args:
            base_dir: Base directory for checkpoint storage
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"FileCheckpointer initialized with base_dir={base_dir}")

    def _get_checkpoint_path(
        self, agent_id: str, session_id: str, checkpoint_id: str
    ) -> Path:
        """Get file path for a checkpoint."""
        agent_dir = self.base_dir / agent_id / session_id
        agent_dir.mkdir(parents=True, exist_ok=True)
        return agent_dir / f"{checkpoint_id}.json"

    async def save_checkpoint(
        self, agent_id: str, session_id: str, checkpoint_data: Dict[str, Any]
    ) -> str:
        """Save checkpoint to file."""
        checkpoint_id = str(uuid.uuid4())
        file_path = self._get_checkpoint_path(agent_id, session_id, checkpoint_id)

        checkpoint = {
            "checkpoint_id": checkpoint_id,
            "agent_id": agent_id,
            "session_id": session_id,
            "data": checkpoint_data,
            "created_at": datetime.utcnow().isoformat(),
        }

        with open(file_path, "w") as f:
            json.dump(checkpoint, f, indent=2, default=str)

        logger.debug(f"Saved checkpoint {checkpoint_id} to {file_path}")
        return checkpoint_id

    async def load_checkpoint(
        self, agent_id: str, session_id: str, checkpoint_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Load checkpoint from file."""
        if checkpoint_id:
            # Load specific checkpoint
            file_path = self._get_checkpoint_path(agent_id, session_id, checkpoint_id)
            if file_path.exists():
                with open(file_path, "r") as f:
                    checkpoint = json.load(f)
                logger.debug(f"Loaded checkpoint {checkpoint_id} from {file_path}")
                return checkpoint["data"]
            return None
        else:
            # Load latest checkpoint
            session_dir = self.base_dir / agent_id / session_id
            if not session_dir.exists():
                return None

            checkpoint_files = list(session_dir.glob("*.json"))
            if not checkpoint_files:
                return None

            # Get latest by modification time
            latest_file = max(checkpoint_files, key=lambda p: p.stat().st_mtime)
            with open(latest_file, "r") as f:
                checkpoint = json.load(f)

            logger.debug(
                f"Loaded latest checkpoint {checkpoint['checkpoint_id']} from {latest_file}"
            )
            return checkpoint["data"]

    async def list_checkpoints(self, agent_id: str, session_id: str) -> List[str]:
        """List all checkpoint IDs for an agent/session."""
        session_dir = self.base_dir / agent_id / session_id
        if not session_dir.exists():
            return []

        checkpoint_ids = []
        for file_path in session_dir.glob("*.json"):
            with open(file_path, "r") as f:
                checkpoint = json.load(f)
                checkpoint_ids.append(checkpoint["checkpoint_id"])

        return sorted(checkpoint_ids)


# Example usage
async def example_usage():
    """Demonstrate checkpointer usage."""
    from aiecs.domain.agent import HybridAgent
    from aiecs.domain.agent.models import AgentConfiguration, AgentType

    # Create checkpointer
    checkpointer = FileCheckpointer(base_dir="./checkpoints")

    # Create agent with checkpointer
    agent = HybridAgent(
        agent_id="agent-1",
        name="My Agent",
        agent_type=AgentType.HYBRID,
        config=AgentConfiguration(),
        checkpointer=checkpointer,
    )

    # Save checkpoint
    session_id = "session-123"
    checkpoint_id = await agent.save_checkpoint(session_id=session_id)
    print(f"Saved checkpoint: {checkpoint_id}")

    # List checkpoints
    checkpoints = await checkpointer.list_checkpoints(
        agent_id=agent.agent_id, session_id=session_id
    )
    print(f"Available checkpoints: {checkpoints}")

    # Load checkpoint
    success = await agent.load_checkpoint(session_id=session_id)
    print(f"Loaded checkpoint: {success}")

    # Load specific checkpoint
    success = await agent.load_checkpoint(
        session_id=session_id, checkpoint_id=checkpoint_id
    )
    print(f"Loaded specific checkpoint: {success}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(example_usage())

