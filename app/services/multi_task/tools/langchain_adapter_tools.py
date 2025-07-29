"""
LangChain Tools Adapter

This module provides integration between the multi-task tools system and LangChain agents.
It allows LangChain agents to dynamically discover, validate, and execute tools from the
main program's tool registry.

Key Features:
- Dynamic tool discovery and injection
- Tool validation and error handling
- Seamless integration with existing tool architecture
- Fallback mechanisms to prevent crashes
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Union, Type
from langchain.tools import BaseTool
from langchain.schema import BaseMessage
from pydantic import Field, BaseModel

from .tool_manager import ToolManager
from ..core.exceptions.task_exceptions import TaskValidationError, TaskExecutionError

logger = logging.getLogger(__name__)


class LangChainToolAdapter(BaseTool):
    """
    Adapter that wraps multi-task tools for use with LangChain agents.

    This adapter bridges the gap between our tool system and LangChain's tool interface,
    allowing agents to seamlessly use tools from the main program.
    """

    name: str = Field(...)
    description: str = Field(...)
    tool_manager: ToolManager = Field(...)
    tool_name: str = Field(...)
    operation_name: str = Field(...)
    return_direct: bool = Field(default=False)

    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True

    def __init__(
        self,
        tool_manager: ToolManager,
        tool_name: str,
        operation_name: str,
        **kwargs
    ):
        """
        Initialize the LangChain tool adapter.

        Args:
            tool_manager: The tool manager instance
            tool_name: Name of the tool to wrap
            operation_name: Name of the operation to execute
            **kwargs: Additional tool configuration
        """
        # Get operation info for description
        try:
            operation_spec = f"{tool_name}.{operation_name}"
            operation_info = tool_manager.get_operation_info(operation_spec)

            name = f"{tool_name}_{operation_name}"
            description = operation_info.get('description', f"Execute {operation_name} on {tool_name}")

        except Exception as e:
            logger.warning(f"Failed to get operation info for {tool_name}.{operation_name}: {e}")
            name = f"{tool_name}_{operation_name}"
            description = f"Execute {operation_name} on {tool_name}"

        super().__init__(
            name=name,
            description=description,
            tool_manager=tool_manager,
            tool_name=tool_name,
            operation_name=operation_name,
            **kwargs
        )

    def _run(self, **kwargs) -> str:
        """
        Execute the tool operation synchronously.

        Args:
            **kwargs: Parameters to pass to the tool operation

        Returns:
            String representation of the tool execution result
        """
        try:
            # Validate parameters first
            validation_errors = self.tool_manager.validate_operation_params(
                self.tool_name, self.operation_name, kwargs
            )

            if validation_errors:
                error_msg = f"Parameter validation failed: {'; '.join(validation_errors)}"
                logger.error(error_msg)
                return f"Error: {error_msg}"

            # Execute the tool operation
            result = self.tool_manager.execute_tool_sync(
                self.tool_name, self.operation_name, **kwargs
            )

            # Convert result to string for LangChain
            return self._format_result(result)

        except Exception as e:
            error_msg = f"Tool execution failed: {str(e)}"
            logger.error(f"Error executing {self.tool_name}.{self.operation_name}: {e}")
            return f"Error: {error_msg}"

    async def _arun(self, **kwargs) -> str:
        """
        Execute the tool operation asynchronously.

        Args:
            **kwargs: Parameters to pass to the tool operation

        Returns:
            String representation of the tool execution result
        """
        try:
            # Validate parameters first
            validation_errors = self.tool_manager.validate_operation_params(
                self.tool_name, self.operation_name, kwargs
            )

            if validation_errors:
                error_msg = f"Parameter validation failed: {'; '.join(validation_errors)}"
                logger.error(error_msg)
                return f"Error: {error_msg}"

            # Execute the tool operation asynchronously
            result = await self.tool_manager.execute_tool(
                self.tool_name, self.operation_name, **kwargs
            )

            # Convert result to string for LangChain
            return self._format_result(result)

        except Exception as e:
            error_msg = f"Tool execution failed: {str(e)}"
            logger.error(f"Error executing {self.tool_name}.{self.operation_name}: {e}")
            return f"Error: {error_msg}"

    def _format_result(self, result: Any) -> str:
        """
        Format the tool execution result for LangChain consumption.

        Args:
            result: Raw result from tool execution

        Returns:
            Formatted string representation
        """
        if result is None:
            return "Operation completed successfully (no return value)"

        if isinstance(result, str):
            return result

        if isinstance(result, (dict, list)):
            import json
            try:
                return json.dumps(result, indent=2, ensure_ascii=False)
            except (TypeError, ValueError):
                return str(result)

        return str(result)


class LangChainToolRegistry:
    """
    Registry for managing LangChain tool adapters.

    This class handles the discovery, creation, and management of LangChain-compatible
    tools from the multi-task tool system.
    """

    def __init__(self, tool_manager: ToolManager):
        """
        Initialize the tool registry.

        Args:
            tool_manager: The tool manager instance
        """
        self.tool_manager = tool_manager
        self._tool_cache: Dict[str, LangChainToolAdapter] = {}
        self._discovery_cache: Dict[str, List[str]] = {}

        logger.info("LangChain tool registry initialized")

    def discover_tools(self, tool_filter: Optional[List[str]] = None) -> List[LangChainToolAdapter]:
        """
        Discover and create LangChain tool adapters for available tools.

        Args:
            tool_filter: Optional list of tool names to filter by

        Returns:
            List of LangChain tool adapters
        """
        try:
            # Get available tools
            available_tools = self.tool_manager.get_available_tools()

            if tool_filter:
                available_tools = [tool for tool in available_tools if tool in tool_filter]

            langchain_tools = []

            for tool_name in available_tools:
                try:
                    # Get operations for this tool
                    operations = self.tool_manager.get_available_operations(tool_name)

                    for operation_name in operations:
                        # Create LangChain tool adapter
                        adapter = self._create_tool_adapter(tool_name, operation_name)
                        if adapter:
                            langchain_tools.append(adapter)

                except Exception as e:
                    logger.warning(f"Failed to create adapters for tool {tool_name}: {e}")
                    continue

            logger.info(f"Discovered {len(langchain_tools)} LangChain tool adapters")
            return langchain_tools

        except Exception as e:
            logger.error(f"Tool discovery failed: {e}")
            return []

    def get_tools_for_agent(self, agent_config: Dict[str, Any]) -> List[LangChainToolAdapter]:
        """
        Get tools specifically configured for an agent.

        Args:
            agent_config: Agent configuration containing tool specifications

        Returns:
            List of LangChain tool adapters for the agent
        """
        try:
            agent_tools = []
            tool_specs = agent_config.get('tools', [])

            if not tool_specs:
                logger.debug("No tools specified for agent")
                return []

            for tool_spec in tool_specs:
                if isinstance(tool_spec, str):
                    # Simple tool name - get all operations
                    tool_name = tool_spec
                    operations = self.tool_manager.get_available_operations(tool_name)

                    for operation_name in operations:
                        adapter = self._create_tool_adapter(tool_name, operation_name)
                        if adapter:
                            agent_tools.append(adapter)

                elif isinstance(tool_spec, dict):
                    # Tool with specific operations
                    tool_name = tool_spec.get('name')
                    operations = tool_spec.get('operations', [])

                    if not tool_name:
                        continue

                    if not operations:
                        # Get all operations if none specified
                        operations = self.tool_manager.get_available_operations(tool_name)

                    for operation_name in operations:
                        adapter = self._create_tool_adapter(tool_name, operation_name)
                        if adapter:
                            agent_tools.append(adapter)

            logger.info(f"Created {len(agent_tools)} tools for agent")
            return agent_tools

        except Exception as e:
            logger.error(f"Failed to get tools for agent: {e}")
            return []

    def get_tools_by_category(self, category: str) -> List[LangChainToolAdapter]:
        """
        Get tools filtered by category (e.g., 'collect', 'process', 'analyze').

        Args:
            category: Tool category to filter by

        Returns:
            List of LangChain tool adapters in the category
        """
        try:
            # This would need to be enhanced based on tool categorization
            # For now, return all tools
            return self.discover_tools()

        except Exception as e:
            logger.error(f"Failed to get tools by category {category}: {e}")
            return []

    def _create_tool_adapter(self, tool_name: str, operation_name: str) -> Optional[LangChainToolAdapter]:
        """
        Create a LangChain tool adapter for a specific tool operation.

        Args:
            tool_name: Name of the tool
            operation_name: Name of the operation

        Returns:
            LangChain tool adapter or None if creation fails
        """
        try:
            # Check if tool and operation are available
            if not self.tool_manager.is_tool_available(tool_name):
                logger.warning(f"Tool not available: {tool_name}")
                return None

            if not self.tool_manager.is_operation_available(tool_name, operation_name):
                logger.warning(f"Operation not available: {tool_name}.{operation_name}")
                return None

            # Create cache key
            cache_key = f"{tool_name}.{operation_name}"

            # Check cache first
            if cache_key in self._tool_cache:
                return self._tool_cache[cache_key]

            # Create new adapter
            adapter = LangChainToolAdapter(
                tool_manager=self.tool_manager,
                tool_name=tool_name,
                operation_name=operation_name
            )

            # Cache the adapter
            self._tool_cache[cache_key] = adapter

            logger.debug(f"Created tool adapter: {cache_key}")
            return adapter

        except Exception as e:
            logger.error(f"Failed to create tool adapter for {tool_name}.{operation_name}: {e}")
            return None

    def refresh_tools(self) -> None:
        """
        Refresh the tool registry by clearing caches and rediscovering tools.
        """
        try:
            logger.info("Refreshing LangChain tool registry...")

            # Clear caches
            self._tool_cache.clear()
            self._discovery_cache.clear()

            # Refresh underlying tool manager
            self.tool_manager.refresh_discovery()

            logger.info("LangChain tool registry refreshed")

        except Exception as e:
            logger.error(f"Failed to refresh tool registry: {e}")

    def get_tool_info(self, tool_name: str, operation_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific tool operation.

        Args:
            tool_name: Name of the tool
            operation_name: Name of the operation

        Returns:
            Dictionary containing tool information
        """
        try:
            operation_spec = f"{tool_name}.{operation_name}"
            return self.tool_manager.get_operation_info(operation_spec)

        except Exception as e:
            logger.error(f"Failed to get tool info for {tool_name}.{operation_name}: {e}")
            return {}

    def validate_tool_usage(self, tool_name: str, operation_name: str, params: Dict[str, Any]) -> List[str]:
        """
        Validate tool usage parameters.

        Args:
            tool_name: Name of the tool
            operation_name: Name of the operation
            params: Parameters to validate

        Returns:
            List of validation error messages
        """
        try:
            return self.tool_manager.validate_operation_params(tool_name, operation_name, params)

        except Exception as e:
            logger.error(f"Failed to validate tool usage: {e}")
            return [f"Validation error: {str(e)}"]

    def get_registry_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the tool registry.

        Returns:
            Dictionary containing registry statistics
        """
        try:
            tool_manager_stats = self.tool_manager.get_system_stats()

            return {
                "cached_adapters": len(self._tool_cache),
                "discovery_cache_size": len(self._discovery_cache),
                "tool_manager_stats": tool_manager_stats,
                "registry_status": "active"
            }

        except Exception as e:
            logger.error(f"Failed to get registry stats: {e}")
            return {"registry_status": "error", "error": str(e)}


class LangChainToolInjector:
    """
    Tool injector for LangChain agents.

    This class handles the injection of tools into LangChain agents based on
    configuration and runtime context.
    """

    def __init__(self, tool_registry: LangChainToolRegistry):
        """
        Initialize the tool injector.

        Args:
            tool_registry: The tool registry instance
        """
        self.tool_registry = tool_registry
        self._injection_cache: Dict[str, List[LangChainToolAdapter]] = {}

        logger.info("LangChain tool injector initialized")

    def inject_tools_for_agent(
        self,
        agent_config: Dict[str, Any],
        context: Dict[str, Any]
    ) -> List[LangChainToolAdapter]:
        """
        Inject appropriate tools for an agent based on configuration and context.

        Args:
            agent_config: Agent configuration
            context: Runtime context

        Returns:
            List of injected LangChain tool adapters
        """
        try:
            # Create cache key
            agent_role = agent_config.get('role', 'unknown')
            cache_key = f"{agent_role}_{hash(str(sorted(agent_config.get('tools', []))))}"

            # Check cache first
            if cache_key in self._injection_cache:
                logger.debug(f"Using cached tools for agent {agent_role}")
                return self._injection_cache[cache_key]

            # Get tools based on agent configuration
            tools = self.tool_registry.get_tools_for_agent(agent_config)

            # Apply context-based filtering if needed
            filtered_tools = self._filter_tools_by_context(tools, context)

            # Cache the result
            self._injection_cache[cache_key] = filtered_tools

            logger.info(f"Injected {len(filtered_tools)} tools for agent {agent_role}")
            return filtered_tools

        except Exception as e:
            logger.error(f"Tool injection failed: {e}")
            return []

    def inject_tools_by_task_category(
        self,
        task_category: str,
        context: Dict[str, Any]
    ) -> List[LangChainToolAdapter]:
        """
        Inject tools based on task category.

        Args:
            task_category: Task category (e.g., 'collect', 'process', 'analyze')
            context: Runtime context

        Returns:
            List of injected LangChain tool adapters
        """
        try:
            # Get tools by category
            tools = self.tool_registry.get_tools_by_category(task_category)

            # Apply context-based filtering
            filtered_tools = self._filter_tools_by_context(tools, context)

            logger.info(f"Injected {len(filtered_tools)} tools for task category {task_category}")
            return filtered_tools

        except Exception as e:
            logger.error(f"Tool injection by category failed: {e}")
            return []

    def _filter_tools_by_context(
        self,
        tools: List[LangChainToolAdapter],
        context: Dict[str, Any]
    ) -> List[LangChainToolAdapter]:
        """
        Filter tools based on runtime context.

        Args:
            tools: List of tools to filter
            context: Runtime context

        Returns:
            Filtered list of tools
        """
        try:
            # For now, return all tools
            # This can be enhanced with context-based filtering logic
            return tools

        except Exception as e:
            logger.error(f"Tool filtering failed: {e}")
            return tools

    def clear_cache(self) -> None:
        """Clear the injection cache."""
        self._injection_cache.clear()
        logger.debug("Tool injection cache cleared")


# Factory function for easy integration
def create_langchain_tool_integration(tool_manager: ToolManager) -> tuple[LangChainToolRegistry, LangChainToolInjector]:
    """
    Factory function to create LangChain tool integration components.

    Args:
        tool_manager: The tool manager instance

    Returns:
        Tuple of (tool_registry, tool_injector)
    """
    try:
        tool_registry = LangChainToolRegistry(tool_manager)
        tool_injector = LangChainToolInjector(tool_registry)

        logger.info("LangChain tool integration created successfully")
        return tool_registry, tool_injector

    except Exception as e:
        logger.error(f"Failed to create LangChain tool integration: {e}")
        raise
