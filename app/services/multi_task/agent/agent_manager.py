"""
Agent Manager

Implementation of the IAgentManager interface providing comprehensive agent management.
Supports both CrewAI and LangChain framework agents through unified interface.
"""

import logging
from typing import Dict, List, Any, Optional, TYPE_CHECKING
from datetime import datetime
from app.services.llm_integration import LLMIntegrationManager

from .base_agent import BaseAgent
from .factory.agent_factory import AgentFactory
from .registry.agent_registry import AgentRegistry
from ..core.interfaces.agent_manager import IAgentManager
from ..core.models.agent_models import AgentConfig, AgentModel, AgentRole, AgentStatus
from ..core.exceptions.task_exceptions import TaskValidationError
from ..config.config_manager import ConfigManager

if TYPE_CHECKING:
    from ..tools.langchain_integration_manager import LangChainIntegrationManager

logger = logging.getLogger(__name__)


class AgentManager(IAgentManager):
    """
    Comprehensive agent manager implementation.

    Provides centralized management of agents including creation, lifecycle management,
    task assignment, and performance monitoring.
    """

    def __init__(self, config_manager: Optional[ConfigManager] = None, llm_manager: Optional[LLMIntegrationManager] = None, tool_integration_manager: Optional['LangChainIntegrationManager'] = None):
        """
        Initialize the agent manager.

        Args:
            config_manager: Configuration manager for agent configs
            llm_manager: LLM integration manager for agent operations
            tool_integration_manager: Optional LangChain tool integration manager
        """
        self.config_manager = config_manager or ConfigManager()
        self.llm_manager = llm_manager
        self.tool_integration_manager = tool_integration_manager

        if self.llm_manager is None:
            raise ValueError("llm_manager is required for AgentManager initialization")

        self.agent_factory = AgentFactory(self.config_manager, self.llm_manager, self.tool_integration_manager)
        self.agent_registry = AgentRegistry(self.config_manager, self.agent_factory)

        # Manager state
        self._initialized = False
        self._startup_time = None

        logger.info("Agent manager initialized")

    async def initialize(self) -> None:
        """Initialize the agent manager."""
        if self._initialized:
            logger.warning("Agent manager already initialized")
            return

        try:
            self._startup_time = datetime.utcnow()

            # Initialize the agent registry (this only registers agents, doesn't activate them)
            await self.agent_registry.initialize()

            # Activate all registered agents
            await self._activate_registered_agents()

            self._initialized = True
            logger.info("Agent manager initialization completed")

        except Exception as e:
            logger.error(f"Failed to initialize agent manager: {e}")
            raise

    async def _activate_registered_agents(self) -> None:
        """Activate all registered agents."""
        try:
            agents = self.agent_registry.list_agents()
            activated_count = 0

            for agent in agents:
                try:
                    if agent.status != AgentStatus.ACTIVE:
                        await agent.activate()
                        activated_count += 1
                        logger.info(f"Activated agent: {agent.agent_id} ({agent.config.role.value})")
                except Exception as e:
                    logger.error(f"Failed to activate agent {agent.agent_id}: {e}")
                    # Continue with other agents instead of failing completely
                    continue

            logger.info(f"Activated {activated_count} agents")

        except Exception as e:
            logger.error(f"Failed to activate registered agents: {e}")
            raise

    async def create_agent(self, config: AgentConfig) -> AgentModel:
        """Create a new agent instance."""
        try:
            # Create agent using factory
            agent = self.agent_factory.create_agent(config)

            # Register agent in registry
            agent_id = await self.agent_registry.register_agent(agent)

            # Return agent model
            return agent.to_model()

        except Exception as e:
            logger.error(f"Failed to create agent: {e}")
            raise

    async def get_agent(self, agent_id: str) -> Optional[AgentModel]:
        """Retrieve an agent by its identifier."""
        agent = self.agent_registry.get_agent(agent_id)
        return agent.to_model() if agent else None

    async def get_agent_by_role(self, role: str) -> Optional[AgentModel]:
        """Retrieve an agent by its role."""
        try:
            agent_role = AgentRole(role.lower())
            agent = self.agent_registry.get_agent_by_role(agent_role)
            return agent.to_model() if agent else None
        except ValueError:
            logger.warning(f"Invalid agent role: {role}")
            return None

    async def list_agents(self, filter_criteria: Optional[Dict[str, Any]] = None) -> List[AgentModel]:
        """List all available agents."""
        agents = self.agent_registry.list_agents(filter_criteria)
        return [agent.to_model() for agent in agents]

    async def update_agent(self, agent_id: str, config: AgentConfig) -> AgentModel:
        """Update an existing agent's configuration."""
        try:
            # Get existing agent
            agent = self.agent_registry.get_agent(agent_id)
            if not agent:
                raise TaskValidationError(
                    message=f"Agent not found: {agent_id}",
                    validation_errors={"agent_not_found": agent_id}
                )

            # Validate new configuration
            validation_errors = self.agent_factory._validate_config(config)
            if validation_errors:
                raise TaskValidationError(
                    message="Agent configuration validation failed",
                    validation_errors={"config_errors": validation_errors}
                )

            # Update agent configuration
            agent.config = config
            agent.updated_at = datetime.utcnow()

            logger.info(f"Agent updated: {agent_id}")
            return agent.to_model()

        except Exception as e:
            logger.error(f"Failed to update agent {agent_id}: {e}")
            raise

    async def delete_agent(self, agent_id: str) -> bool:
        """Delete an agent."""
        try:
            return await self.agent_registry.unregister_agent(agent_id)
        except Exception as e:
            logger.error(f"Failed to delete agent {agent_id}: {e}")
            return False

    async def register_agent_type(self, agent_type: str, factory_func: callable) -> None:
        """Register a new agent type with its factory function."""
        try:
            self.agent_factory.register_custom_agent_type(agent_type, factory_func)
            logger.info(f"Registered custom agent type: {agent_type}")
        except Exception as e:
            logger.error(f"Failed to register agent type {agent_type}: {e}")
            raise

    async def get_available_agent_types(self) -> List[str]:
        """Get list of available agent types."""
        return self.agent_factory.get_available_agent_types()

    async def validate_agent_config(self, config: AgentConfig) -> Dict[str, Any]:
        """Validate an agent configuration."""
        try:
            validation_errors = self.agent_factory._validate_config(config)

            return {
                "is_valid": len(validation_errors) == 0,
                "errors": validation_errors,
                "warnings": [],  # Could be extended for warnings
                "validated_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error during agent config validation: {e}")
            return {
                "is_valid": False,
                "errors": [f"Validation process failed: {e}"],
                "warnings": [],
                "validated_at": datetime.utcnow().isoformat()
            }

    async def get_agent_capabilities(self, agent_id: str) -> Dict[str, Any]:
        """Get the capabilities of a specific agent."""
        try:
            agent = self.agent_registry.get_agent(agent_id)
            if not agent:
                raise TaskValidationError(
                    message=f"Agent not found: {agent_id}",
                    validation_errors={"agent_not_found": agent_id}
                )

            capabilities = agent.get_capabilities()

            return {
                "agent_id": agent_id,
                "role": agent.config.role.value,
                "capabilities": capabilities,
                "tools": agent.config.tools,
                "domain_specialization": agent.config.domain_specialization,
                "status": agent.status.value,
                "retrieved_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to get agent capabilities for {agent_id}: {e}")
            raise

    async def assign_tools_to_agent(self, agent_id: str, tool_names: List[str]) -> bool:
        """Assign tools to an agent."""
        try:
            agent = self.agent_registry.get_agent(agent_id)
            if not agent:
                logger.error(f"Agent not found: {agent_id}")
                return False

            # Update agent configuration with new tools
            agent.config.tools = tool_names
            agent.updated_at = datetime.utcnow()

            # Clear cached agent executor to force recreation with new tools
            agent._agent_executor = None

            logger.info(f"Tools assigned to agent {agent_id}: {tool_names}")
            return True

        except Exception as e:
            logger.error(f"Failed to assign tools to agent {agent_id}: {e}")
            return False

    async def get_agent_tools(self, agent_id: str) -> List[str]:
        """Get the tools assigned to an agent."""
        try:
            agent = self.agent_registry.get_agent(agent_id)
            if not agent:
                raise TaskValidationError(
                    message=f"Agent not found: {agent_id}",
                    validation_errors={"agent_not_found": agent_id}
                )

            return agent.config.tools.copy()

        except Exception as e:
            logger.error(f"Failed to get agent tools for {agent_id}: {e}")
            raise

    async def cleanup(self) -> None:
        """Clean up resources used by the agent manager."""
        try:
            logger.info("Cleaning up agent manager...")

            # Shutdown agent registry
            await self.agent_registry.shutdown()

            self._initialized = False
            logger.info("Agent manager cleanup completed")

        except Exception as e:
            logger.error(f"Error during agent manager cleanup: {e}")

    # Additional methods for enhanced functionality

    async def execute_agent_task(self, agent_id: str, task_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a task using a specific agent.

        Args:
            agent_id: ID of the agent to use
            task_data: Task data
            context: Execution context

        Returns:
            Task execution result
        """
        try:
            agent = self.agent_registry.get_agent(agent_id)
            if not agent:
                raise TaskValidationError(
                    message=f"Agent not found: {agent_id}",
                    validation_errors={"agent_not_found": agent_id}
                )

            # Execute task
            result = await agent.execute_task(task_data, context)

            logger.info(f"Task executed by agent {agent_id}")
            return result

        except Exception as e:
            logger.error(f"Failed to execute task with agent {agent_id}: {e}")
            raise

    async def assign_task_by_role(self, role: str, task_data: Dict[str, Any], context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Assign a task to an available agent with the specified role.

        Args:
            role: Required agent role
            task_data: Task data
            context: Task context

        Returns:
            Task execution result or None if no agent available
        """
        try:
            agent_role = AgentRole(role.lower())
            agent = await self.agent_registry.assign_task_to_agent(agent_role, task_data, context)

            if not agent:
                logger.warning(f"No available agent found for role: {role}")
                return None

            try:
                # Execute task
                result = await agent.execute_task(task_data, context)

                # Release agent
                self.agent_registry.release_agent(agent.agent_id)

                return result

            except Exception as e:
                # Ensure agent is released even if task fails
                self.agent_registry.release_agent(agent.agent_id)
                raise

        except ValueError:
            logger.error(f"Invalid agent role: {role}")
            return None
        except Exception as e:
            logger.error(f"Failed to assign task by role {role}: {e}")
            raise

    async def get_agent_performance_metrics(self) -> List[Dict[str, Any]]:
        """
        Get performance metrics for all agents.

        Returns:
            List of agent performance summaries
        """
        return self.agent_registry.get_agent_performance_summary()

    async def health_check_all_agents(self) -> Dict[str, Dict[str, Any]]:
        """
        Perform health check on all agents.

        Returns:
            Dictionary mapping agent IDs to health status
        """
        return await self.agent_registry.health_check_agents()

    def get_manager_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the agent manager.

        Returns:
            Dictionary containing manager statistics
        """
        registry_stats = self.agent_registry.get_registry_statistics()

        return {
            **registry_stats,
            "manager_initialized": self._initialized,
            "manager_uptime": (datetime.utcnow() - self._startup_time).total_seconds() if self._startup_time else 0,
            "available_agent_types": len(self.agent_factory.get_available_agent_types()),
            "config_manager_status": "active" if self.config_manager else "inactive"
        }

    async def create_agent_from_role(self, role_name: str, **overrides) -> AgentModel:
        """
        Create an agent from role configuration.

        Args:
            role_name: Name of the role
            **overrides: Configuration overrides

        Returns:
            Created agent model
        """
        try:
            agent = self.agent_factory.create_agent_from_role_config(role_name, **overrides)
            agent_id = await self.agent_registry.register_agent(agent)
            return agent.to_model()

        except Exception as e:
            logger.error(f"Failed to create agent from role {role_name}: {e}")
            raise

    async def clone_agent(self, agent_id: str, **config_overrides) -> AgentModel:
        """
        Clone an existing agent with optional configuration overrides.

        Args:
            agent_id: ID of agent to clone
            **config_overrides: Configuration overrides

        Returns:
            Cloned agent model
        """
        try:
            original_agent = self.agent_registry.get_agent(agent_id)
            if not original_agent:
                raise TaskValidationError(
                    message=f"Agent not found: {agent_id}",
                    validation_errors={"agent_not_found": agent_id}
                )

            cloned_agent = self.agent_factory.clone_agent(original_agent, **config_overrides)
            cloned_agent_id = await self.agent_registry.register_agent(cloned_agent)

            logger.info(f"Agent cloned: {agent_id} -> {cloned_agent_id}")
            return cloned_agent.to_model()

        except Exception as e:
            logger.error(f"Failed to clone agent {agent_id}: {e}")
            raise

    def is_initialized(self) -> bool:
        """Check if the agent manager is initialized."""
        return self._initialized

    def get_agent_count(self) -> int:
        """Get the total number of registered agents."""
        return len(self.agent_registry)

    def get_available_agent_count(self) -> int:
        """Get the number of available agents."""
        return len(self.agent_registry.get_available_agents())
