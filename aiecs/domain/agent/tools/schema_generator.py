"""
Tool Schema Generator

Generate OpenAI-style function schemas from AIECS tools.
"""

import inspect
import logging
from typing import Dict, Any, List, Optional, Type, Tuple
from pydantic import BaseModel
from aiecs.tools import get_tool, BaseTool

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

        This method prioritizes Pydantic schemas from BaseTool for accurate
        parameter descriptions and types.

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

        # Try to get Pydantic schema from BaseTool first
        schema_class = None
        if isinstance(tool, BaseTool) and hasattr(tool, "_schemas"):
            schema_class = tool._schemas.get(operation)

        # Extract parameters - prefer Pydantic schema if available
        if schema_class:
            parameters, required = ToolSchemaGenerator._extract_from_pydantic_schema(schema_class)
            # Get description from schema class docstring or method docstring
            if not description:
                description = ToolSchemaGenerator._get_description(schema_class, method)
        else:
            # Fallback to method signature inspection
            parameters = ToolSchemaGenerator._extract_parameters(method)
            required = ToolSchemaGenerator._get_required_params(method)
            if not description:
                description = ToolSchemaGenerator._get_description(None, method) or f"{tool_name} tool"

        # Build schema
        schema = {
            "name": function_name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": parameters,
                "required": required,
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
    def _extract_from_pydantic_schema(schema_class: Type[BaseModel]) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
        """
        Extract parameters from Pydantic schema class.

        Args:
            schema_class: Pydantic BaseModel class

        Returns:
            Tuple of (properties dict, required fields list)
        """
        properties = {}
        required = []

        if not hasattr(schema_class, "model_fields"):
            return properties, required

        # Import PydanticUndefined for v2 compatibility
        try:
            from pydantic_core import PydanticUndefined
        except ImportError:
            PydanticUndefined = type(None)  # Fallback for Pydantic v1

        for field_name, field_info in schema_class.model_fields.items():
            # Build property schema
            prop_schema: Dict[str, Any] = {}

            # Get type
            field_type = field_info.annotation
            prop_schema.update(ToolSchemaGenerator._type_to_schema(field_type))

            # Get description from Field
            if hasattr(field_info, "description") and field_info.description:
                prop_schema["description"] = field_info.description

            # Check if required using Pydantic v2 API (preferred)
            if hasattr(field_info, "is_required") and callable(field_info.is_required):
                if field_info.is_required():
                    required.append(field_name)
                elif field_info.default is not None and field_info.default is not PydanticUndefined:
                    prop_schema["default"] = field_info.default
            else:
                # Fallback for Pydantic v1
                if field_info.default is None or field_info.default == inspect.Parameter.empty:
                    required.append(field_name)
                else:
                    prop_schema["default"] = field_info.default

            properties[field_name] = prop_schema

        return properties, required

    @staticmethod
    def _get_description(schema_class: Optional[Type[BaseModel]], method) -> Optional[str]:
        """Get description from schema class docstring or method docstring."""
        if schema_class and schema_class.__doc__:
            return schema_class.__doc__.strip().split("\n")[0]
        if method and method.__doc__:
            # Extract first line of docstring
            doc_lines = method.__doc__.strip().split("\n")
            if doc_lines:
                return doc_lines[0]
        return None

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

    @staticmethod
    def generate_schemas_for_tool_instances(
        tool_instances: Dict[str, BaseTool],
        operations: Optional[Dict[str, List[str]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Generate schemas for tool instances.

        This method works directly with tool instances, which is useful
        when tools are pre-configured with state.

        Args:
            tool_instances: Dict mapping tool names to BaseTool instances
            operations: Optional dict mapping tool names to operations

        Returns:
            List of function schemas
        """
        schemas = []
        operations = operations or {}

        for tool_name, tool in tool_instances.items():
            tool_ops = operations.get(tool_name, [None])

            for op in tool_ops:
                try:
                    # Generate function name
                    if op:
                        function_name = f"{tool_name}_{op}"
                    else:
                        function_name = tool_name

                    # Get operation method
                    if op:
                        if not hasattr(tool, op):
                            logger.warning(f"Tool {tool_name} has no operation '{op}'")
                            continue
                        method = getattr(tool, op)
                    else:
                        method = getattr(tool, "run", None)
                        if method is None:
                            logger.warning(f"Tool {tool_name} has no 'run' method")
                            continue

                    # Try to get Pydantic schema from BaseTool
                    schema_class = None
                    if hasattr(tool, "_schemas"):
                        schema_class = tool._schemas.get(op)

                    # Extract parameters
                    if schema_class:
                        parameters, required = ToolSchemaGenerator._extract_from_pydantic_schema(schema_class)
                        description = ToolSchemaGenerator._get_description(schema_class, method)
                    else:
                        parameters = ToolSchemaGenerator._extract_parameters(method)
                        required = ToolSchemaGenerator._get_required_params(method)
                        description = ToolSchemaGenerator._get_description(None, method) or f"{tool_name} tool"

                    schema = {
                        "name": function_name,
                        "description": description,
                        "parameters": {
                            "type": "object",
                            "properties": parameters,
                            "required": required,
                        },
                    }
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
