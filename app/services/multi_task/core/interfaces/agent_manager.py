"""
Agent Manager Interface

Defines the contract for agent management implementations in the multi-task architecture.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from ..models.agent_models import AgentConfig, AgentModel


class IAgentManager(ABC):
    """
    Abstract interface for agent management implementations.

    This interface defines the core contract for managing AI agents,
    including creation, configuration, and lifecycle management.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the agent manager.

        Sets up agent registry, loads configurations, and prepares
        the manager for agent operations.

        Raises:
            Exception: If initialization fails
        """
        pass

    @abstractmethod
    async def create_agent(self, config: AgentConfig) -> AgentModel:
        """
        Create a new agent instance.

        Args:
            config: Configuration for the agent to create

        Returns:
            The created agent model

        Raises:
            AgentCreationError: If agent creation fails
            ValidationError: If configuration is invalid
        """
        pass

    @abstractmethod
    async def get_agent(self, agent_id: str) -> Optional[AgentModel]:
        """
        Retrieve an agent by its identifier.

        Args:
            agent_id: Unique identifier of the agent

        Returns:
            The agent model if found, None otherwise

        Raises:
            AgentException: If retrieval fails
        """
        pass

    @abstractmethod
    async def get_agent_by_role(self, role: str) -> Optional[AgentModel]:
        """
        Retrieve an agent by its role.

        Args:
            role: Role name of the agent (e.g., 'intent_parser', 'planner')

        Returns:
            The agent model if found, None otherwise

        Raises:
            AgentException: If retrieval fails
        """
        pass

    @abstractmethod
    async def list_agents(self, filter_criteria: Optional[Dict[str, Any]] = None) -> List[AgentModel]:
        """
        List all available agents.

        Args:
            filter_criteria: Optional criteria to filter agents

        Returns:
            List of agent models matching the criteria

        Raises:
            AgentException: If listing fails
        """
        pass

    @abstractmethod
    async def update_agent(self, agent_id: str, config: AgentConfig) -> AgentModel:
        """
        Update an existing agent's configuration.

        Args:
            agent_id: Unique identifier of the agent to update
            config: New configuration for the agent

        Returns:
            The updated agent model

        Raises:
            AgentNotFoundException: If agent is not found
            ValidationError: If configuration is invalid
            AgentException: If update fails
        """
        pass

    @abstractmethod
    async def delete_agent(self, agent_id: str) -> bool:
        """
        Delete an agent.

        Args:
            agent_id: Unique identifier of the agent to delete

        Returns:
            True if agent was successfully deleted, False otherwise

        Raises:
            AgentNotFoundException: If agent is not found
            AgentException: If deletion fails
        """
        pass

    @abstractmethod
    async def register_agent_type(self, agent_type: str, factory_func: callable) -> None:
        """
        Register a new agent type with its factory function.

        Args:
            agent_type: Name of the agent type
            factory_func: Function to create agents of this type

        Raises:
            AgentRegistrationError: If registration fails
        """
        pass

    @abstractmethod
    async def get_available_agent_types(self) -> List[str]:
        """
        Get list of available agent types.

        Returns:
            List of registered agent type names

        Raises:
            AgentException: If retrieval fails
        """
        pass

    @abstractmethod
    async def validate_agent_config(self, config: AgentConfig) -> Dict[str, Any]:
        """
        Validate an agent configuration.

        Args:
            config: Agent configuration to validate

        Returns:
            Validation result with status and any error messages

        Raises:
            ValidationError: If validation process fails
        """
        pass

    @abstractmethod
    async def get_agent_capabilities(self, agent_id: str) -> Dict[str, Any]:
        """
        Get the capabilities of a specific agent.

        Args:
            agent_id: Unique identifier of the agent

        Returns:
            Dictionary describing agent capabilities

        Raises:
            AgentNotFoundException: If agent is not found
            AgentException: If capability retrieval fails
        """
        pass

    @abstractmethod
    async def assign_tools_to_agent(self, agent_id: str, tool_names: List[str]) -> bool:
        """
        Assign tools to an agent.

        Args:
            agent_id: Unique identifier of the agent
            tool_names: List of tool names to assign

        Returns:
            True if tools were successfully assigned, False otherwise

        Raises:
            AgentNotFoundException: If agent is not found
            ToolNotFoundException: If any tool is not found
            AgentException: If assignment fails
        """
        pass

    @abstractmethod
    async def get_agent_tools(self, agent_id: str) -> List[str]:
        """
        Get the tools assigned to an agent.

        Args:
            agent_id: Unique identifier of the agent

        Returns:
            List of tool names assigned to the agent

        Raises:
            AgentNotFoundException: If agent is not found
            AgentException: If tool retrieval fails
        """
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """
        Clean up resources used by the agent manager.

        This method should be called when the manager is being shut down
        to properly release any held resources.
        """
        pass
