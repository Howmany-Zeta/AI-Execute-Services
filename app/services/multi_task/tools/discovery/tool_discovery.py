"""
Tool Discovery Module

This module is responsible for discovering available tools and operations in the system.
It provides functionality to:
- Discover all available tools and their operations
- Cache discovered tools and operations for performance
- Retrieve lists of available tools and operations
"""

import inspect
import logging
from typing import Dict, List, Any

# Import tools functions with delayed import to avoid circular dependencies
def _get_tool_functions():
    """Get tool functions with delayed import to avoid circular dependencies."""
    try:
        from app.tools import get_tool, list_tools
        return get_tool, list_tools
    except ImportError as e:
        # Fallback if there are import issues
        raise ImportError(f"Could not import tool functions: {e}")

def _get_tool(tool_name: str):
    """Get tool with delayed import."""
    get_tool, _ = _get_tool_functions()
    return get_tool(tool_name)

def _list_tools():
    """List tools with delayed import."""
    _, list_tools = _get_tool_functions()
    return list_tools()


class ToolDiscovery:
    """
    Tool discovery component responsible for finding and cataloging available tools and operations.

    This class handles the discovery of all tools in the system and their available operations,
    providing caching mechanisms for efficient access to tool information.
    """

    def __init__(self):
        """
        Initialize the tool discovery process.

        This method sets up logging, initializes caches, and triggers the discovery
        of all available tools and their operations.
        """
        # Initialize logger
        self.logger = logging.getLogger(__name__)

        # Cache for discovered tools
        self._available_tools: List[str] = []

        # Cache for discovered operations (tool_name -> list of operations)
        self._available_operations: Dict[str, List[str]] = {}

        # Cache for tool instances to avoid redundant creation
        self._tools_cache: Dict[str, Any] = {}

        # Trigger discovery process
        self._discover_all_operations()

    def _discover_all_operations(self) -> Dict[str, List[str]]:
        """
        Discover all operations (methods) for each available tool.

        This method iterates through all available tools and discovers their
        public methods that can be used as operations.

        Returns:
            Dict[str, List[str]]: A dictionary mapping tool names to lists of their operations.
        """
        # Get all available tools from the tool registry
        self._available_tools = _list_tools()

        # Clear existing operations cache
        self._available_operations = {}

        # Discover operations for each tool
        for tool_name in self._available_tools:
            try:
                tool_instance = self._get_tool_instance(tool_name)
                tool_operations = self._get_tool_operations(tool_instance)
                self._available_operations[tool_name] = tool_operations

                self.logger.debug(f"Discovered {len(tool_operations)} operations for tool '{tool_name}'")

            except Exception as e:
                self.logger.warning(f"Error discovering operations for tool '{tool_name}': {e}")
                # Set empty operations list for tools that failed to load
                self._available_operations[tool_name] = []

        self.logger.info(f"Discovery completed: {len(self._available_tools)} tools, "
                        f"{sum(len(ops) for ops in self._available_operations.values())} total operations")

        return self._available_operations

    def _get_tool_operations(self, tool: Any) -> List[str]:
        """
        Get all public operations (methods) from a single tool instance.

        This method inspects a tool instance and extracts all public methods
        that can be used as operations, excluding private methods and the 'run' method.

        Args:
            tool (Any): The tool instance to inspect.

        Returns:
            List[str]: A list of public method names that can be used as operations.
        """
        operations = []

        try:
            # Get all methods from the tool instance
            for name, method in inspect.getmembers(tool, inspect.ismethod):
                # Include only public methods, exclude private methods and 'run'
                if not name.startswith('_') and name != 'run':
                    operations.append(name)

        except Exception as e:
            self.logger.warning(f"Error extracting operations from tool: {e}")

        return operations

    def _get_tool_instance(self, tool_name: str) -> Any:
        """
        Retrieve a tool instance with caching to avoid redundant creation.

        Args:
            tool_name (str): Name of the tool to retrieve.

        Returns:
            Any: The tool instance.

        Raises:
            ValueError: If the tool does not exist or cannot be instantiated.
        """
        # Check cache first
        if tool_name not in self._tools_cache:
            try:
                # Get tool instance from the tool registry
                self._tools_cache[tool_name] = _get_tool(tool_name)
                self.logger.debug(f"Cached tool instance for '{tool_name}'")

            except ValueError as e:
                raise ValueError(f"Tool '{tool_name}' does not exist: {e}")
            except Exception as e:
                raise ValueError(f"Error instantiating tool '{tool_name}': {e}")

        return self._tools_cache[tool_name]

    def get_available_tools(self) -> List[str]:
        """
        Return a list of all discovered tools.

        Returns:
            List[str]: A list containing the names of all available tools.
        """
        return self._available_tools.copy()

    def get_available_operations(self, tool_name: str = None) -> Dict[str, List[str]] | List[str]:
        """
        Return available operations for all tools or a specific tool.

        Args:
            tool_name (str, optional): Name of a specific tool. If provided,
                                     returns only operations for that tool.
                                     If None, returns operations for all tools.

        Returns:
            Dict[str, List[str]] | List[str]: If tool_name is None, returns a dictionary
                                            mapping all tool names to their operations.
                                            If tool_name is provided, returns a list of
                                            operations for that specific tool.
        """
        if tool_name is not None:
            # Return operations for specific tool
            return self._available_operations.get(tool_name, []).copy()
        else:
            # Return all operations for all tools
            return {
                tool: operations.copy()
                for tool, operations in self._available_operations.items()
            }

    def refresh_discovery(self) -> None:
        """
        Refresh the discovery process to pick up any newly registered tools.

        This method clears all caches and re-runs the discovery process,
        useful when tools are dynamically registered after initialization.
        """
        self.logger.info("Refreshing tool discovery...")

        # Clear all caches
        self._available_tools.clear()
        self._available_operations.clear()
        self._tools_cache.clear()

        # Re-run discovery
        self._discover_all_operations()

        self.logger.info("Tool discovery refresh completed")

    def is_tool_available(self, tool_name: str) -> bool:
        """
        Check if a specific tool is available.

        Args:
            tool_name (str): Name of the tool to check.

        Returns:
            bool: True if the tool is available, False otherwise.
        """
        return tool_name in self._available_tools

    def is_operation_available(self, tool_name: str, operation_name: str) -> bool:
        """
        Check if a specific operation is available for a tool.

        Args:
            tool_name (str): Name of the tool.
            operation_name (str): Name of the operation.

        Returns:
            bool: True if the operation is available for the tool, False otherwise.
        """
        if not self.is_tool_available(tool_name):
            return False

        tool_operations = self._available_operations.get(tool_name, [])
        return operation_name in tool_operations

    def get_discovery_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the discovery process.

        Returns:
            Dict[str, Any]: Dictionary containing discovery statistics including
                          total tools, total operations, and per-tool operation counts.
        """
        total_operations = sum(len(ops) for ops in self._available_operations.values())

        return {
            "total_tools": len(self._available_tools),
            "total_operations": total_operations,
            "tools_with_operations": len([t for t, ops in self._available_operations.items() if ops]),
            "tools_without_operations": len([t for t, ops in self._available_operations.items() if not ops]),
            "per_tool_operations": {
                tool: len(operations)
                for tool, operations in self._available_operations.items()
            }
        }
