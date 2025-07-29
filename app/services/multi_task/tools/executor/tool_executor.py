"""
Tool Executor Module

This module is responsible for executing specified operations on tools.
It receives instructions and runs the actual code, handling both synchronous and asynchronous execution.
"""

import asyncio
import logging
from typing import Any, Dict, Optional

# Import tools functions with delayed import to avoid circular dependencies
def _get_tool(tool_name: str):
    """Get tool with delayed import to avoid circular dependencies."""
    try:
        from app.tools import get_tool
        return get_tool(tool_name)
    except ImportError as e:
        raise ImportError(f"Could not import tool function: {e}")
from ..discovery.tool_discovery import ToolDiscovery


class ToolExecutor:
    """
    Tool executor component responsible for executing operations on tools.

    This class handles the actual execution of tool operations, supporting both
    synchronous and asynchronous execution modes with comprehensive error handling.
    """

    def __init__(self, tool_discovery: Optional[ToolDiscovery] = None):
        """
        Initialize the tool executor.

        Args:
            tool_discovery (Optional[ToolDiscovery]): Tool discovery instance to use.
                                                    If None, creates a new instance.
        """
        # Initialize logger
        self.logger = logging.getLogger(__name__)

        # Tool discovery instance for checking tool/operation availability
        self.tool_discovery = tool_discovery or ToolDiscovery()

        # Cache for tool instances to avoid redundant creation
        self._tools_cache: Dict[str, Any] = {}

        # Execution statistics
        self._execution_stats = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "async_executions": 0,
            "sync_executions": 0
        }

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

    async def execute_tool(self, tool_name: str, operation_name: str, **params) -> Any:
        """
        Execute a tool operation with the given parameters (supports async operations).

        This is the core execution method that handles both synchronous and asynchronous
        operations, automatically detecting the operation type and executing accordingly.

        Args:
            tool_name (str): Name of the tool to execute.
            operation_name (str): Name of the operation to execute.
            **params: Parameters to pass to the operation.

        Returns:
            Any: The result of the tool operation.

        Raises:
            ValueError: If the tool or operation does not exist, or if execution fails.
        """
        # Update execution statistics
        self._execution_stats["total_executions"] += 1

        try:
            # Validate tool exists
            if not self.tool_discovery.is_tool_available(tool_name):
                raise ValueError(f"Tool '{tool_name}' does not exist")

            # Validate operation exists
            if not self.tool_discovery.is_operation_available(tool_name, operation_name):
                raise ValueError(f"Operation '{operation_name}' not found in tool '{tool_name}'")

            # Get tool instance
            tool = self._get_tool_instance(tool_name)

            # Get the operation method from the tool instance
            operation = getattr(tool, operation_name)

            # Log execution attempt
            self.logger.info(f"Executing {tool_name}.{operation_name} with params: {list(params.keys())}")

            # Execute the operation based on its type (async or sync)
            if asyncio.iscoroutinefunction(operation):
                # Asynchronous execution
                self._execution_stats["async_executions"] += 1
                self.logger.debug(f"Executing async operation {tool_name}.{operation_name}")
                result = await operation(**params)
            else:
                # Synchronous execution
                self._execution_stats["sync_executions"] += 1
                self.logger.debug(f"Executing sync operation {tool_name}.{operation_name}")
                result = operation(**params)

            # Update success statistics
            self._execution_stats["successful_executions"] += 1

            self.logger.info(f"Successfully executed {tool_name}.{operation_name}")
            return result

        except Exception as e:
            # Update failure statistics
            self._execution_stats["failed_executions"] += 1

            # Log the error with context
            error_msg = f"Error executing {tool_name}.{operation_name}: {e}"
            self.logger.error(error_msg, exc_info=True)

            # Re-raise as ValueError with context
            raise ValueError(error_msg) from e

    def execute_tool_sync(self, tool_name: str, operation_name: str, **params) -> Any:
        """
        Synchronously execute a tool operation.

        This method is specifically for synchronous execution and will raise an error
        if the operation is asynchronous. Use this when you need to ensure synchronous execution.

        Args:
            tool_name (str): Name of the tool to execute.
            operation_name (str): Name of the operation to execute.
            **params: Parameters to pass to the operation.

        Returns:
            Any: The result of the tool operation.

        Raises:
            ValueError: If the tool/operation does not exist, is async, or execution fails.
        """
        # Update execution statistics
        self._execution_stats["total_executions"] += 1
        self._execution_stats["sync_executions"] += 1

        try:
            # Validate tool exists
            if not self.tool_discovery.is_tool_available(tool_name):
                raise ValueError(f"Tool '{tool_name}' does not exist")

            # Validate operation exists
            if not self.tool_discovery.is_operation_available(tool_name, operation_name):
                raise ValueError(f"Operation '{operation_name}' not found in tool '{tool_name}'")

            # Get tool instance
            tool = self._get_tool_instance(tool_name)

            # Get the operation method from the tool instance
            operation = getattr(tool, operation_name)

            # Check if operation is synchronous
            if asyncio.iscoroutinefunction(operation):
                raise ValueError(f"Cannot execute async operation '{operation_name}' synchronously. Use execute_tool() instead.")

            # Log execution attempt
            self.logger.info(f"Executing sync {tool_name}.{operation_name} with params: {list(params.keys())}")

            # Execute the synchronous operation
            result = operation(**params)

            # Update success statistics
            self._execution_stats["successful_executions"] += 1

            self.logger.info(f"Successfully executed sync {tool_name}.{operation_name}")
            return result

        except Exception as e:
            # Update failure statistics
            self._execution_stats["failed_executions"] += 1

            # Log the error with context
            error_msg = f"Error executing sync {tool_name}.{operation_name}: {e}"
            self.logger.error(error_msg, exc_info=True)

            # Re-raise as ValueError with context
            raise ValueError(error_msg) from e

    def execute_operation_spec(self, operation_spec: str, **params) -> Any:
        """
        Execute an operation using the 'tool_name.operation_name' specification format.

        Args:
            operation_spec (str): The operation specification in format 'tool_name.operation_name'.
            **params: Parameters to pass to the operation.

        Returns:
            Any: The result of the tool operation.

        Raises:
            ValueError: If the operation specification is invalid or execution fails.
        """
        # Validate operation specification format
        if "." not in operation_spec:
            raise ValueError(f"Invalid operation specification: {operation_spec}, expected 'tool_name.operation_name' format")

        # Parse tool and operation names
        tool_name, operation_name = operation_spec.split(".", 1)

        # Execute using the standard method
        return self.execute_tool_sync(tool_name, operation_name, **params)

    async def execute_operation_spec_async(self, operation_spec: str, **params) -> Any:
        """
        Asynchronously execute an operation using the 'tool_name.operation_name' specification format.

        Args:
            operation_spec (str): The operation specification in format 'tool_name.operation_name'.
            **params: Parameters to pass to the operation.

        Returns:
            Any: The result of the tool operation.

        Raises:
            ValueError: If the operation specification is invalid or execution fails.
        """
        # Validate operation specification format
        if "." not in operation_spec:
            raise ValueError(f"Invalid operation specification: {operation_spec}, expected 'tool_name.operation_name' format")

        # Parse tool and operation names
        tool_name, operation_name = operation_spec.split(".", 1)

        # Execute using the async method
        return await self.execute_tool(tool_name, operation_name, **params)

    def execute_batch_sync(self, operations: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
        """
        Execute multiple operations synchronously in batch.

        Args:
            operations (list[Dict[str, Any]]): List of operation dictionaries, each containing:
                                             - tool_name: str
                                             - operation_name: str
                                             - params: Dict[str, Any] (optional)

        Returns:
            list[Dict[str, Any]]: List of results, each containing:
                                - success: bool
                                - result: Any (if successful)
                                - error: str (if failed)
                                - tool_name: str
                                - operation_name: str
        """
        results = []

        for i, op in enumerate(operations):
            try:
                # Extract operation details
                tool_name = op.get("tool_name")
                operation_name = op.get("operation_name")
                params = op.get("params", {})

                if not tool_name or not operation_name:
                    raise ValueError("Missing tool_name or operation_name")

                # Execute operation
                result = self.execute_tool_sync(tool_name, operation_name, **params)

                results.append({
                    "success": True,
                    "result": result,
                    "tool_name": tool_name,
                    "operation_name": operation_name,
                    "index": i
                })

            except Exception as e:
                results.append({
                    "success": False,
                    "error": str(e),
                    "tool_name": op.get("tool_name", "unknown"),
                    "operation_name": op.get("operation_name", "unknown"),
                    "index": i
                })

        return results

    async def execute_batch_async(self, operations: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
        """
        Execute multiple operations asynchronously in batch.

        Args:
            operations (list[Dict[str, Any]]): List of operation dictionaries, each containing:
                                             - tool_name: str
                                             - operation_name: str
                                             - params: Dict[str, Any] (optional)

        Returns:
            list[Dict[str, Any]]: List of results, each containing:
                                - success: bool
                                - result: Any (if successful)
                                - error: str (if failed)
                                - tool_name: str
                                - operation_name: str
        """
        async def execute_single(op: Dict[str, Any], index: int) -> Dict[str, Any]:
            try:
                # Extract operation details
                tool_name = op.get("tool_name")
                operation_name = op.get("operation_name")
                params = op.get("params", {})

                if not tool_name or not operation_name:
                    raise ValueError("Missing tool_name or operation_name")

                # Execute operation
                result = await self.execute_tool(tool_name, operation_name, **params)

                return {
                    "success": True,
                    "result": result,
                    "tool_name": tool_name,
                    "operation_name": operation_name,
                    "index": index
                }

            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "tool_name": op.get("tool_name", "unknown"),
                    "operation_name": op.get("operation_name", "unknown"),
                    "index": index
                }

        # Execute all operations concurrently
        tasks = [execute_single(op, i) for i, op in enumerate(operations)]
        results = await asyncio.gather(*tasks, return_exceptions=False)

        return results

    def get_execution_stats(self) -> Dict[str, Any]:
        """
        Get execution statistics.

        Returns:
            Dict[str, Any]: Dictionary containing execution statistics.
        """
        stats = self._execution_stats.copy()

        # Calculate success rate
        if stats["total_executions"] > 0:
            stats["success_rate"] = stats["successful_executions"] / stats["total_executions"]
            stats["failure_rate"] = stats["failed_executions"] / stats["total_executions"]
        else:
            stats["success_rate"] = 0.0
            stats["failure_rate"] = 0.0

        return stats

    def reset_stats(self) -> None:
        """
        Reset execution statistics.
        """
        self.logger.info("Resetting execution statistics")

        self._execution_stats = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "async_executions": 0,
            "sync_executions": 0
        }

    def clear_cache(self) -> None:
        """
        Clear cached tool instances to force fresh instantiation on next access.
        """
        self.logger.info("Clearing tool executor cache...")
        self._tools_cache.clear()
        self.logger.info("Tool executor cache cleared")

    def get_cache_stats(self) -> Dict[str, int]:
        """
        Get statistics about cached tool instances.

        Returns:
            Dict[str, int]: Dictionary containing cache statistics.
        """
        return {
            "cached_tools": len(self._tools_cache)
        }
