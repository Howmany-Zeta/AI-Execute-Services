"""
Tool Manager Module

This module serves as the main coordinator for all tool components, providing a unified interface
for tool discovery, inspection, and execution. It acts as the central hub that brings together
all the separated tool functionality.
"""

import logging
from typing import Dict, List, Any, Optional, Union, Callable
from datetime import datetime
import uuid

from .discovery.tool_discovery import ToolDiscovery
from .inspector.tool_inspector import ToolInspector
from .executor.tool_executor import ToolExecutor
from ..core.interfaces.tool_manager import IToolManager
from ..core.models.execution_models import ToolConfig, ToolResult, ToolType


class ToolManager(IToolManager):
    """
    Tool manager that coordinates all tool-related functionality.

    This class serves as the main interface for tool operations, providing a unified API
    that combines discovery, inspection, and execution capabilities. It implements the
    IToolManager interface while maintaining compatibility with existing functionality.
    """

    def __init__(self):
        """
        Initialize the tool manager with all component instances.

        Creates instances of ToolDiscovery, ToolInspector, and ToolExecutor,
        ensuring they work together cohesively.
        """
        # Initialize logger
        self.logger = logging.getLogger(__name__)

        # Initialize core components
        self.discovery = ToolDiscovery()
        self.inspector = ToolInspector(tool_discovery=self.discovery)
        self.executor = ToolExecutor(tool_discovery=self.discovery)

        # Tool registry for interface compliance
        self._tool_registry: Dict[str, ToolConfig] = {}
        self._tool_adapters: Dict[str, Callable] = {}
        self._tool_metrics: Dict[str, Dict[str, Any]] = {}
        self._initialized = False

        self.logger.info("ToolManager initialized with all components")

    # ===== INTERFACE IMPLEMENTATION =====

    async def initialize(self) -> None:
        """
        Initialize the tool manager.

        Sets up tool registry, loads available tools, and prepares
        the manager for tool operations.
        """
        if self._initialized:
            return

        try:
            # Refresh discovery to load available tools
            self.refresh_discovery()

            # Initialize tool registry with discovered tools
            await self._populate_tool_registry()

            self._initialized = True
            self.logger.info("ToolManager initialization completed")

        except Exception as e:
            self.logger.error(f"Failed to initialize ToolManager: {e}")
            raise

    async def _populate_tool_registry(self) -> None:
        """Populate tool registry with discovered tools."""
        available_tools = self.get_available_tools()

        for tool_name in available_tools:
            try:
                # Create a basic ToolConfig for discovered tools
                operations = self.get_available_operations(tool_name)
                if isinstance(operations, list):
                    operations_dict = {op: {} for op in operations}
                else:
                    operations_dict = operations

                tool_config = ToolConfig(
                    name=tool_name,
                    tool_type=ToolType.CUSTOM,  # Default type for discovered tools
                    description=f"Auto-discovered tool: {tool_name}",
                    operations=operations_dict
                )

                self._tool_registry[tool_name] = tool_config
                self._tool_metrics[tool_name] = {
                    "execution_count": 0,
                    "success_count": 0,
                    "failure_count": 0,
                    "total_execution_time": 0.0
                }

            except Exception as e:
                self.logger.warning(f"Failed to register discovered tool {tool_name}: {e}")

    async def register_tool(self, tool_name: str, tool_config: ToolConfig) -> bool:
        """
        Register a new tool.

        Args:
            tool_name: Unique name for the tool
            tool_config: Configuration for the tool

        Returns:
            True if tool was successfully registered, False otherwise
        """
        try:
            if tool_name in self._tool_registry:
                self.logger.warning(f"Tool {tool_name} already registered, updating configuration")

            self._tool_registry[tool_name] = tool_config

            # Initialize metrics for the tool
            if tool_name not in self._tool_metrics:
                self._tool_metrics[tool_name] = {
                    "execution_count": 0,
                    "success_count": 0,
                    "failure_count": 0,
                    "total_execution_time": 0.0
                }

            self.logger.info(f"Tool {tool_name} registered successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to register tool {tool_name}: {e}")
            return False

    async def unregister_tool(self, tool_name: str) -> bool:
        """
        Unregister a tool.

        Args:
            tool_name: Name of the tool to unregister

        Returns:
            True if tool was successfully unregistered, False otherwise
        """
        try:
            if tool_name not in self._tool_registry:
                self.logger.warning(f"Tool {tool_name} not found in registry")
                return False

            del self._tool_registry[tool_name]

            # Clean up metrics
            if tool_name in self._tool_metrics:
                del self._tool_metrics[tool_name]

            self.logger.info(f"Tool {tool_name} unregistered successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to unregister tool {tool_name}: {e}")
            return False

    async def get_tool(self, tool_name: str) -> Optional[ToolConfig]:
        """
        Retrieve a tool configuration by name.

        Args:
            tool_name: Name of the tool to retrieve

        Returns:
            Tool configuration if found, None otherwise
        """
        return self._tool_registry.get(tool_name)

    async def list_tools(self, category: Optional[str] = None) -> List[str]:
        """
        List available tools.

        Args:
            category: Optional category to filter tools

        Returns:
            List of tool names matching the criteria
        """
        if category is None:
            return list(self._tool_registry.keys())

        # Filter by tool type if category is specified
        filtered_tools = []
        for tool_name, tool_config in self._tool_registry.items():
            tool_type_value = tool_config.tool_type.value if hasattr(tool_config.tool_type, 'value') else tool_config.tool_type
            if tool_type_value == category:
                filtered_tools.append(tool_name)

        return filtered_tools

    async def execute_tool(
        self,
        tool_name: str,
        operation: str,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> ToolResult:
        """
        Execute a tool operation.

        Args:
            tool_name: Name of the tool to execute
            operation: Specific operation to perform
            parameters: Parameters for the operation
            context: Optional execution context

        Returns:
            Result of the tool execution
        """
        execution_id = str(uuid.uuid4())
        started_at = datetime.utcnow()

        try:
            # Update metrics
            if tool_name in self._tool_metrics:
                self._tool_metrics[tool_name]["execution_count"] += 1

            # Execute using existing executor
            result = await self.executor.execute_tool(tool_name, operation, **parameters)

            completed_at = datetime.utcnow()
            execution_time = (completed_at - started_at).total_seconds()

            # Update success metrics
            if tool_name in self._tool_metrics:
                self._tool_metrics[tool_name]["success_count"] += 1
                self._tool_metrics[tool_name]["total_execution_time"] += execution_time

            # Create ToolResult
            tool_result = ToolResult(
                tool_name=tool_name,
                operation=operation,
                execution_id=execution_id,
                success=True,
                status="completed",
                message="Tool execution completed successfully",
                result=result,
                execution_time_seconds=execution_time,
                input_parameters=parameters,
                started_at=started_at,
                completed_at=completed_at
            )

            return tool_result

        except Exception as e:
            completed_at = datetime.utcnow()
            execution_time = (completed_at - started_at).total_seconds()

            # Update failure metrics
            if tool_name in self._tool_metrics:
                self._tool_metrics[tool_name]["failure_count"] += 1
                self._tool_metrics[tool_name]["total_execution_time"] += execution_time

            # Create error ToolResult
            tool_result = ToolResult(
                tool_name=tool_name,
                operation=operation,
                execution_id=execution_id,
                success=False,
                status="failed",
                message=f"Tool execution failed: {str(e)}",
                error_code="EXECUTION_ERROR",
                error_message=str(e),
                execution_time_seconds=execution_time,
                input_parameters=parameters,
                started_at=started_at,
                completed_at=completed_at
            )

            return tool_result

    async def execute_tool_sequence(
        self,
        operations: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> List[ToolResult]:
        """
        Execute a sequence of tool operations.

        Args:
            operations: List of operation definitions
            context: Optional execution context

        Returns:
            List of tool execution results
        """
        results = []

        for operation in operations:
            tool_name = operation.get("tool_name")
            operation_name = operation.get("operation")
            parameters = operation.get("parameters", {})

            if not tool_name or not operation_name:
                # Create error result for invalid operation
                error_result = ToolResult(
                    tool_name=tool_name or "unknown",
                    operation=operation_name or "unknown",
                    execution_id=str(uuid.uuid4()),
                    success=False,
                    status="failed",
                    message="Invalid operation definition",
                    error_code="INVALID_OPERATION",
                    error_message="Missing tool_name or operation",
                    execution_time_seconds=0.0,
                    started_at=datetime.utcnow(),
                    completed_at=datetime.utcnow()
                )
                results.append(error_result)
                continue

            result = await self.execute_tool(tool_name, operation_name, parameters, context)
            results.append(result)

            # Stop on failure if specified
            if not result.success and operation.get("stop_on_failure", False):
                break

        return results

    async def validate_tool_parameters(
        self,
        tool_name: str,
        operation: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate parameters for a tool operation.

        Args:
            tool_name: Name of the tool
            operation: Operation to validate parameters for
            parameters: Parameters to validate

        Returns:
            Validation result with status and any error messages
        """
        try:
            # Try to use existing validation from inspector
            try:
                validation_errors = self.validate_operation_params(tool_name, operation, parameters)
            except Exception:
                # Fallback validation using tool config
                tool_config = await self.get_tool(tool_name)
                if not tool_config:
                    raise ValueError(f"Tool {tool_name} not found")

                if operation not in tool_config.operations:
                    raise ValueError(f"Operation {operation} not found for tool {tool_name}")

                # Basic validation - just check if tool and operation exist
                validation_errors = []

            return {
                "valid": len(validation_errors) == 0,
                "errors": validation_errors,
                "tool_name": tool_name,
                "operation": operation
            }

        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Validation failed: {str(e)}"],
                "tool_name": tool_name,
                "operation": operation
            }

    async def get_tool_capabilities(self, tool_name: str) -> Dict[str, Any]:
        """
        Get the capabilities of a specific tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Dictionary describing tool capabilities and operations
        """
        try:
            tool_config = await self.get_tool(tool_name)
            if not tool_config:
                raise ValueError(f"Tool {tool_name} not found")

            # Try to get operations info from inspector, fallback to config
            try:
                operations_info = self.get_tool_operations_info(tool_name)
            except Exception:
                # Fallback to operations from tool config
                operations_info = tool_config.operations

            return {
                "tool_name": tool_name,
                "tool_type": tool_config.tool_type.value if hasattr(tool_config.tool_type, 'value') else tool_config.tool_type,
                "description": tool_config.description,
                "version": tool_config.version,
                "operations": operations_info,
                "enabled": tool_config.enabled,
                "requires_auth": tool_config.requires_auth,
                "security_level": tool_config.security_level
            }

        except Exception as e:
            self.logger.error(f"Failed to get capabilities for tool {tool_name}: {e}")
            raise

    async def get_tool_schema(self, tool_name: str, operation: str) -> Dict[str, Any]:
        """
        Get the parameter schema for a tool operation.

        Args:
            tool_name: Name of the tool
            operation: Operation to get schema for

        Returns:
            JSON schema describing the operation parameters
        """
        try:
            # Try to get signature from inspector, fallback to tool config
            try:
                signature = self.get_operation_signature(tool_name, operation)
            except Exception:
                # Fallback to tool config
                tool_config = await self.get_tool(tool_name)
                if not tool_config or operation not in tool_config.operations:
                    raise ValueError(f"Operation {operation} not found for tool {tool_name}")

                operation_config = tool_config.operations[operation]
                signature = {"parameters": operation_config.get("parameters", {})}

            # Convert signature to JSON schema format
            schema = {
                "type": "object",
                "properties": {},
                "required": []
            }

            if "parameters" in signature:
                for param_name, param_info in signature["parameters"].items():
                    schema["properties"][param_name] = {
                        "type": param_info.get("type", "string"),
                        "description": param_info.get("description", "")
                    }

                    if param_info.get("required", False):
                        schema["required"].append(param_name)

            return schema

        except Exception as e:
            self.logger.error(f"Failed to get schema for {tool_name}.{operation}: {e}")
            raise

    async def register_tool_adapter(
        self,
        adapter_name: str,
        adapter_func: Callable
    ) -> bool:
        """
        Register a tool adapter for external tool integration.

        Args:
            adapter_name: Name of the adapter
            adapter_func: Function that adapts external tools

        Returns:
            True if adapter was successfully registered, False otherwise
        """
        try:
            self._tool_adapters[adapter_name] = adapter_func
            self.logger.info(f"Tool adapter {adapter_name} registered successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to register adapter {adapter_name}: {e}")
            return False

    async def get_available_adapters(self) -> List[str]:
        """
        Get list of available tool adapters.

        Returns:
            List of registered adapter names
        """
        return list(self._tool_adapters.keys())

    async def create_tool_from_adapter(
        self,
        adapter_name: str,
        tool_config: Dict[str, Any]
    ) -> str:
        """
        Create a tool using an adapter.

        Args:
            adapter_name: Name of the adapter to use
            tool_config: Configuration for the tool creation

        Returns:
            Name of the created tool
        """
        if adapter_name not in self._tool_adapters:
            raise ValueError(f"Adapter {adapter_name} not found")

        try:
            adapter_func = self._tool_adapters[adapter_name]
            tool_name = adapter_func(tool_config)

            self.logger.info(f"Tool {tool_name} created using adapter {adapter_name}")
            return tool_name

        except Exception as e:
            self.logger.error(f"Failed to create tool using adapter {adapter_name}: {e}")
            raise

    async def get_tool_metrics(self, tool_name: str) -> Dict[str, Any]:
        """
        Get execution metrics for a tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Dictionary containing tool execution metrics
        """
        if tool_name not in self._tool_metrics:
            raise ValueError(f"No metrics found for tool {tool_name}")

        metrics = self._tool_metrics[tool_name].copy()

        # Calculate additional metrics
        total_executions = metrics["execution_count"]
        if total_executions > 0:
            metrics["success_rate"] = metrics["success_count"] / total_executions
            metrics["failure_rate"] = metrics["failure_count"] / total_executions
            metrics["average_execution_time"] = metrics["total_execution_time"] / total_executions
        else:
            metrics["success_rate"] = 0.0
            metrics["failure_rate"] = 0.0
            metrics["average_execution_time"] = 0.0

        return metrics

    async def cleanup(self) -> None:
        """
        Clean up resources used by the tool manager.
        """
        try:
            # Clear all caches
            self.clear_all_caches()

            # Clear registries
            self._tool_registry.clear()
            self._tool_adapters.clear()
            self._tool_metrics.clear()

            self._initialized = False
            self.logger.info("ToolManager cleanup completed")

        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

    # ===== DISCOVERY INTERFACE =====

    def get_available_tools(self) -> List[str]:
        """
        Retrieve a list of all available tools.

        Returns:
            List[str]: A list of tool names.
        """
        return self.discovery.get_available_tools()

    def get_available_operations(self, tool_name: Optional[str] = None) -> Union[Dict[str, List[str]], List[str]]:
        """
        Retrieve available operations for tools.

        Args:
            tool_name (Optional[str]): Optional, the name of a specific tool.
                                     If provided, returns only the operations for that tool.

        Returns:
            Union[Dict[str, List[str]], List[str]]: If a tool name is specified, returns a list
                                                  of operations for that tool. Otherwise, returns
                                                  a dictionary mapping all tools to their operations.
        """
        return self.discovery.get_available_operations(tool_name)

    def is_tool_available(self, tool_name: str) -> bool:
        """
        Check if a specific tool is available.

        Args:
            tool_name (str): Name of the tool to check.

        Returns:
            bool: True if the tool is available, False otherwise.
        """
        return self.discovery.is_tool_available(tool_name)

    def is_operation_available(self, tool_name: str, operation_name: str) -> bool:
        """
        Check if a specific operation is available for a tool.

        Args:
            tool_name (str): Name of the tool.
            operation_name (str): Name of the operation.

        Returns:
            bool: True if the operation is available for the tool, False otherwise.
        """
        return self.discovery.is_operation_available(tool_name, operation_name)

    def refresh_discovery(self) -> None:
        """
        Refresh the discovery process to pick up any newly registered tools.

        This method refreshes all components to ensure they have the latest tool information.
        """
        self.logger.info("Refreshing tool discovery across all components")

        # Refresh discovery
        self.discovery.refresh_discovery()

        # Clear caches in other components to ensure consistency
        self.inspector.clear_cache()
        self.executor.clear_cache()

        self.logger.info("Tool discovery refresh completed across all components")

    # ===== INSPECTION INTERFACE =====

    def get_operation_info(self, operation_spec: str) -> Dict[str, Any]:
        """
        Retrieve detailed information about an operation.

        Args:
            operation_spec (str): The operation specification in the format 'tool_name.operation_name'.

        Returns:
            Dict[str, Any]: A dictionary containing the tool name, operation name, description,
                          and signature details.

        Raises:
            ValueError: If the operation specification is invalid or the tool/operation does not exist.
        """
        return self.inspector.get_operation_info(operation_spec)

    def get_operation_signature(self, tool_name: str, operation_name: str) -> Dict[str, Any]:
        """
        Get the signature information for a specific operation.

        Args:
            tool_name (str): Name of the tool.
            operation_name (str): Name of the operation.

        Returns:
            Dict[str, Any]: Dictionary containing signature information.
        """
        return self.inspector.get_operation_signature(tool_name, operation_name)

    def validate_operation_params(self, tool_name: str, operation_name: str, params: Dict[str, Any]) -> List[str]:
        """
        Validate parameters for a tool operation.

        Args:
            tool_name (str): Name of the tool.
            operation_name (str): Name of the operation.
            params (Dict[str, Any]): Parameters to validate.

        Returns:
            List[str]: List of validation error messages (empty if valid).
        """
        return self.inspector.validate_operation_params(tool_name, operation_name, params)

    def get_tool_operations_info(self, tool_name: str) -> Dict[str, Dict[str, Any]]:
        """
        Get information about all operations for a specific tool.

        Args:
            tool_name (str): Name of the tool to get operations info for.

        Returns:
            Dict[str, Dict[str, Any]]: Dictionary mapping operation names to their info.

        Raises:
            ValueError: If the tool does not exist.
        """
        return self.inspector.get_tool_operations_info(tool_name)

    # ===== EXECUTION INTERFACE =====

    async def execute_tool(self, tool_name: str, operation_name: str, **params) -> Any:
        """
        Execute a tool operation with the given parameters.

        Args:
            tool_name (str): Name of the tool to execute.
            operation_name (str): Name of the operation to execute.
            **params: Parameters to pass to the operation.

        Returns:
            Any: The result of the tool operation.

        Raises:
            ValueError: If the tool or operation does not exist.
        """
        return await self.executor.execute_tool(tool_name, operation_name, **params)

    def execute_tool_sync(self, tool_name: str, operation_name: str, **params) -> Any:
        """
        Synchronously execute a tool operation.

        Args:
            tool_name (str): Name of the tool to execute.
            operation_name (str): Name of the operation to execute.
            **params: Parameters to pass to the operation.

        Returns:
            Any: The result of the tool operation.
        """
        return self.executor.execute_tool_sync(tool_name, operation_name, **params)

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
        return self.executor.execute_operation_spec(operation_spec, **params)

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
        return await self.executor.execute_operation_spec_async(operation_spec, **params)

    # ===== BATCH OPERATIONS =====

    def execute_batch_sync(self, operations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Execute multiple operations synchronously in batch.

        Args:
            operations (List[Dict[str, Any]]): List of operation dictionaries.

        Returns:
            List[Dict[str, Any]]: List of results with success/error information.
        """
        return self.executor.execute_batch_sync(operations)

    async def execute_batch_async(self, operations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Execute multiple operations asynchronously in batch.

        Args:
            operations (List[Dict[str, Any]]): List of operation dictionaries.

        Returns:
            List[Dict[str, Any]]: List of results with success/error information.
        """
        return await self.executor.execute_batch_async(operations)

    # ===== UTILITY AND MANAGEMENT METHODS =====

    def get_system_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics about the tool system.

        Returns:
            Dict[str, Any]: Dictionary containing statistics from all components.
        """
        return {
            "discovery": self.discovery.get_discovery_stats(),
            "inspector": self.inspector.get_cache_stats(),
            "executor": self.executor.get_execution_stats(),
            "executor_cache": self.executor.get_cache_stats()
        }

    def clear_all_caches(self) -> None:
        """
        Clear all caches across all components.

        This method clears caches in discovery, inspector, and executor components
        to force fresh data on next access.
        """
        self.logger.info("Clearing all caches across tool components")

        self.inspector.clear_cache()
        self.executor.clear_cache()

        self.logger.info("All tool component caches cleared")

    def reset_execution_stats(self) -> None:
        """
        Reset execution statistics in the executor component.
        """
        self.executor.reset_stats()

    def validate_and_execute_sync(self, tool_name: str, operation_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate parameters and execute operation synchronously with comprehensive result information.

        Args:
            tool_name (str): Name of the tool.
            operation_name (str): Name of the operation.
            params (Dict[str, Any]): Parameters to validate and use for execution.

        Returns:
            Dict[str, Any]: Dictionary containing validation results, execution results, and metadata.
        """
        result = {
            "tool_name": tool_name,
            "operation_name": operation_name,
            "validation_errors": [],
            "execution_success": False,
            "execution_result": None,
            "execution_error": None
        }

        try:
            # Validate parameters
            validation_errors = self.validate_operation_params(tool_name, operation_name, params)
            result["validation_errors"] = validation_errors

            if validation_errors:
                result["execution_error"] = f"Validation failed: {'; '.join(validation_errors)}"
                return result

            # Execute operation
            execution_result = self.execute_tool_sync(tool_name, operation_name, **params)
            result["execution_success"] = True
            result["execution_result"] = execution_result

        except Exception as e:
            result["execution_error"] = str(e)

        return result

    async def validate_and_execute_async(self, tool_name: str, operation_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate parameters and execute operation asynchronously with comprehensive result information.

        Args:
            tool_name (str): Name of the tool.
            operation_name (str): Name of the operation.
            params (Dict[str, Any]): Parameters to validate and use for execution.

        Returns:
            Dict[str, Any]: Dictionary containing validation results, execution results, and metadata.
        """
        result = {
            "tool_name": tool_name,
            "operation_name": operation_name,
            "validation_errors": [],
            "execution_success": False,
            "execution_result": None,
            "execution_error": None
        }

        try:
            # Validate parameters
            validation_errors = self.validate_operation_params(tool_name, operation_name, params)
            result["validation_errors"] = validation_errors

            if validation_errors:
                result["execution_error"] = f"Validation failed: {'; '.join(validation_errors)}"
                return result

            # Execute operation
            execution_result = await self.execute_tool(tool_name, operation_name, **params)
            result["execution_success"] = True
            result["execution_result"] = execution_result

        except Exception as e:
            result["execution_error"] = str(e)

        return result

    def get_component_health(self) -> Dict[str, bool]:
        """
        Check the health status of all components.

        Returns:
            Dict[str, bool]: Dictionary indicating the health status of each component.
        """
        health = {}

        try:
            # Test discovery component
            tools = self.discovery.get_available_tools()
            health["discovery"] = isinstance(tools, list)
        except Exception:
            health["discovery"] = False

        try:
            # Test inspector component
            stats = self.inspector.get_cache_stats()
            health["inspector"] = isinstance(stats, dict)
        except Exception:
            health["inspector"] = False

        try:
            # Test executor component
            stats = self.executor.get_execution_stats()
            health["executor"] = isinstance(stats, dict)
        except Exception:
            health["executor"] = False

        return health

    def __repr__(self) -> str:
        """
        String representation of the ToolManager.

        Returns:
            str: String representation including component status.
        """
        stats = self.get_system_stats()
        discovery_stats = stats.get("discovery", {})

        return (f"ToolManager("
                f"tools={discovery_stats.get('total_tools', 0)}, "
                f"operations={discovery_stats.get('total_operations', 0)}, "
                f"components=['discovery', 'inspector', 'executor'])")
