import inspect
import logging
import asyncio
from typing import Dict, List, Any, Optional, Union

from app.tools import get_tool, list_tools

class MultiTaskTools:
    """
    Dynamic tool loader focused on discovering tools and their sub-operations for AI usage.

    Core functionality:
    1. Discover all available tools and sub-operations.
    2. Retrieve detailed information about sub-operations (documentation, parameters, async/sync status, etc.).
    """
    def __init__(self):
        # Initialize logger
        self.logger = logging.getLogger(__name__)
        # Cache for tool instances
        self._tools_cache = {}
        # Cache for sub-operations
        self._operations_cache = {}
        # Cache for sub-operation documentation
        self._operation_docs_cache = {}
        # Retrieve all available tools
        self._available_tools = list_tools()
        # Discover all sub-operations for the tools
        self._available_operations = self._discover_all_operations()

    def _get_tool_instance(self, tool_name: str) -> Any:
        """
        Retrieve a tool instance, using caching to avoid redundant creation.

        Args:
            tool_name: Name of the tool to retrieve.

        Returns:
            The tool instance.

        Raises:
            ValueError: If the tool does not exist.
        """
        if tool_name not in self._tools_cache:
            try:
                self._tools_cache[tool_name] = get_tool(tool_name)
            except ValueError as e:
                raise ValueError(f"Tool '{tool_name}' does not exist: {e}")
        return self._tools_cache[tool_name]

    def _discover_all_operations(self) -> Dict[str, List[str]]:
        """
        Discover all sub-operations (methods) for each available tool.

        Returns:
            A dictionary mapping tool names to lists of their sub-operations.
        """
        operations = {}
        for tool_name in self._available_tools:
            try:
                tool = self._get_tool_instance(tool_name)
                tool_ops = self._get_tool_operations(tool)
                operations[tool_name] = tool_ops
            except Exception as e:
                self.logger.warning(f"Error retrieving sub-operations for tool {tool_name}: {e}")
        return operations

    def _get_tool_operations(self, tool: Any) -> List[str]:
        """
        Retrieve all sub-operations (public methods) of a tool.

        Args:
            tool: The tool instance to inspect.

        Returns:
            A list of public method names (sub-operations).
        """
        operations = []
        for name, method in inspect.getmembers(tool, inspect.ismethod):
            # Exclude private methods and the 'run' method
            if not name.startswith('_') and name != 'run':
                operations.append(name)
        return operations

    def _get_operation_doc(self, tool_name: str, operation_name: str) -> str:
        """
        Retrieve the documentation string for a sub-operation.

        Args:
            tool_name: Name of the tool.
            operation_name: Name of the sub-operation.

        Returns:
            The documentation string, or "No documentation" if unavailable.
        """
        cache_key = f"{tool_name}.{operation_name}"
        if cache_key in self._operation_docs_cache:
            return self._operation_docs_cache[cache_key]

        try:
            tool = self._get_tool_instance(tool_name)
            method = getattr(tool, operation_name, None)
            if method:
                # Unwrap decorators to access the original method
                method = inspect.unwrap(method)
                doc = method.__doc__.strip() if method.__doc__ else "No documentation"
                self._operation_docs_cache[cache_key] = doc
                return doc
        except Exception as e:
            self.logger.warning(f"Error retrieving documentation for operation {tool_name}.{operation_name}: {e}")
        return "No documentation"

    def _analyze_operation_signature(self, tool_name: str, operation_name: str) -> Dict[str, Any]:
        """
        Analyze the signature of a sub-operation to retrieve parameter information.

        Args:
            tool_name: Name of the tool.
            operation_name: Name of the sub-operation.

        Returns:
            A dictionary containing parameter details, return type, and whether the operation is async.
        """
        try:
            tool = self._get_tool_instance(tool_name)
            method = getattr(tool, operation_name)
            sig = inspect.signature(method)
            params = {}
            for name, param in sig.parameters.items():
                if name == 'self':
                    continue
                params[name] = {
                    "name": name,
                    "required": param.default == inspect.Parameter.empty,
                    "default": None if param.default == inspect.Parameter.empty else param.default,
                    "type": str(param.annotation) if param.annotation != inspect.Parameter.empty else "Any"
                }
            return_type = str(sig.return_annotation) if sig.return_annotation != inspect.Signature.empty else "Any"
            return {
                "parameters": params,
                "return_type": return_type,
                "is_async": asyncio.iscoroutinefunction(method)
            }
        except Exception as e:
            self.logger.warning(f"Error analyzing signature for operation {tool_name}.{operation_name}: {e}")
            return {"parameters": {}, "return_type": "Any", "is_async": False}

    # Public API

    def get_available_tools(self) -> List[str]:
        """
        Retrieve a list of all available tools.

        Returns:
            A list of tool names.
        """
        return self._available_tools

    def get_available_operations(self, tool_name: Optional[str] = None) -> Union[Dict[str, List[str]], List[str]]:
        """
        Retrieve available sub-operations for tools.

        Args:
            tool_name: Optional, the name of a specific tool. If provided, returns only the sub-operations for that tool.

        Returns:
            If a tool name is specified, returns a list of sub-operations for that tool.
            Otherwise, returns a dictionary mapping all tools to their sub-operations.
        """
        if tool_name:
            return self._available_operations.get(tool_name, [])
        return self._available_operations

    def get_operation_info(self, operation_spec: str) -> Dict[str, Any]:
        """
        Retrieve detailed information about a sub-operation.

        Args:
            operation_spec: The sub-operation specification in the format 'tool_name.operation_name'.

        Returns:
            A dictionary containing the tool name, operation name, description, and signature details.

        Raises:
            ValueError: If the operation specification is invalid or the tool/operation does not exist.
        """
        if "." not in operation_spec:
            raise ValueError(f"Invalid operation specification: {operation_spec}, expected 'tool_name.operation_name' format")

        tool_name, operation_name = operation_spec.split(".", 1)
        if tool_name not in self._available_tools:
            raise ValueError(f"Tool '{tool_name}' does not exist")
        if operation_name not in self._available_operations.get(tool_name, []):
            raise ValueError(f"Operation '{operation_name}' not found in tool '{tool_name}'")

        doc = self._get_operation_doc(tool_name, operation_name)
        signature = self._analyze_operation_signature(tool_name, operation_name)
        return {
            "tool": tool_name,
            "operation": operation_name,
            "description": doc,
            "signature": signature
        }

    async def execute_tool(self, tool_name: str, operation_name: str, **params) -> Any:
        """
        Execute a tool operation with the given parameters.

        Args:
            tool_name: Name of the tool to execute.
            operation_name: Name of the operation to execute.
            **params: Parameters to pass to the operation.

        Returns:
            The result of the tool operation.

        Raises:
            ValueError: If the tool or operation does not exist.
        """
        try:
            # Get tool instance
            tool = self._get_tool_instance(tool_name)

            # Check if operation exists
            if operation_name not in self._available_operations.get(tool_name, []):
                raise ValueError(f"Operation '{operation_name}' not found in tool '{tool_name}'")

            # Get the operation method
            operation = getattr(tool, operation_name)

            # Execute the operation
            if asyncio.iscoroutinefunction(operation):
                return await operation(**params)
            else:
                return operation(**params)

        except Exception as e:
            self.logger.error(f"Error executing {tool_name}.{operation_name}: {e}")
            raise ValueError(f"Error executing {tool_name}.{operation_name}: {e}")

    def execute_tool_sync(self, tool_name: str, operation_name: str, **params) -> Any:
        """
        Synchronously execute a tool operation.

        Args:
            tool_name: Name of the tool to execute.
            operation_name: Name of the operation to execute.
            **params: Parameters to pass to the operation.

        Returns:
            The result of the tool operation.
        """
        try:
            # Get tool instance
            tool = self._get_tool_instance(tool_name)

            # Check if operation exists
            if operation_name not in self._available_operations.get(tool_name, []):
                raise ValueError(f"Operation '{operation_name}' not found in tool '{tool_name}'")

            # Get the operation method
            operation = getattr(tool, operation_name)

            # Execute the operation (must be synchronous)
            if asyncio.iscoroutinefunction(operation):
                raise ValueError(f"Cannot execute async operation '{operation_name}' synchronously")

            return operation(**params)

        except Exception as e:
            self.logger.error(f"Error executing {tool_name}.{operation_name}: {e}")
            raise ValueError(f"Error executing {tool_name}.{operation_name}: {e}")

    def get_operation_signature(self, tool_name: str, operation_name: str) -> Dict[str, Any]:
        """
        Get the signature information for a specific operation.

        Args:
            tool_name: Name of the tool.
            operation_name: Name of the operation.

        Returns:
            Dictionary containing signature information.
        """
        operation_spec = f"{tool_name}.{operation_name}"
        return self.get_operation_info(operation_spec)["signature"]

    def validate_operation_params(self, tool_name: str, operation_name: str, params: Dict[str, Any]) -> List[str]:
        """
        Validate parameters for a tool operation.

        Args:
            tool_name: Name of the tool.
            operation_name: Name of the operation.
            params: Parameters to validate.

        Returns:
            List of validation error messages (empty if valid).
        """
        errors = []

        try:
            signature = self.get_operation_signature(tool_name, operation_name)
            required_params = {name: info for name, info in signature["parameters"].items() if info["required"]}

            # Check for missing required parameters
            for param_name in required_params:
                if param_name not in params:
                    errors.append(f"Missing required parameter: {param_name}")

            # Check for unknown parameters
            valid_params = set(signature["parameters"].keys())
            for param_name in params:
                if param_name not in valid_params:
                    errors.append(f"Unknown parameter: {param_name}")

        except Exception as e:
            errors.append(f"Error validating parameters: {e}")

        return errors
