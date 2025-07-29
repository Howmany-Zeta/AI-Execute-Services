"""
Tool Inspector Module

This module is responsible for providing detailed information about specific tools and operations.
It handles inspection and analysis of tools without executing any operations - it only "looks" at them.
"""

import inspect
import logging
import asyncio
from typing import Dict, List, Any, Optional

# Import tools functions with delayed import to avoid circular dependencies
def _get_tool(tool_name: str):
    """Get tool with delayed import to avoid circular dependencies."""
    try:
        from app.tools import get_tool
        return get_tool(tool_name)
    except ImportError as e:
        raise ImportError(f"Could not import tool function: {e}")
from ..discovery.tool_discovery import ToolDiscovery


class ToolInspector:
    """
    Tool inspector component responsible for analyzing and providing detailed information about tools and operations.

    This class handles the inspection of tools and their operations, providing detailed information
    about signatures, documentation, parameters, and validation capabilities.
    """

    def __init__(self, tool_discovery: Optional[ToolDiscovery] = None):
        """
        Initialize the tool inspector.

        Args:
            tool_discovery (Optional[ToolDiscovery]): Tool discovery instance to use.
                                                    If None, creates a new instance.
        """
        # Initialize logger
        self.logger = logging.getLogger(__name__)

        # Tool discovery instance for checking tool availability
        self.tool_discovery = tool_discovery or ToolDiscovery()

        # Cache for tool instances to avoid redundant creation
        self._tools_cache: Dict[str, Any] = {}

        # Cache for operation documentation
        self._operation_docs_cache: Dict[str, str] = {}

        # Cache for operation signatures
        self._operation_signature_cache: Dict[str, Dict[str, Any]] = {}

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

    def _get_operation_doc(self, tool_name: str, operation_name: str) -> str:
        """
        Retrieve the documentation string for a specific operation.

        This method extracts and caches the docstring from an operation method,
        handling decorator unwrapping to access the original method documentation.

        Args:
            tool_name (str): Name of the tool containing the operation.
            operation_name (str): Name of the operation to get documentation for.

        Returns:
            str: The documentation string, or "No documentation" if unavailable.
        """
        # Create cache key
        cache_key = f"{tool_name}.{operation_name}"

        # Check cache first
        if cache_key in self._operation_docs_cache:
            return self._operation_docs_cache[cache_key]

        try:
            # Get tool instance
            tool = self._get_tool_instance(tool_name)

            # Get the operation method
            method = getattr(tool, operation_name, None)
            if method is None:
                doc = "Operation not found"
            else:
                # Unwrap decorators to access the original method
                unwrapped_method = inspect.unwrap(method)

                # Extract documentation
                if unwrapped_method.__doc__:
                    doc = unwrapped_method.__doc__.strip()
                else:
                    doc = "No documentation"

            # Cache the result
            self._operation_docs_cache[cache_key] = doc
            return doc

        except Exception as e:
            self.logger.warning(f"Error retrieving documentation for operation {tool_name}.{operation_name}: {e}")
            doc = "Error retrieving documentation"
            self._operation_docs_cache[cache_key] = doc
            return doc

    def _analyze_operation_signature(self, tool_name: str, operation_name: str) -> Dict[str, Any]:
        """
        Analyze the signature of an operation to retrieve detailed parameter information.

        This method performs deep analysis of an operation's signature, extracting information
        about parameters, return types, and whether the operation is asynchronous.

        Args:
            tool_name (str): Name of the tool containing the operation.
            operation_name (str): Name of the operation to analyze.

        Returns:
            Dict[str, Any]: A dictionary containing detailed signature information including:
                          - parameters: Dict of parameter details (name, required, default, type)
                          - return_type: The return type annotation
                          - is_async: Whether the operation is asynchronous
        """
        # Create cache key
        cache_key = f"{tool_name}.{operation_name}"

        # Check cache first
        if cache_key in self._operation_signature_cache:
            return self._operation_signature_cache[cache_key]

        try:
            # Get tool instance
            tool = self._get_tool_instance(tool_name)

            # Get the operation method
            method = getattr(tool, operation_name)

            # Get method signature
            sig = inspect.signature(method)

            # Analyze parameters
            params = {}
            for name, param in sig.parameters.items():
                # Skip 'self' parameter
                if name == 'self':
                    continue

                # Extract parameter information
                param_info = {
                    "name": name,
                    "required": param.default == inspect.Parameter.empty,
                    "default": None if param.default == inspect.Parameter.empty else param.default,
                    "type": str(param.annotation) if param.annotation != inspect.Parameter.empty else "Any",
                    "kind": param.kind.name  # POSITIONAL_ONLY, POSITIONAL_OR_KEYWORD, etc.
                }

                params[name] = param_info

            # Extract return type
            return_type = str(sig.return_annotation) if sig.return_annotation != inspect.Signature.empty else "Any"

            # Check if method is async
            is_async = asyncio.iscoroutinefunction(method)

            # Build signature information
            signature_info = {
                "parameters": params,
                "return_type": return_type,
                "is_async": is_async,
                "parameter_count": len(params),
                "required_parameter_count": len([p for p in params.values() if p["required"]])
            }

            # Cache the result
            self._operation_signature_cache[cache_key] = signature_info
            return signature_info

        except Exception as e:
            self.logger.warning(f"Error analyzing signature for operation {tool_name}.{operation_name}: {e}")

            # Return default signature info on error
            default_signature = {
                "parameters": {},
                "return_type": "Any",
                "is_async": False,
                "parameter_count": 0,
                "required_parameter_count": 0
            }

            self._operation_signature_cache[cache_key] = default_signature
            return default_signature

    def get_operation_info(self, operation_spec: str) -> Dict[str, Any]:
        """
        Get complete information about a specific operation.

        This method provides a comprehensive report about an operation including
        its description, signature details, and metadata.

        Args:
            operation_spec (str): The operation specification in format 'tool_name.operation_name'.

        Returns:
            Dict[str, Any]: A dictionary containing complete operation information including:
                          - tool: Tool name
                          - operation: Operation name
                          - description: Operation documentation
                          - signature: Detailed signature information
                          - available: Whether the operation is available

        Raises:
            ValueError: If the operation specification is invalid or the tool/operation does not exist.
        """
        # Validate operation specification format
        if "." not in operation_spec:
            raise ValueError(f"Invalid operation specification: {operation_spec}, expected 'tool_name.operation_name' format")

        # Parse tool and operation names
        tool_name, operation_name = operation_spec.split(".", 1)

        # Validate tool exists
        if not self.tool_discovery.is_tool_available(tool_name):
            raise ValueError(f"Tool '{tool_name}' does not exist")

        # Validate operation exists
        if not self.tool_discovery.is_operation_available(tool_name, operation_name):
            raise ValueError(f"Operation '{operation_name}' not found in tool '{tool_name}'")

        # Get operation documentation
        description = self._get_operation_doc(tool_name, operation_name)

        # Get operation signature
        signature = self._analyze_operation_signature(tool_name, operation_name)

        # Build complete operation information
        operation_info = {
            "tool": tool_name,
            "operation": operation_name,
            "description": description,
            "signature": signature,
            "available": True,
            "spec": operation_spec
        }

        return operation_info

    def get_operation_signature(self, tool_name: str, operation_name: str) -> Dict[str, Any]:
        """
        Get signature information for a specific operation.

        This is a public interface method for retrieving operation signature details.

        Args:
            tool_name (str): Name of the tool containing the operation.
            operation_name (str): Name of the operation.

        Returns:
            Dict[str, Any]: Dictionary containing signature information.

        Raises:
            ValueError: If the tool or operation does not exist.
        """
        # Validate inputs
        if not self.tool_discovery.is_tool_available(tool_name):
            raise ValueError(f"Tool '{tool_name}' does not exist")

        if not self.tool_discovery.is_operation_available(tool_name, operation_name):
            raise ValueError(f"Operation '{operation_name}' not found in tool '{tool_name}'")

        # Return signature information
        return self._analyze_operation_signature(tool_name, operation_name)

    def validate_operation_params(self, tool_name: str, operation_name: str, params: Dict[str, Any]) -> List[str]:
        """
        Validate parameters for a tool operation against its signature requirements.

        This method checks if the provided parameters match the operation's signature,
        including required parameters, unknown parameters, and basic type validation.

        Args:
            tool_name (str): Name of the tool containing the operation.
            operation_name (str): Name of the operation.
            params (Dict[str, Any]): Parameters to validate against the operation signature.

        Returns:
            List[str]: List of validation error messages. Empty list if validation passes.
        """
        errors = []

        try:
            # Get operation signature
            signature = self.get_operation_signature(tool_name, operation_name)
            signature_params = signature["parameters"]

            # Check for missing required parameters
            required_params = {name: info for name, info in signature_params.items() if info["required"]}
            for param_name in required_params:
                if param_name not in params:
                    errors.append(f"Missing required parameter: {param_name}")

            # Check for unknown parameters
            valid_param_names = set(signature_params.keys())
            for param_name in params:
                if param_name not in valid_param_names:
                    errors.append(f"Unknown parameter: {param_name}")

            # Additional validation could be added here:
            # - Type checking against annotations
            # - Value range validation
            # - Custom validation rules

        except Exception as e:
            errors.append(f"Error validating parameters: {e}")

        return errors

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
        if not self.tool_discovery.is_tool_available(tool_name):
            raise ValueError(f"Tool '{tool_name}' does not exist")

        operations = self.tool_discovery.get_available_operations(tool_name)
        operations_info = {}

        for operation_name in operations:
            try:
                operation_spec = f"{tool_name}.{operation_name}"
                operations_info[operation_name] = self.get_operation_info(operation_spec)
            except Exception as e:
                self.logger.warning(f"Error getting info for operation {tool_name}.{operation_name}: {e}")
                operations_info[operation_name] = {
                    "tool": tool_name,
                    "operation": operation_name,
                    "description": "Error retrieving information",
                    "signature": {},
                    "available": False,
                    "error": str(e)
                }

        return operations_info

    def clear_cache(self) -> None:
        """
        Clear all cached information to force fresh inspection on next access.

        This method clears all internal caches including tool instances,
        operation documentation, and signature information.
        """
        self.logger.info("Clearing tool inspector caches...")

        self._tools_cache.clear()
        self._operation_docs_cache.clear()
        self._operation_signature_cache.clear()

        self.logger.info("Tool inspector caches cleared")

    def get_cache_stats(self) -> Dict[str, int]:
        """
        Get statistics about cached information.

        Returns:
            Dict[str, int]: Dictionary containing cache statistics.
        """
        return {
            "cached_tools": len(self._tools_cache),
            "cached_docs": len(self._operation_docs_cache),
            "cached_signatures": len(self._operation_signature_cache)
        }
