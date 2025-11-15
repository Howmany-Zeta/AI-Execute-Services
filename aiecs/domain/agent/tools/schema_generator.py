"""
Tool Schema Generator

Generate OpenAI-style function schemas from AIECS tools.
"""

import inspect
import logging
from typing import Dict, Any, List, Optional
from aiecs.tools import get_tool

logger = logging.getLogger(__name__)


class ToolSchemaGenerator:
    """
    Generates OpenAI-style function calling schemas from AIECS tools.

    Example:
        generator = ToolSchemaGenerator()
        schema = generator.generate_schema("search", "search_web")
    """

    @staticmethod
    def generate_schema(
        tool_name: str,
        operation: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate OpenAI function schema for a tool operation.

        Args:
            tool_name: Tool name
            operation: Optional operation name
            description: Optional custom description

        Returns:
            OpenAI function schema dictionary
        """
        try:
            tool = get_tool(tool_name)
        except Exception as e:
            logger.error(f"Failed to get tool {tool_name}: {e}")
            raise

        # Generate function name
        if operation:
            function_name = f"{tool_name}_{operation}"
        else:
            function_name = tool_name

        # Get operation method if specified
        if operation:
            if not hasattr(tool, operation):
                raise ValueError(f"Tool {tool_name} has no operation '{operation}'")
            method = getattr(tool, operation)
        else:
            # Default to 'run' method
            method = getattr(tool, "run", None)
            if method is None:
                raise ValueError(f"Tool {tool_name} has no 'run' method")

        # Extract parameters
        parameters = ToolSchemaGenerator._extract_parameters(method)

        # Build schema
        schema = {
            "name": function_name,
            "description": description or f"{tool_name} tool",
            "parameters": {
                "type": "object",
                "properties": parameters,
                "required": ToolSchemaGenerator._get_required_params(method),
            },
        }

        return schema

    @staticmethod
    def _extract_parameters(method) -> Dict[str, Dict[str, Any]]:
        """Extract parameter schemas from method."""
        sig = inspect.signature(method)
        parameters = {}

        for param_name, param in sig.parameters.items():
            # Skip 'self' and 'op' parameters
            if param_name in ["self", "op", "cls"]:
                continue

            param_schema = ToolSchemaGenerator._param_to_schema(param_name, param)
            if param_schema:
                parameters[param_name] = param_schema

        return parameters

    @staticmethod
    def _param_to_schema(param_name: str, param: inspect.Parameter) -> Optional[Dict[str, Any]]:
        """Convert parameter to JSON schema."""
        schema: Dict[str, Any] = {}

        # Try to infer type from annotation
        if param.annotation != inspect.Parameter.empty:
            schema.update(ToolSchemaGenerator._type_to_schema(param.annotation))

        # Add default if present
        if param.default != inspect.Parameter.empty:
            schema["default"] = param.default

        # If no type info, default to string
        if "type" not in schema:
            schema["type"] = "string"

        return schema

    @staticmethod
    def _type_to_schema(type_hint) -> Dict[str, Any]:
        """Convert Python type hint to JSON schema type."""
        # Handle string annotations
        if isinstance(type_hint, str):
            if type_hint == "str":
                return {"type": "string"}
            elif type_hint == "int":
                return {"type": "integer"}
            elif type_hint == "float":
                return {"type": "number"}
            elif type_hint == "bool":
                return {"type": "boolean"}
            elif type_hint.startswith("List"):
                return {"type": "array"}
            elif type_hint.startswith("Dict"):
                return {"type": "object"}
            else:
                return {"type": "string"}

        # Handle actual types
        if type_hint == str:
            return {"type": "string"}
        elif type_hint == int:
            return {"type": "integer"}
        elif type_hint == float:
            return {"type": "number"}
        elif type_hint == bool:
            return {"type": "boolean"}
        elif hasattr(type_hint, "__origin__"):
            # Generic types (List, Dict, etc.)
            origin = type_hint.__origin__
            if origin == list:
                return {"type": "array"}
            elif origin == dict:
                return {"type": "object"}
            else:
                return {"type": "string"}
        else:
            return {"type": "string"}

    @staticmethod
    def _get_required_params(method) -> List[str]:
        """Get list of required parameter names."""
        sig = inspect.signature(method)
        required = []

        for param_name, param in sig.parameters.items():
            # Skip 'self' and 'op' parameters
            if param_name in ["self", "op", "cls"]:
                continue

            # Required if no default value
            if param.default == inspect.Parameter.empty:
                required.append(param_name)

        return required

    @staticmethod
    def generate_schemas_for_tools(
        tool_names: List[str],
        operations: Optional[Dict[str, List[str]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Generate schemas for multiple tools.

        Args:
            tool_names: List of tool names
            operations: Optional dict mapping tool names to operations

        Returns:
            List of function schemas
        """
        schemas = []
        operations = operations or {}

        for tool_name in tool_names:
            tool_ops = operations.get(tool_name, [None])

            for op in tool_ops:
                try:
                    schema = ToolSchemaGenerator.generate_schema(tool_name, op)
                    schemas.append(schema)
                except Exception as e:
                    logger.warning(f"Failed to generate schema for {tool_name}.{op}: {e}")

        return schemas


def generate_tool_schema(
    tool_name: str,
    operation: Optional[str] = None,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Convenience function to generate tool schema.

    Args:
        tool_name: Tool name
        operation: Optional operation name
        description: Optional custom description

    Returns:
        OpenAI function schema dictionary
    """
    return ToolSchemaGenerator.generate_schema(tool_name, operation, description)
