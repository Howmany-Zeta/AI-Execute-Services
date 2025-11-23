"""
Agent Lifecycle Management

Manages agent lifecycle transitions and state management.
"""

import logging
from typing import Dict, Any, Optional, List

from .base_agent import BaseAIAgent
from .models import AgentState
from .registry import AgentRegistry, get_global_registry
from .exceptions import (
    AgentInitializationError,
)

logger = logging.getLogger(__name__)


class AgentLifecycleManager:
    """
    Manages agent lifecycle: creation, initialization, activation, deactivation, shutdown.

    Ensures proper state transitions and coordinates with registry.
    """

    def __init__(self, registry: Optional[AgentRegistry] = None):
        """
        Initialize lifecycle manager.

        Args:
            registry: Optional custom registry (uses global if not provided)
        """
        self.registry = registry or get_global_registry()
        logger.info("AgentLifecycleManager initialized")

    async def create_and_initialize(self, agent: BaseAIAgent) -> BaseAIAgent:
        """
        Register and initialize an agent.

        Args:
            agent: Agent to initialize

        Returns:
            Initialized agent

        Raises:
            AgentInitializationError: If initialization fails
        """
        try:
            # Register agent
            self.registry.register(agent)
            logger.info(f"Agent {agent.agent_id} registered")

            # Initialize agent
            await agent.initialize()
            logger.info(f"Agent {agent.agent_id} initialized")

            return agent

        except Exception as e:
            logger.error(f"Failed to create and initialize agent {agent.agent_id}: {e}")

            # Cleanup on failure
            try:
                if self.registry.exists(agent.agent_id):
                    self.registry.unregister(agent.agent_id)
            except Exception as cleanup_error:
                logger.error(f"Cleanup failed: {cleanup_error}")

            raise AgentInitializationError(
                f"Agent initialization failed: {str(e)}",
                agent_id=agent.agent_id,
            )

    async def activate(self, agent_id: str) -> None:
        """
        Activate an agent.

        Args:
            agent_id: Agent identifier

        Raises:
            AgentNotFoundError: If agent not found
            InvalidStateTransitionError: If activation not allowed
        """
        agent = self.registry.get(agent_id)

        try:
            await agent.activate()
            logger.info(f"Agent {agent_id} activated")
        except Exception as e:
            logger.error(f"Failed to activate agent {agent_id}: {e}")
            raise

    async def deactivate(self, agent_id: str) -> None:
        """
        Deactivate an agent.

        Args:
            agent_id: Agent identifier

        Raises:
            AgentNotFoundError: If agent not found
            InvalidStateTransitionError: If deactivation not allowed
        """
        agent = self.registry.get(agent_id)

        try:
            await agent.deactivate()
            logger.info(f"Agent {agent_id} deactivated")
        except Exception as e:
            logger.error(f"Failed to deactivate agent {agent_id}: {e}")
            raise

    async def shutdown(self, agent_id: str, unregister: bool = True) -> None:
        """
        Shutdown an agent.

        Args:
            agent_id: Agent identifier
            unregister: Whether to unregister after shutdown

        Raises:
            AgentNotFoundError: If agent not found
        """
        agent = self.registry.get(agent_id)

        try:
            await agent.shutdown()
            logger.info(f"Agent {agent_id} shut down")

            if unregister:
                self.registry.unregister(agent_id)
                logger.info(f"Agent {agent_id} unregistered")

        except Exception as e:
            logger.error(f"Failed to shutdown agent {agent_id}: {e}")
            raise

    async def restart(self, agent_id: str) -> None:
        """
        Restart an agent (deactivate → initialize → activate).

        Args:
            agent_id: Agent identifier

        Raises:
            AgentNotFoundError: If agent not found
        """
        agent = self.registry.get(agent_id)

        try:
            # Deactivate
            if agent.state in [AgentState.ACTIVE, AgentState.BUSY]:
                await agent.deactivate()

            # Re-initialize
            await agent.initialize()

            # Re-activate
            await agent.activate()

            logger.info(f"Agent {agent_id} restarted")

        except Exception as e:
            logger.error(f"Failed to restart agent {agent_id}: {e}")
            raise

    async def shutdown_all(self) -> Dict[str, Any]:
        """
        Shutdown all registered agents.

        Returns:
            Dictionary with shutdown results
        """
        results: Dict[str, Any] = {
            "success": [],
            "failed": [],
            "total": self.registry.count(),
        }

        agents = self.registry.list_all()

        for agent in agents:
            try:
                await self.shutdown(agent.agent_id, unregister=True)
                results["success"].append(agent.agent_id)
            except Exception as e:
                logger.error(f"Failed to shutdown agent {agent.agent_id}: {e}")
                results["failed"].append(
                    {
                        "agent_id": agent.agent_id,
                        "error": str(e),
                    }
                )

        logger.info(f"Shutdown all agents: {len(results['success'])} succeeded, " f"{len(results['failed'])} failed")

        return results

    def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """
        Get agent status information.

        Args:
            agent_id: Agent identifier

        Returns:
            Status dictionary

        Raises:
            AgentNotFoundError: If agent not found
        """
        agent = self.registry.get(agent_id)

        return {
            "agent_id": agent.agent_id,
            "name": agent.name,
            "type": agent.agent_type.value,
            "state": agent.state.value,
            "version": agent.version,
            "created_at": (agent.created_at.isoformat() if agent.created_at else None),
            "last_active_at": (agent.last_active_at.isoformat() if agent.last_active_at else None),
            "current_task_id": agent._current_task_id,
            "metrics": {
                "total_tasks_executed": agent.get_metrics().total_tasks_executed,
                "successful_tasks": agent.get_metrics().successful_tasks,
                "failed_tasks": agent.get_metrics().failed_tasks,
                "average_execution_time": agent.get_metrics().average_execution_time,
                "total_tool_calls": agent.get_metrics().total_tool_calls,
            },
        }

    def list_agent_statuses(self, agent_type: Optional[str] = None, state: Optional[str] = None) -> "List[Dict[str, Any]]":
        """
        List agent statuses with optional filtering.

        Args:
            agent_type: Optional filter by agent type
            state: Optional filter by state

        Returns:
            List of status dictionaries
        """
        agents = self.registry.list_all()

        # Filter by type
        if agent_type:
            from .models import AgentType

            try:
                type_enum = AgentType(agent_type)
                agents = [a for a in agents if a.agent_type == type_enum]
            except ValueError:
                logger.warning(f"Invalid agent type: {agent_type}")

        # Filter by state
        if state:
            from .models import AgentState

            try:
                state_enum = AgentState(state)
                agents = [a for a in agents if a.state == state_enum]
            except ValueError:
                logger.warning(f"Invalid state: {state}")

        return [self.get_agent_status(a.agent_id) for a in agents]


# Global lifecycle manager
_global_lifecycle_manager: Optional[AgentLifecycleManager] = None


def get_global_lifecycle_manager() -> AgentLifecycleManager:
    """
    Get or create global lifecycle manager.

    Returns:
        Global AgentLifecycleManager instance
    """
    global _global_lifecycle_manager
    if _global_lifecycle_manager is None:
        _global_lifecycle_manager = AgentLifecycleManager()
    return _global_lifecycle_manager


def reset_global_lifecycle_manager() -> None:
    """Reset global lifecycle manager (primarily for testing)."""
    global _global_lifecycle_manager
    _global_lifecycle_manager = None
