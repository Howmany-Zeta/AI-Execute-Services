"""
Agent Registry

Central registry for managing agent instances and their lifecycle.
"""

import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import asyncio

from ..base_agent import BaseAgent
from ...core.models.agent_models import AgentModel, AgentStatus, AgentRole
from ...core.exceptions.task_exceptions import TaskValidationError
from ...config.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class AgentRegistry:
    """
    Central registry for managing agent instances.

    Provides functionality for agent registration, discovery, lifecycle management,
    and coordination between different agents in the system.
    """

    def __init__(self, config_manager: Optional[ConfigManager] = None, agent_factory=None):
        """
        Initialize the agent registry.

        Args:
            config_manager: Configuration manager for agent configs
            agent_factory: Agent factory instance (optional, will be created if not provided)
        """
        self.config_manager = config_manager or ConfigManager()
        self.agent_factory = agent_factory

        # Agent storage
        self._agents: Dict[str, BaseAgent] = {}
        self._agents_by_role: Dict[str, List[BaseAgent]] = {}
        self._agent_metadata: Dict[str, Dict[str, Any]] = {}

        # Registry state
        self._initialized = False
        self._startup_time = None

        logger.info("Agent registry initialized")

    async def initialize(self) -> None:
        """Initialize the agent registry and load default agents."""
        if self._initialized:
            logger.warning("Agent registry already initialized")
            return

        try:
            self._startup_time = datetime.utcnow()

            # Create agents from configuration only if agent_factory is available
            if self.agent_factory:
                agents = self.agent_factory.create_agents_from_config()

                # Register all created agents
                for role_name, agent in agents.items():
                    await self.register_agent(agent)
            else:
                logger.info("No agent factory provided, skipping default agent creation")

            self._initialized = True
            logger.info(f"Agent registry initialized with {len(self._agents)} agents")

        except Exception as e:
            logger.error(f"Failed to initialize agent registry: {e}")
            raise TaskValidationError(
                message=f"Agent registry initialization failed: {e}",
                validation_errors={"initialization_error": str(e)}
            )

    async def register_agent(self, agent: BaseAgent) -> str:
        """
        Register an agent in the registry.

        Args:
            agent: Agent to register

        Returns:
            Agent ID

        Raises:
            TaskValidationError: If registration fails
        """
        try:
            # Validate agent
            validation_errors = agent.validate_config()
            if validation_errors:
                raise TaskValidationError(
                    message="Agent validation failed",
                    validation_errors={"validation_errors": validation_errors}
                )

            # Register in main storage (without activating)
            self._agents[agent.agent_id] = agent

            # Register by role - convert role to string for consistent key storage
            role = agent.config.role
            role_key = role.value if hasattr(role, 'value') else str(role)

            if role_key not in self._agents_by_role:
                self._agents_by_role[role_key] = []
            self._agents_by_role[role_key].append(agent)

            # Store metadata
            self._agent_metadata[agent.agent_id] = {
                "registered_at": datetime.utcnow(),
                "registration_source": "registry",
                "last_health_check": None,
                "total_tasks": 0,
                "last_task_time": None
            }

            logger.info(f"Agent registered: {agent.agent_id} ({role_key})")
            return agent.agent_id

        except Exception as e:
            logger.error(f"Failed to register agent: {e}")
            raise TaskValidationError(
                message=f"Agent registration failed: {e}",
                validation_errors={"registration_error": str(e)}
            )

    async def register_agents(self, agents: Dict[Any, BaseAgent]) -> List[str]:
        """
        Register multiple agents in the registry.

        Args:
            agents: Dictionary mapping agent identifiers (can be AgentRole enum or string) to Agent objects

        Returns:
            List of registered agent IDs

        Raises:
            TaskValidationError: If any registration fails
        """
        registered_ids = []
        failed_registrations = []

        for agent_identifier, agent in agents.items():
            try:
                # Convert agent identifier to string for consistent storage
                if hasattr(agent_identifier, 'value'):  # Check if it's an enum
                    agent_key = agent_identifier.value
                else:
                    agent_key = str(agent_identifier)

                # Register the individual agent
                agent_id = await self.register_agent(agent)
                registered_ids.append(agent_id)

                logger.debug(f"Successfully registered agent '{agent_key}' with ID: {agent_id}")

            except Exception as e:
                error_msg = f"Failed to register agent '{agent_identifier}': {e}"
                logger.error(error_msg)
                failed_registrations.append(error_msg)

        if failed_registrations:
            # If some registrations failed, log the errors but don't fail completely
            logger.warning(f"Some agent registrations failed: {failed_registrations}")

        logger.info(f"Successfully registered {len(registered_ids)} agents out of {len(agents)} total")
        return registered_ids

    async def unregister_agent(self, agent_id: str) -> bool:
        """
        Unregister an agent from the registry.

        Args:
            agent_id: ID of agent to unregister

        Returns:
            True if successfully unregistered

        Raises:
            TaskValidationError: If unregistration fails
        """
        try:
            if agent_id not in self._agents:
                logger.warning(f"Agent not found for unregistration: {agent_id}")
                return False

            agent = self._agents[agent_id]

            # Deactivate agent
            await agent.deactivate()

            # Remove from role mapping
            role = agent.config.role
            role_key = role.value if hasattr(role, 'value') else str(role)
            if role_key in self._agents_by_role:
                self._agents_by_role[role_key] = [
                    a for a in self._agents_by_role[role_key] if a.agent_id != agent_id
                ]
                if not self._agents_by_role[role_key]:
                    del self._agents_by_role[role_key]

            # Remove from main storage
            del self._agents[agent_id]
            del self._agent_metadata[agent_id]

            logger.info(f"Agent unregistered: {agent_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to unregister agent {agent_id}: {e}")
            raise TaskValidationError(
                message=f"Agent unregistration failed: {e}",
                validation_errors={"unregistration_error": str(e)}
            )

    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """
        Get an agent by ID.

        Args:
            agent_id: Agent ID

        Returns:
            Agent instance or None if not found
        """
        return self._agents.get(agent_id)

    def get_agent_by_role(self, role: Union[AgentRole, str]) -> Optional[BaseAgent]:
        """
        Get the first available agent by role.

        Args:
            role: Agent role (enum or string)

        Returns:
            Agent instance or None if not found
        """
        role_key = role.value if hasattr(role, 'value') else str(role)
        agents = self._agents_by_role.get(role_key, [])
        for agent in agents:
            if agent.status == AgentStatus.ACTIVE:
                return agent
        return agents[0] if agents else None

    def get_agents_by_role(self, role: Union[AgentRole, str]) -> List[BaseAgent]:
        """
        Get all agents by role.

        Args:
            role: Agent role (enum or string)

        Returns:
            List of agent instances
        """
        role_key = role.value if hasattr(role, 'value') else str(role)
        return self._agents_by_role.get(role_key, []).copy()

    def list_agents(self, filter_criteria: Optional[Dict[str, Any]] = None) -> List[BaseAgent]:
        """
        List all agents with optional filtering.

        Args:
            filter_criteria: Optional criteria to filter agents

        Returns:
            List of agent instances
        """
        agents = list(self._agents.values())

        if not filter_criteria:
            return agents

        filtered_agents = []
        for agent in agents:
            match = True

            # Filter by status
            if 'status' in filter_criteria:
                if agent.status != filter_criteria['status']:
                    match = False

            # Filter by role
            if 'role' in filter_criteria:
                if agent.config.role != filter_criteria['role']:
                    match = False

            # Filter by agent type
            if 'agent_type' in filter_criteria:
                if agent.config.agent_type != filter_criteria['agent_type']:
                    match = False

            # Filter by availability
            if 'available' in filter_criteria:
                is_available = agent.status == AgentStatus.ACTIVE
                if is_available != filter_criteria['available']:
                    match = False

            if match:
                filtered_agents.append(agent)

        return filtered_agents

    def get_available_agents(self) -> List[BaseAgent]:
        """
        Get all available agents.

        Returns:
            List of available agent instances
        """
        return self.list_agents({'available': True})

    def get_agent_models(self) -> List[AgentModel]:
        """
        Get agent models for all registered agents.

        Returns:
            List of agent models
        """
        return [agent.to_model() for agent in self._agents.values()]

    async def health_check_agents(self) -> Dict[str, Dict[str, Any]]:
        """
        Perform health check on all registered agents.

        Returns:
            Dictionary mapping agent IDs to health status
        """
        health_results = {}

        for agent_id, agent in self._agents.items():
            try:
                # Basic health check
                health_status = {
                    "status": agent.status.value,
                    "healthy": agent.status in [AgentStatus.ACTIVE, AgentStatus.BUSY],
                    "last_active": agent.last_active_at.isoformat() if agent.last_active_at else None,
                    "total_tasks": agent.total_tasks_executed,
                    "success_rate": agent.successful_tasks / agent.total_tasks_executed if agent.total_tasks_executed > 0 else 0.0,
                    "average_execution_time": agent.average_execution_time,
                    "check_time": datetime.utcnow().isoformat()
                }

                # Update metadata
                self._agent_metadata[agent_id]["last_health_check"] = datetime.utcnow()

                health_results[agent_id] = health_status

            except Exception as e:
                logger.error(f"Health check failed for agent {agent_id}: {e}")
                health_results[agent_id] = {
                    "status": "error",
                    "healthy": False,
                    "error": str(e),
                    "check_time": datetime.utcnow().isoformat()
                }

        return health_results

    async def assign_task_to_agent(self, role: Union[AgentRole, str], task_data: Dict[str, Any], context: Dict[str, Any]) -> Optional[BaseAgent]:
        """
        Assign a task to an available agent with the specified role.

        Args:
            role: Required agent role (enum or string)
            task_data: Task data
            context: Task context

        Returns:
            Assigned agent or None if no agent available
        """
        agents = self.get_agents_by_role(role)
        role_value = role.value if hasattr(role, 'value') else str(role)

        # Find available agent
        for agent in agents:
            if agent.status == AgentStatus.ACTIVE:
                # Mark agent as busy
                task_id = context.get('task_id', 'unknown')
                agent.set_busy(task_id)

                # Update metadata
                self._agent_metadata[agent.agent_id]["total_tasks"] += 1
                self._agent_metadata[agent.agent_id]["last_task_time"] = datetime.utcnow()

                logger.info(f"Task assigned to agent {agent.agent_id} ({role_value})")
                return agent

        logger.warning(f"No available agent found for role: {role_value}")
        return None

    def release_agent(self, agent_id: str) -> bool:
        """
        Release an agent from its current task.

        Args:
            agent_id: Agent ID

        Returns:
            True if successfully released
        """
        agent = self.get_agent(agent_id)
        if agent and agent.status == AgentStatus.BUSY:
            agent.set_available()
            logger.info(f"Agent released: {agent_id}")
            return True
        return False

    def get_registry_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the agent registry.

        Returns:
            Dictionary containing registry statistics
        """
        total_agents = len(self._agents)
        active_agents = len([a for a in self._agents.values() if a.status == AgentStatus.ACTIVE])
        busy_agents = len([a for a in self._agents.values() if a.status == AgentStatus.BUSY])

        # Role distribution
        role_distribution = {}
        for role_key, agents in self._agents_by_role.items():
            role_distribution[role_key] = len(agents)

        # Performance metrics
        total_tasks = sum(agent.total_tasks_executed for agent in self._agents.values())
        successful_tasks = sum(agent.successful_tasks for agent in self._agents.values())

        return {
            "total_agents": total_agents,
            "active_agents": active_agents,
            "busy_agents": busy_agents,
            "inactive_agents": total_agents - active_agents - busy_agents,
            "role_distribution": role_distribution,
            "total_tasks_executed": total_tasks,
            "successful_tasks": successful_tasks,
            "overall_success_rate": successful_tasks / total_tasks if total_tasks > 0 else 0.0,
            "registry_uptime": (datetime.utcnow() - self._startup_time).total_seconds() if self._startup_time else 0,
            "initialized": self._initialized
        }

    def get_agent_performance_summary(self) -> List[Dict[str, Any]]:
        """
        Get performance summary for all agents.

        Returns:
            List of agent performance summaries
        """
        summaries = []

        for agent in self._agents.values():
            summary = {
                "agent_id": agent.agent_id,
                "role": agent.config.role.value,
                "status": agent.status.value,
                "total_tasks": agent.total_tasks_executed,
                "successful_tasks": agent.successful_tasks,
                "failed_tasks": agent.failed_tasks,
                "success_rate": agent.successful_tasks / agent.total_tasks_executed if agent.total_tasks_executed > 0 else 0.0,
                "average_execution_time": agent.average_execution_time,
                "average_quality_score": agent.average_quality_score,
                "last_active": agent.last_active_at.isoformat() if agent.last_active_at else None
            }
            summaries.append(summary)

        # Sort by success rate descending
        summaries.sort(key=lambda x: x['success_rate'], reverse=True)
        return summaries

    async def shutdown(self) -> None:
        """Shutdown the agent registry and all agents."""
        try:
            logger.info("Shutting down agent registry...")

            # Deactivate all agents
            for agent in self._agents.values():
                try:
                    await agent.deactivate()
                except Exception as e:
                    logger.error(f"Error deactivating agent {agent.agent_id}: {e}")

            # Clear registry
            self._agents.clear()
            self._agents_by_role.clear()
            self._agent_metadata.clear()

            self._initialized = False
            logger.info("Agent registry shutdown completed")

        except Exception as e:
            logger.error(f"Error during agent registry shutdown: {e}")

    def __len__(self) -> int:
        """Return the number of registered agents."""
        return len(self._agents)

    def __contains__(self, agent_id: str) -> bool:
        """Check if an agent is registered."""
        return agent_id in self._agents

    def __iter__(self):
        """Iterate over registered agents."""
        return iter(self._agents.values())
