"""
Dynamic Agent Manager

Extends the existing AgentManager with dynamic agent creation capabilities
specifically for LangChain engine runtime requirements.
"""

import asyncio
import logging
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime

from langchain.agents import AgentExecutor

from .agent_manager import AgentManager
from .factory.lazy_agent_pool import LazyAgentPool
from ..core.models.agent_models import AgentConfig, AgentRole, AgentType
from ..core.exceptions.task_exceptions import TaskValidationError
from ..config.config_manager import ConfigManager
from app.services.llm_integration import LLMIntegrationManager

logger = logging.getLogger(__name__)


class DynamicAgentManager:
    """
    Dynamic Agent Manager - LangChain version.

    Extends AgentManager with dynamic creation capabilities and lazy pooling
    for runtime agent management in LangChain execution engine.
    """

    def __init__(self, agent_manager: AgentManager):
        """
        Initialize the dynamic agent manager.

        Args:
            agent_manager: Base AgentManager instance to extend
        """
        self.agent_manager = agent_manager
        self.lazy_pool = LazyAgentPool(self)

        # Dynamic agent tracking (agents created at runtime)
        self.dynamic_agents: Dict[str, str] = {}  # dynamic_id -> agent_manager_id
        self.agent_executors: Dict[str, AgentExecutor] = {}  # dynamic_id -> executor

        # Runtime statistics
        self.runtime_stats = {
            'dynamic_agents_created': 0,
            'dynamic_agents_destroyed': 0,
            'pool_hits': 0,
            'pool_misses': 0
        }

        logger.info("DynamicAgentManager initialized with AgentManager integration")

    async def create_agent_on_demand(
        self,
        role: str,
        context: Dict[str, Any],
        tools: List = None,
        agent_id: Optional[str] = None
    ) -> str:
        """
        Dynamically create an agent on demand using the underlying AgentManager.

        Args:
            role: Agent role identifier
            context: Execution context for agent creation
            tools: Optional list of tools to assign
            agent_id: Optional custom agent ID

        Returns:
            Dynamic agent ID for tracking

        Raises:
            TaskValidationError: If agent creation fails
        """
        try:
            # Generate unique dynamic ID if not provided
            if not agent_id:
                agent_id = f"dynamic_{role}_{uuid.uuid4().hex[:8]}"

            # Try to get from lazy pool first
            try:
                pooled_agent_id = await self.lazy_pool.get_or_create_agent(role, context, tools)
                if pooled_agent_id:
                    self.dynamic_agents[agent_id] = pooled_agent_id
                    self.runtime_stats['pool_hits'] += 1
                    logger.debug(f"Retrieved agent from pool: {agent_id} -> {pooled_agent_id}")
                    return agent_id
            except Exception as e:
                logger.warning(f"Pool retrieval failed, creating new agent: {e}")
                self.runtime_stats['pool_misses'] += 1

            # Create new agent using AgentManager
            base_agent = await self.agent_manager.create_agent_from_role(role)

            # Assign tools if provided
            if tools:
                await self.agent_manager.assign_tools_to_agent(base_agent.agent_id, tools)

            # Create LangChain executor
            agent_instance = await self.agent_manager.get_agent(base_agent.agent_id)
            if not agent_instance:
                raise TaskValidationError(f"Failed to retrieve created agent: {base_agent.agent_id}")

            # Get the actual BaseAgent instance from registry
            base_agent_instance = self.agent_manager.agent_registry.get_agent(base_agent.agent_id)
            if not base_agent_instance:
                raise TaskValidationError(f"Agent not found in registry: {base_agent.agent_id}")

            # Create LangChain agent executor
            langchain_executor = await base_agent_instance.create_langchain_agent(context, tools)

            # Track the dynamic agent
            self.dynamic_agents[agent_id] = base_agent.agent_id
            self.agent_executors[agent_id] = langchain_executor

            self.runtime_stats['dynamic_agents_created'] += 1

            logger.info(f"Created dynamic agent: {agent_id} -> {base_agent.agent_id} for role: {role}")
            return agent_id

        except Exception as e:
            logger.error(f"Failed to create dynamic agent for role {role}: {e}")
            raise TaskValidationError(
                message=f"Dynamic agent creation failed: {e}",
                validation_errors={"creation_error": str(e)}
            )

    async def create_multiple_agents(
        self,
        agent_specs: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Batch create multiple dynamic agents.

        Args:
            agent_specs: List of agent specifications
                        Each spec should contain: role, context, tools (optional), agent_id (optional)

        Returns:
            List of created dynamic agent IDs
        """
        agent_ids = []
        failed_creations = []

        for spec in agent_specs:
            try:
                agent_id = await self.create_agent_on_demand(
                    role=spec['role'],
                    context=spec.get('context', {}),
                    tools=spec.get('tools', []),
                    agent_id=spec.get('agent_id')
                )
                agent_ids.append(agent_id)

            except Exception as e:
                error_msg = f"Failed to create agent for spec {spec}: {e}"
                logger.error(error_msg)
                failed_creations.append(error_msg)

        if failed_creations:
            logger.warning(f"Some agent creations failed: {failed_creations}")

        logger.info(f"Successfully created {len(agent_ids)} out of {len(agent_specs)} dynamic agents")
        return agent_ids

    async def destroy_agent(self, dynamic_agent_id: str) -> bool:
        """
        Destroy a dynamic agent and clean up resources.

        Args:
            dynamic_agent_id: Dynamic agent ID to destroy

        Returns:
            True if successfully destroyed, False if agent not found
        """
        try:
            if dynamic_agent_id not in self.dynamic_agents:
                logger.warning(f"Dynamic agent not found: {dynamic_agent_id}")
                return False

            # Get the underlying agent ID
            agent_manager_id = self.dynamic_agents[dynamic_agent_id]

            # Try to return to pool first (if it came from pool)
            agent_instance = self.agent_manager.agent_registry.get_agent(agent_manager_id)
            if agent_instance:
                role = agent_instance.config.role.value
                try:
                    await self.lazy_pool.return_agent_to_pool(agent_manager_id, role)
                    logger.debug(f"Returned agent to pool: {dynamic_agent_id} -> {agent_manager_id}")
                except Exception as e:
                    logger.warning(f"Failed to return agent to pool, destroying: {e}")
                    # If pool return fails, destroy the agent
                    await self.agent_manager.delete_agent(agent_manager_id)

            # Clean up dynamic tracking
            del self.dynamic_agents[dynamic_agent_id]

            if dynamic_agent_id in self.agent_executors:
                del self.agent_executors[dynamic_agent_id]

            self.runtime_stats['dynamic_agents_destroyed'] += 1

            logger.info(f"Destroyed dynamic agent: {dynamic_agent_id}")
            return True

        except Exception as e:
            logger.error(f"Error destroying dynamic agent {dynamic_agent_id}: {e}")
            return False

    async def get_agent_executor(self, dynamic_agent_id: str) -> Optional[AgentExecutor]:
        """
        Get the LangChain agent executor for a dynamic agent.

        Args:
            dynamic_agent_id: Dynamic agent ID

        Returns:
            AgentExecutor instance or None if not found
        """
        return self.agent_executors.get(dynamic_agent_id)

    async def execute_task_with_agent(
        self,
        dynamic_agent_id: str,
        task_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a task using a specific dynamic agent.

        Args:
            dynamic_agent_id: Dynamic agent ID
            task_data: Task data and parameters
            context: Execution context

        Returns:
            Task execution result
        """
        try:
            # Get the agent executor
            agent_executor = self.agent_executors.get(dynamic_agent_id)
            if not agent_executor:
                raise TaskValidationError(
                    message=f"Agent executor not found: {dynamic_agent_id}",
                    validation_errors={"executor_not_found": dynamic_agent_id}
                )

            # Get underlying agent ID for delegation to AgentManager
            agent_manager_id = self.dynamic_agents.get(dynamic_agent_id)
            if agent_manager_id:
                # Use AgentManager's execute_agent_task method
                return await self.agent_manager.execute_agent_task(
                    agent_manager_id, task_data, context
                )
            else:
                # Fallback to direct executor execution
                task_input = task_data.get('description', task_data.get('input', ''))

                result = await agent_executor.arun(
                    input=task_input,
                    task_description=task_data.get('description', ''),
                    expected_output=task_data.get('expected_output', ''),
                    context=context
                )

                return {
                    "status": "completed",
                    "result": result,
                    "agent_id": dynamic_agent_id,
                    "task_data": task_data,
                    "context": context,
                    "execution_time": datetime.utcnow().isoformat()
                }

        except Exception as e:
            logger.error(f"Task execution failed for dynamic agent {dynamic_agent_id}: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "agent_id": dynamic_agent_id,
                "task_data": task_data,
                "execution_time": datetime.utcnow().isoformat()
            }

    async def assign_task_to_role(
        self,
        role: str,
        task_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Assign a task to any available agent with the specified role.
        Uses AgentManager's assign_task_by_role method.

        Args:
            role: Required agent role
            task_data: Task data and parameters
            context: Execution context

        Returns:
            Task execution result or None if no agent available
        """
        try:
            # First try using existing AgentManager functionality
            result = await self.agent_manager.assign_task_by_role(role, task_data, context)
            if result:
                return result

            # If no existing agent available, create one dynamically
            logger.info(f"No existing agent for role {role}, creating dynamic agent")
            dynamic_agent_id = await self.create_agent_on_demand(role, context)
            return await self.execute_task_with_agent(dynamic_agent_id, task_data, context)

        except Exception as e:
            logger.error(f"Failed to assign task to role {role}: {e}")
            return None

    async def get_manager_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics combining AgentManager and dynamic stats.

        Returns:
            Dictionary containing combined manager statistics
        """
        # Get base AgentManager statistics
        base_stats = self.agent_manager.get_manager_statistics()

        # Get lazy pool statistics
        pool_stats = await self.lazy_pool.get_pool_statistics()

        # Combine with dynamic manager statistics
        return {
            'base_manager': base_stats,
            'dynamic_manager': {
                'runtime_stats': self.runtime_stats.copy(),
                'active_dynamic_agents': len(self.dynamic_agents),
                'active_executors': len(self.agent_executors),
                'pool_efficiency': {
                    'hit_rate': (self.runtime_stats['pool_hits'] /
                               (self.runtime_stats['pool_hits'] + self.runtime_stats['pool_misses'])) * 100
                               if (self.runtime_stats['pool_hits'] + self.runtime_stats['pool_misses']) > 0 else 0
                }
            },
            'lazy_pool': pool_stats
        }

    async def cleanup_dynamic_agents(self):
        """
        Clean up all dynamic agents and resources.
        """
        logger.info("Cleaning up dynamic agents")

        # Clean up dynamic agents
        dynamic_agent_ids = list(self.dynamic_agents.keys())
        for dynamic_agent_id in dynamic_agent_ids:
            try:
                await self.destroy_agent(dynamic_agent_id)
            except Exception as e:
                logger.error(f"Error cleaning up dynamic agent {dynamic_agent_id}: {e}")

        # Clean up lazy pool
        await self.lazy_pool.force_cleanup_all()

        logger.info("Dynamic agent cleanup completed")

    def list_dynamic_agents(self) -> List[str]:
        """
        Get list of all dynamic agent IDs.

        Returns:
            List of dynamic agent IDs
        """
        return list(self.dynamic_agents.keys())

    async def get_agent_by_dynamic_id(self, dynamic_agent_id: str):
        """
        Get the underlying agent instance by dynamic ID.

        Args:
            dynamic_agent_id: Dynamic agent ID

        Returns:
            Agent instance or None if not found
        """
        agent_manager_id = self.dynamic_agents.get(dynamic_agent_id)
        if agent_manager_id:
            return await self.agent_manager.get_agent(agent_manager_id)
        return None
