"""
Automatic Schema Generation Tool

Automatically generate Pydantic Schema from method signatures and type annotations
"""

import inspect
import logging
from typing import Any, Dict, Optional, Type, get_type_hints, Callable, List
from pydantic import BaseModel, Field, create_model, ConfigDict

logger = logging.getLogger(__name__)


def _normalize_type(param_type: Type) -> Type:
    """
    Normalize types, handle unsupported types

    Map complex types like pandas.DataFrame to Any
    """
    # Get type name
    type_name = getattr(param_type, "__name__", str(param_type))

    # Check if it's a pandas type
    if "DataFrame" in type_name or "Series" in type_name:
        return Any

    return param_type


def _extract_param_description_from_docstring(docstring: str, param_name: str) -> Optional[str]:
    """
    Extract parameter description from docstring

    Supported formats:
    - Google style: Args: param_name: description
    - NumPy style: Parameters: param_name : type description
    """
    if not docstring:
        return None

    lines = docstring.split("\n")
    in_args_section = False
    current_param = None
    description_lines: List[str] = []

    for line in lines:
        stripped = line.strip()

        # Detect Args/Parameters section
        if stripped in ["Args:", "Arguments:", "Parameters:"]:
            in_args_section = True
            continue

        # Detect end
        if in_args_section and stripped in [
            "Returns:",
            "Raises:",
            "Yields:",
            "Examples:",
            "Note:",
            "Notes:",
        ]:
            break

        if in_args_section:
            # Google style: param_name: description or param_name (type):
            # description
            if ":" in stripped and not stripped.startswith(" "):
                # Save previous parameter
                if current_param == param_name and description_lines:
                    return " ".join(description_lines).strip()

                # Parse new parameter
                parts = stripped.split(":", 1)
                if len(parts) == 2:
                    # Remove possible type annotation (type)
                    param_part = parts[0].strip()
                    if "(" in param_part:
                        param_part = param_part.split("(")[0].strip()

                    current_param = param_part
                    description_lines = [parts[1].strip()]
            elif current_param and stripped:
                # Continue description
                description_lines.append(stripped)

    # Check last parameter
    if current_param == param_name and description_lines:
        return " ".join(description_lines).strip()

    return None


def generate_schema_from_method(method: Callable[..., Any], method_name: str, base_class: Type[BaseModel] = BaseModel) -> Optional[Type[BaseModel]]:
    """
    Automatically generate Pydantic Schema from method signature

    Args:
        method: Method to generate Schema for
        method_name: Method name
        base_class: Schema base class

    Returns:
        Generated Pydantic Schema class, returns None if unable to generate
    """
    try:
        # Get method signature
        sig = inspect.signature(method)

        # Get type annotations
        try:
            type_hints = get_type_hints(method)
        except Exception as e:
            logger.debug(f"Failed to get type hints for {method_name}: {e}")
            type_hints = {}

        # Get docstring
        docstring = inspect.getdoc(method) or f"Execute {method_name} operation"

        # Extract short description (first line)
        first_line = docstring.split("\n")[0].strip()
        schema_description = first_line if first_line else f"Execute {method_name} operation"

        # Build field definitions
        field_definitions = {}

        for param_name, param in sig.parameters.items():
            # Skip self parameter
            if param_name == "self":
                continue

            # Get parameter type and normalize
            param_type = type_hints.get(param_name, Any)
            param_type = _normalize_type(param_type)

            # Get default value
            has_default = param.default != inspect.Parameter.empty
            default_value = param.default if has_default else ...

            # Extract parameter description from docstring
            field_description = _extract_param_description_from_docstring(docstring, param_name)
            if not field_description:
                field_description = f"Parameter {param_name}"

            # Create Field
            if has_default:
                if default_value is None:
                    # Optional parameter
                    field_definitions[param_name] = (
                        param_type,
                        Field(default=None, description=field_description),
                    )
                else:
                    field_definitions[param_name] = (
                        param_type,
                        Field(
                            default=default_value,
                            description=field_description,
                        ),
                    )
            else:
                # Required parameter
                field_definitions[param_name] = (
                    param_type,
                    Field(description=field_description),
                )

        # If no parameters (except self), return None
        if not field_definitions:
            logger.debug(f"No parameters found for {method_name}, skipping schema generation")
            return None

        # Generate Schema class name
        schema_name = f"{method_name.title().replace('_', '')}Schema"

        # Create Schema class, allow arbitrary types
        # In Pydantic v2, create_model signature may vary - use type ignore for dynamic model creation
        schema_class = create_model(  # type: ignore[call-overload]
            schema_name,
            __base__=base_class,
            __doc__=schema_description,
            **field_definitions,
        )
        # Set model_config if base_class supports it
        if hasattr(schema_class, "model_config"):
            schema_class.model_config = ConfigDict(arbitrary_types_allowed=True)  # type: ignore[assignment]

        logger.debug(f"Generated schema {schema_name} for method {method_name}")
        return schema_class

    except Exception as e:
        logger.warning(f"Failed to generate schema for {method_name}: {e}")
        return None


def generate_schemas_for_tool(tool_class: Type) -> Dict[str, Type[BaseModel]]:
    """
    Generate Schema for all methods of a tool class

    Args:
        tool_class: Tool class

    Returns:
        Mapping from method names to Schema classes
    """
    schemas = {}

    for method_name in dir(tool_class):
        # Skip private methods and special methods
        if method_name.startswith("_"):
            continue

        # Skip base class methods
        if method_name in ["run", "run_async", "run_batch"]:
            continue

        method = getattr(tool_class, method_name)

        # Skip non-method attributes
        if not callable(method):
            continue

        # Skip classes (like Config, Schema, etc.)
        if isinstance(method, type):
            continue

        # Generate Schema
        schema = generate_schema_from_method(method, method_name)

        if schema:
            # Normalize method name (remove underscores, convert to lowercase)
            normalized_name = method_name.replace("_", "").lower()
            schemas[normalized_name] = schema
            logger.info(f"Generated schema for {method_name}")

    return schemas


# Usage example
if __name__ == "__main__":
    import sys

    sys.path.insert(0, "/home/coder1/python-middleware-dev")

    from aiecs.tools import discover_tools, TOOL_CLASSES

    # Configure logging
    logging.basicConfig(level=logging.INFO)

    # Discover tools
    discover_tools()

    # Generate Schema for PandasTool
    print("Generating Schema for PandasTool:")
    print("=" * 80)

    pandas_tool = TOOL_CLASSES["pandas"]
    schemas = generate_schemas_for_tool(pandas_tool)

    print(f"\nGenerated {len(schemas)} Schemas:\n")

    # Show first 3 examples
    for method_name, schema in list(schemas.items())[:3]:
        print(f"{schema.__name__}:")
        print(f"  Description: {schema.__doc__}")
        print("  Fields:")
        for field_name, field_info in schema.model_fields.items():
            required = "Required" if field_info.is_required() else "Optional"
            default = f" (default: {field_info.default})" if not field_info.is_required() and field_info.default is not None else ""
            print(f"    - {field_name}: {field_info.description} [{required}]{default}")
        print()
