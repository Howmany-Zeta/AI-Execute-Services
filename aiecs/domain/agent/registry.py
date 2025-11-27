"""
Agent Registry

Central registry for tracking and managing active agents.
"""

import logging
from typing import Dict, List, Optional, Set

from .base_agent import BaseAIAgent
from .models import AgentState, AgentType
from .exceptions import AgentNotFoundError, AgentAlreadyRegisteredError

logger = logging.getLogger(__name__)


class AgentRegistry:
    """
    Central registry for tracking and managing active agents.

    Thread-safe registry for agent lifecycle management.
    """

    def __init__(self) -> None:
        """Initialize agent registry."""
        self._agents: Dict[str, BaseAIAgent] = {}
        self._agents_by_type: Dict[AgentType, Set[str]] = {}
        self._agents_by_state: Dict[AgentState, Set[str]] = {}

        logger.info("AgentRegistry initialized")

    def register(self, agent: BaseAIAgent) -> None:
        """
        Register an agent.

        Args:
            agent: Agent to register

        Raises:
            AgentAlreadyRegisteredError: If agent already registered
        """
        if agent.agent_id in self._agents:
            raise AgentAlreadyRegisteredError(agent.agent_id)

        # Register agent
        self._agents[agent.agent_id] = agent

        # Index by type
        if agent.agent_type not in self._agents_by_type:
            self._agents_by_type[agent.agent_type] = set()
        self._agents_by_type[agent.agent_type].add(agent.agent_id)

        # Index by state
        if agent.state not in self._agents_by_state:
            self._agents_by_state[agent.state] = set()
        self._agents_by_state[agent.state].add(agent.agent_id)

        logger.info(f"Agent registered: {agent.agent_id} ({agent.agent_type.value})")

    def unregister(self, agent_id: str) -> None:
        """
        Unregister an agent.

        Args:
            agent_id: Agent identifier

        Raises:
            AgentNotFoundError: If agent not found
        """
        agent = self.get(agent_id)

        # Remove from indexes
        if agent.agent_type in self._agents_by_type:
            self._agents_by_type[agent.agent_type].discard(agent_id)

        if agent.state in self._agents_by_state:
            self._agents_by_state[agent.state].discard(agent_id)

        # Remove from main registry
        del self._agents[agent_id]

        logger.info(f"Agent unregistered: {agent_id}")

    def get(self, agent_id: str) -> BaseAIAgent:
        """
        Get agent by ID.

        Args:
            agent_id: Agent identifier

        Returns:
            Agent instance

        Raises:
            AgentNotFoundError: If agent not found
        """
        if agent_id not in self._agents:
            raise AgentNotFoundError(agent_id)

        return self._agents[agent_id]

    def get_optional(self, agent_id: str) -> Optional[BaseAIAgent]:
        """
        Get agent by ID, returning None if not found.

        Args:
            agent_id: Agent identifier

        Returns:
            Agent instance or None
        """
        return self._agents.get(agent_id)

    def exists(self, agent_id: str) -> bool:
        """
        Check if agent exists.

        Args:
            agent_id: Agent identifier

        Returns:
            True if agent exists
        """
        return agent_id in self._agents

    def list_all(self) -> List[BaseAIAgent]:
        """
        List all registered agents.

        Returns:
            List of all agents
        """
        return list(self._agents.values())

    def list_by_type(self, agent_type: AgentType) -> List[BaseAIAgent]:
        """
        List agents by type.

        Args:
            agent_type: Agent type

        Returns:
            List of agents of specified type
        """
        agent_ids = self._agents_by_type.get(agent_type, set())
        return [self._agents[aid] for aid in agent_ids if aid in self._agents]

    def list_by_state(self, state: AgentState) -> List[BaseAIAgent]:
        """
        List agents by state.

        Args:
            state: Agent state

        Returns:
            List of agents in specified state
        """
        agent_ids = self._agents_by_state.get(state, set())
        return [self._agents[aid] for aid in agent_ids if aid in self._agents]

    def update_state_index(self, agent_id: str, old_state: AgentState, new_state: AgentState) -> None:
        """
        Update state index when agent state changes.

        Args:
            agent_id: Agent identifier
            old_state: Previous state
            new_state: New state
        """
        # Remove from old state index
        if old_state in self._agents_by_state:
            self._agents_by_state[old_state].discard(agent_id)

        # Add to new state index
        if new_state not in self._agents_by_state:
            self._agents_by_state[new_state] = set()
        self._agents_by_state[new_state].add(agent_id)

    def count(self) -> int:
        """
        Get total number of registered agents.

        Returns:
            Number of agents
        """
        return len(self._agents)

    def count_by_type(self, agent_type: AgentType) -> int:
        """
        Get count of agents by type.

        Args:
            agent_type: Agent type

        Returns:
            Number of agents of specified type
        """
        return len(self._agents_by_type.get(agent_type, set()))

    def count_by_state(self, state: AgentState) -> int:
        """
        Get count of agents by state.

        Args:
            state: Agent state

        Returns:
            Number of agents in specified state
        """
        return len(self._agents_by_state.get(state, set()))

    def get_stats(self) -> Dict:
        """
        Get registry statistics.

        Returns:
            Dictionary with stats
        """
        return {
            "total_agents": self.count(),
            "by_type": {agent_type.value: len(agent_ids) for agent_type, agent_ids in self._agents_by_type.items()},
            "by_state": {state.value: len(agent_ids) for state, agent_ids in self._agents_by_state.items()},
        }

    def clear(self) -> None:
        """Clear all agents from registry."""
        self._agents.clear()
        self._agents_by_type.clear()
        self._agents_by_state.clear()
        logger.info("AgentRegistry cleared")


# Global registry instance
_global_registry: Optional[AgentRegistry] = None


def get_global_registry() -> AgentRegistry:
    """
    Get or create global agent registry.

    Returns:
        Global AgentRegistry instance
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = AgentRegistry()
    return _global_registry


def reset_global_registry() -> None:
    """Reset global registry (primarily for testing)."""
    global _global_registry
    _global_registry = None
