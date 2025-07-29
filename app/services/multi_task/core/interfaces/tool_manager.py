"""
Tool Manager Interface

Defines the contract for tool management implementations in the multi-task architecture.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Callable
from ..models.execution_models import ToolConfig, ToolResult


class IToolManager(ABC):
    """
    Abstract interface for tool management implementations.

    This interface defines the core contract for managing tools,
    including registration, execution, and lifecycle management.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the tool manager.

        Sets up tool registry, loads available tools, and prepares
        the manager for tool operations.

        Raises:
            Exception: If initialization fails
        """
        pass

    @abstractmethod
    async def register_tool(self, tool_name: str, tool_config: ToolConfig) -> bool:
        """
        Register a new tool.

        Args:
            tool_name: Unique name for the tool
            tool_config: Configuration for the tool

        Returns:
            True if tool was successfully registered, False otherwise

        Raises:
            ToolRegistrationError: If registration fails
            ValidationError: If tool configuration is invalid
        """
        pass

    @abstractmethod
    async def unregister_tool(self, tool_name: str) -> bool:
        """
        Unregister a tool.

        Args:
            tool_name: Name of the tool to unregister

        Returns:
            True if tool was successfully unregistered, False otherwise

        Raises:
            ToolNotFoundException: If tool is not found
            ToolException: If unregistration fails
        """
        pass

    @abstractmethod
    async def get_tool(self, tool_name: str) -> Optional[ToolConfig]:
        """
        Retrieve a tool configuration by name.

        Args:
            tool_name: Name of the tool to retrieve

        Returns:
            Tool configuration if found, None otherwise

        Raises:
            ToolException: If retrieval fails
        """
        pass

    @abstractmethod
    async def list_tools(self, category: Optional[str] = None) -> List[str]:
        """
        List available tools.

        Args:
            category: Optional category to filter tools

        Returns:
            List of tool names matching the criteria

        Raises:
            ToolException: If listing fails
        """
        pass

    @abstractmethod
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

        Raises:
            ToolNotFoundException: If tool is not found
            ToolExecutionError: If execution fails
            ValidationError: If parameters are invalid
        """
        pass

    @abstractmethod
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

        Raises:
            ToolExecutionError: If any operation fails
        """
        pass

    @abstractmethod
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

        Raises:
            ToolNotFoundException: If tool is not found
            ValidationError: If validation process fails
        """
        pass

    @abstractmethod
    async def get_tool_capabilities(self, tool_name: str) -> Dict[str, Any]:
        """
        Get the capabilities of a specific tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Dictionary describing tool capabilities and operations

        Raises:
            ToolNotFoundException: If tool is not found
            ToolException: If capability retrieval fails
        """
        pass

    @abstractmethod
    async def get_tool_schema(self, tool_name: str, operation: str) -> Dict[str, Any]:
        """
        Get the parameter schema for a tool operation.

        Args:
            tool_name: Name of the tool
            operation: Operation to get schema for

        Returns:
            JSON schema describing the operation parameters

        Raises:
            ToolNotFoundException: If tool is not found
            OperationNotFoundException: If operation is not found
            ToolException: If schema retrieval fails
        """
        pass

    @abstractmethod
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

        Raises:
            AdapterRegistrationError: If registration fails
        """
        pass

    @abstractmethod
    async def get_available_adapters(self) -> List[str]:
        """
        Get list of available tool adapters.

        Returns:
            List of registered adapter names

        Raises:
            ToolException: If retrieval fails
        """
        pass

    @abstractmethod
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

        Raises:
            AdapterNotFoundException: If adapter is not found
            ToolCreationError: If tool creation fails
        """
        pass

    @abstractmethod
    async def get_tool_metrics(self, tool_name: str) -> Dict[str, Any]:
        """
        Get execution metrics for a tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Dictionary containing tool execution metrics

        Raises:
            ToolNotFoundException: If tool is not found
            ToolException: If metrics retrieval fails
        """
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """
        Clean up resources used by the tool manager.

        This method should be called when the manager is being shut down
        to properly release any held resources.
        """
        pass
