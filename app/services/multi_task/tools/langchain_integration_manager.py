"""
LangChain Integration Manager

This module provides the main integration manager that coordinates all LangChain tool
integration components. It serves as the central orchestrator for tool discovery,
injection, selection, execution, and error handling.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass

from .tool_manager import ToolManager
from .langchain_adapter_tools import (
    LangChainToolAdapter,
    LangChainToolRegistry,
    LangChainToolInjector,
    create_langchain_tool_integration
)
from .langchain_tool_selector import (
    LangChainToolSelector,
    ToolExecutionContext,
    ToolExecutionResult,
    ToolSelectionStrategy
)
from .langchain_error_handler import LangChainErrorHandler
from ..core.models.agent_models import AgentConfig
from ..core.exceptions.task_exceptions import TaskValidationError

logger = logging.getLogger(__name__)


@dataclass
class IntegrationConfig:
    """Configuration for LangChain integration."""
    enable_tool_discovery: bool = True
    enable_error_handling: bool = True
    enable_circuit_breakers: bool = True
    enable_adaptive_selection: bool = True
    max_tools_per_agent: int = 10
    tool_timeout: int = 300
    retry_attempts: int = 3
    fallback_enabled: bool = True
    blacklist_threshold: int = 5
    success_rate_threshold: float = 0.7


class LangChainIntegrationManager:
    """
    Main integration manager for LangChain tool integration.

    This class coordinates all aspects of LangChain tool integration including:
    - Tool discovery and registration
    - Tool injection for agents
    - Dynamic tool selection and execution
    - Error handling and recovery
    - Performance monitoring and optimization
    """

    def __init__(
        self,
        tool_manager: ToolManager,
        config: Optional[IntegrationConfig] = None
    ):
        """
        Initialize the integration manager.

        Args:
            tool_manager: The underlying tool manager
            config: Integration configuration
        """
        self.tool_manager = tool_manager
        self.config = config or IntegrationConfig()

        # Initialize core components
        self.tool_registry, self.tool_injector = create_langchain_tool_integration(tool_manager)
        self.tool_selector = LangChainToolSelector(
            self.tool_registry, self.tool_injector, tool_manager
        )
        self.error_handler = LangChainErrorHandler()

        # State management
        self._initialized = False
        self._agent_tool_cache: Dict[str, List[LangChainToolAdapter]] = {}
        self._performance_metrics: Dict[str, Any] = {}

        logger.info("LangChain integration manager initialized")

    async def initialize(self) -> None:
        """Initialize the integration manager and all components."""
        if self._initialized:
            logger.warning("Integration manager already initialized")
            return

        try:
            logger.info("Initializing LangChain integration manager...")

            # Initialize tool discovery if enabled
            if self.config.enable_tool_discovery:
                await self._initialize_tool_discovery()

            # Initialize performance monitoring
            self._initialize_performance_monitoring()

            self._initialized = True
            logger.info("LangChain integration manager initialization completed")

        except Exception as e:
            logger.error(f"Failed to initialize integration manager: {e}")
            raise

    async def _initialize_tool_discovery(self) -> None:
        """Initialize tool discovery process."""
        try:
            logger.info("Starting tool discovery...")

            # Discover all available tools
            discovered_tools = self.tool_registry.discover_tools()

            logger.info(f"Discovered {len(discovered_tools)} LangChain tool adapters")

            # Log discovered tools for debugging
            for tool in discovered_tools:
                logger.debug(f"Discovered tool: {tool.name} ({tool.tool_name}.{tool.operation_name})")

        except Exception as e:
            logger.error(f"Tool discovery failed: {e}")
            raise

    def _initialize_performance_monitoring(self) -> None:
        """Initialize performance monitoring."""
        self._performance_metrics = {
            "total_tool_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "average_execution_time": 0.0,
            "tools_discovered": 0,
            "agents_served": 0,
            "error_recovery_attempts": 0,
            "successful_recoveries": 0
        }

    async def get_tools_for_agent(
        self,
        agent_config: AgentConfig,
        context: Dict[str, Any]
    ) -> List[LangChainToolAdapter]:
        """
        Get appropriate tools for an agent based on configuration and context.

        Args:
            agent_config: Agent configuration
            context: Runtime context

        Returns:
            List of LangChain tool adapters for the agent
        """
        try:
            # Create cache key
            agent_id = getattr(agent_config, 'agent_id', 'unknown')
            agent_key = f"{agent_config.role.value}_{agent_id}"

            # Check cache first
            if agent_key in self._agent_tool_cache:
                logger.debug(f"Using cached tools for agent {agent_key}")
                return self._agent_tool_cache[agent_key]

            # Convert agent config to dict for tool injector
            agent_config_dict = {
                'role': agent_config.role.value,
                'tools': agent_config.tools,
                'domain_specialization': agent_config.domain_specialization,
                'capabilities': agent_config.capabilities
            }

            # Get tools from injector
            tools = self.tool_injector.inject_tools_for_agent(agent_config_dict, context)

            # Apply configuration limits
            if len(tools) > self.config.max_tools_per_agent:
                tools = tools[:self.config.max_tools_per_agent]
                logger.info(f"Limited tools to {self.config.max_tools_per_agent} for agent {agent_key}")

            # Cache the result
            self._agent_tool_cache[agent_key] = tools

            # Update metrics
            self._performance_metrics["agents_served"] += 1

            logger.info(f"Provided {len(tools)} tools for agent {agent_key}")
            return tools

        except Exception as e:
            logger.error(f"Failed to get tools for agent: {e}")
            if self.config.enable_error_handling:
                # Return empty list to prevent crash
                return []
            raise

    async def execute_agent_task_with_tools(
        self,
        agent_config: AgentConfig,
        task_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute an agent task with integrated tool support.

        Args:
            agent_config: Agent configuration
            task_data: Task data
            context: Execution context

        Returns:
            Task execution result with tool integration
        """
        try:
            logger.info(f"Executing task with tool integration for agent {agent_config.role.value}")

            # Get tools for the agent
            tools = await self.get_tools_for_agent(agent_config, context)

            # Create execution context
            execution_context = ToolExecutionContext(
                task_id=task_data.get('task_id', 'unknown'),
                agent_id=getattr(agent_config, 'agent_id', 'unknown'),
                task_category=task_data.get('category', 'unknown'),
                user_input=task_data.get('description', ''),
                domain=agent_config.domain_specialization,
                timeout=self.config.tool_timeout,
                retry_count=self.config.retry_attempts,
                fallback_enabled=self.config.fallback_enabled,
                metadata=context
            )

            # Execute tools with selection and error handling
            tool_results = await self._execute_tools_with_integration(
                execution_context, tools, task_data
            )

            # Compile final result
            result = {
                "status": "completed",
                "agent_id": getattr(agent_config, 'agent_id', 'unknown'),
                "task_data": task_data,
                "tool_results": [self._serialize_tool_result(r) for r in tool_results],
                "tools_used": len([r for r in tool_results if r.success]),
                "tools_failed": len([r for r in tool_results if not r.success]),
                "context": context
            }

            # Update performance metrics
            self._update_performance_metrics(tool_results)

            logger.info(f"Task execution completed with {len(tool_results)} tool results")
            return result

        except Exception as e:
            logger.error(f"Task execution with tools failed: {e}")
            if self.config.enable_error_handling:
                return {
                    "status": "failed",
                    "error": str(e),
                    "agent_id": getattr(agent_config, 'agent_id', 'unknown'),
                    "task_data": task_data
                }
            raise

    async def _execute_tools_with_integration(
        self,
        context: ToolExecutionContext,
        tools: List[LangChainToolAdapter],
        task_data: Dict[str, Any]
    ) -> List[ToolExecutionResult]:
        """
        Execute tools with full integration support.

        Args:
            context: Execution context
            tools: Available tools
            task_data: Task data for tool requirements

        Returns:
            List of tool execution results
        """
        try:
            # Determine tool requirements from task data
            tool_requirements = self._extract_tool_requirements(task_data)

            # Use tool selector for intelligent execution
            if self.config.enable_adaptive_selection:
                results = await self.tool_selector.select_and_execute_tools(
                    context, tools, tool_requirements
                )
            else:
                # Simple execution of all tools
                results = await self._execute_all_tools(context, tools)

            return results

        except Exception as e:
            logger.error(f"Integrated tool execution failed: {e}")
            return []

    async def _execute_all_tools(
        self,
        context: ToolExecutionContext,
        tools: List[LangChainToolAdapter]
    ) -> List[ToolExecutionResult]:
        """
        Execute all tools without selection logic.

        Args:
            context: Execution context
            tools: Tools to execute

        Returns:
            List of execution results
        """
        results = []

        for tool in tools:
            try:
                # Create execution function
                async def execute_tool():
                    params = self._prepare_tool_parameters(context, tool)
                    result_text = await tool._arun(**params)

                    return ToolExecutionResult(
                        success=True,
                        result=result_text,
                        tool_name=tool.tool_name,
                        operation_name=tool.operation_name,
                        execution_time=0.1  # Placeholder
                    )

                # Execute with error handling if enabled
                if self.config.enable_error_handling:
                    result = await self.error_handler.handle_tool_execution(
                        tool, context, execute_tool
                    )
                else:
                    result = await execute_tool()

                results.append(result)

            except Exception as e:
                logger.error(f"Tool execution failed: {tool.name} - {e}")
                error_result = ToolExecutionResult(
                    success=False,
                    result=None,
                    tool_name=tool.tool_name,
                    operation_name=tool.operation_name,
                    execution_time=0.0,
                    error_message=str(e)
                )
                results.append(error_result)

        return results

    def _extract_tool_requirements(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract tool requirements from task data.

        Args:
            task_data: Task data

        Returns:
            Tool requirements dictionary
        """
        requirements = {}

        # Check for explicit tool specifications
        if 'tools' in task_data:
            requirements['explicit_tools'] = task_data['tools']

        # Check for tool categories
        if 'category' in task_data:
            requirements['category'] = task_data['category']

        # Check for domain requirements
        if 'domain' in task_data:
            requirements['domain'] = task_data['domain']

        return requirements

    def _prepare_tool_parameters(
        self,
        context: ToolExecutionContext,
        tool: LangChainToolAdapter
    ) -> Dict[str, Any]:
        """
        Prepare parameters for tool execution.

        Args:
            context: Execution context
            tool: Tool to prepare parameters for

        Returns:
            Tool parameters
        """
        # Basic parameters
        params = {
            'input': context.user_input
        }

        # Add tool-specific parameters
        if tool.operation_name == 'summarize':
            params['text'] = context.user_input
        elif tool.operation_name == 'keyword_extract':
            params['text'] = context.user_input

        return params

    def _serialize_tool_result(self, result: ToolExecutionResult) -> Dict[str, Any]:
        """
        Serialize tool execution result for JSON compatibility.

        Args:
            result: Tool execution result

        Returns:
            Serialized result dictionary
        """
        return {
            "success": result.success,
            "tool_name": result.tool_name,
            "operation_name": result.operation_name,
            "execution_time": result.execution_time,
            "result": str(result.result) if result.result is not None else None,
            "error_message": result.error_message,
            "fallback_used": result.fallback_used,
            "retry_count": result.retry_count,
            "metadata": result.metadata or {}
        }

    def _update_performance_metrics(self, results: List[ToolExecutionResult]) -> None:
        """
        Update performance metrics based on execution results.

        Args:
            results: List of execution results
        """
        try:
            total_executions = len(results)
            successful_executions = len([r for r in results if r.success])
            failed_executions = total_executions - successful_executions

            # Update counters
            self._performance_metrics["total_tool_executions"] += total_executions
            self._performance_metrics["successful_executions"] += successful_executions
            self._performance_metrics["failed_executions"] += failed_executions

            # Update average execution time
            if results:
                avg_time = sum(r.execution_time for r in results) / len(results)
                current_avg = self._performance_metrics["average_execution_time"]
                total_count = self._performance_metrics["total_tool_executions"]

                # Weighted average
                new_avg = ((current_avg * (total_count - total_executions)) + (avg_time * total_executions)) / total_count
                self._performance_metrics["average_execution_time"] = new_avg

        except Exception as e:
            logger.error(f"Failed to update performance metrics: {e}")

    async def refresh_tool_discovery(self) -> None:
        """Refresh tool discovery and clear caches."""
        try:
            logger.info("Refreshing tool discovery...")

            # Clear caches
            self._agent_tool_cache.clear()
            self.tool_injector.clear_cache()

            # Refresh tool registry
            self.tool_registry.refresh_tools()

            # Re-discover tools
            if self.config.enable_tool_discovery:
                await self._initialize_tool_discovery()

            logger.info("Tool discovery refresh completed")

        except Exception as e:
            logger.error(f"Tool discovery refresh failed: {e}")
            raise

    def get_integration_status(self) -> Dict[str, Any]:
        """
        Get comprehensive integration status and metrics.

        Returns:
            Integration status dictionary
        """
        try:
            # Get component statistics
            tool_registry_stats = self.tool_registry.get_registry_stats()
            tool_selector_metrics = self.tool_selector.get_tool_metrics()
            error_handler_stats = self.error_handler.get_error_statistics()

            return {
                "initialized": self._initialized,
                "configuration": {
                    "tool_discovery_enabled": self.config.enable_tool_discovery,
                    "error_handling_enabled": self.config.enable_error_handling,
                    "adaptive_selection_enabled": self.config.enable_adaptive_selection,
                    "max_tools_per_agent": self.config.max_tools_per_agent,
                    "tool_timeout": self.config.tool_timeout
                },
                "performance_metrics": self._performance_metrics.copy(),
                "tool_registry": tool_registry_stats,
                "tool_selector": tool_selector_metrics,
                "error_handler": error_handler_stats,
                "cached_agents": len(self._agent_tool_cache),
                "system_health": self._assess_system_health()
            }

        except Exception as e:
            logger.error(f"Failed to get integration status: {e}")
            return {
                "initialized": self._initialized,
                "error": str(e),
                "system_health": "unhealthy"
            }

    def _assess_system_health(self) -> str:
        """
        Assess overall system health.

        Returns:
            Health status string
        """
        try:
            # Check success rate
            total_executions = self._performance_metrics["total_tool_executions"]
            if total_executions > 0:
                success_rate = self._performance_metrics["successful_executions"] / total_executions
                if success_rate < 0.5:
                    return "unhealthy"
                elif success_rate < 0.8:
                    return "degraded"

            # Check error handler state
            error_stats = self.error_handler.get_error_statistics()
            if len(error_stats.get("blacklisted_tools", [])) > 5:
                return "degraded"

            return "healthy"

        except Exception as e:
            logger.error(f"Health assessment failed: {e}")
            return "unknown"

    async def cleanup(self) -> None:
        """Clean up resources and shutdown integration."""
        try:
            logger.info("Cleaning up LangChain integration manager...")

            # Clear caches
            self._agent_tool_cache.clear()
            self.tool_injector.clear_cache()

            # Reset error states
            self.error_handler.reset_error_state()

            # Reset metrics
            self._performance_metrics.clear()

            self._initialized = False
            logger.info("LangChain integration manager cleanup completed")

        except Exception as e:
            logger.error(f"Cleanup failed: {e}")

    def is_initialized(self) -> bool:
        """Check if the integration manager is initialized."""
        return self._initialized

    def get_available_tools_count(self) -> int:
        """Get the number of available tools."""
        try:
            tools = self.tool_registry.discover_tools()
            return len(tools)
        except Exception as e:
            logger.error(f"Failed to get tools count: {e}")
            return 0

    def get_agent_tools_count(self, agent_id: str) -> int:
        """Get the number of tools assigned to a specific agent."""
        agent_tools = [tools for key, tools in self._agent_tool_cache.items() if agent_id in key]
        return len(agent_tools[0]) if agent_tools else 0


# Factory function for easy integration setup
async def create_langchain_integration(
    tool_manager: ToolManager,
    config: Optional[IntegrationConfig] = None
) -> LangChainIntegrationManager:
    """
    Factory function to create and initialize LangChain integration.

    Args:
        tool_manager: The tool manager instance
        config: Optional integration configuration

    Returns:
        Initialized integration manager
    """
    try:
        integration_manager = LangChainIntegrationManager(tool_manager, config)
        await integration_manager.initialize()

        logger.info("LangChain integration created and initialized successfully")
        return integration_manager

    except Exception as e:
        logger.error(f"Failed to create LangChain integration: {e}")
        raise
