"""
Langchain Adapter: Converts BaseTool and its sub-functions into Langchain ReAct Agent compatible tool collections

Main Features:
1. Automatically discover all operation methods of BaseTool
2. Create independent Langchain Tool for each operation
3. Maintain all original functionality features (caching, validation, security, etc.)
4. Support synchronous and asynchronous execution
"""

import inspect
import logging
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel

# Import schema generator
from aiecs.tools.schema_generator import generate_schema_from_method

try:
    from langchain.tools import BaseTool as LangchainBaseTool
    from langchain.callbacks.manager import (
        CallbackManagerForToolRun,
        AsyncCallbackManagerForToolRun,
    )

    LANGCHAIN_AVAILABLE = True
except ImportError:
    # If langchain is not installed, create simple base class for type checking
    # Use different name to avoid redefinition error
    class _LangchainBaseToolFallback:  # type: ignore[no-redef]
        pass

    LangchainBaseTool = _LangchainBaseToolFallback  # type: ignore[assignment,misc]
    CallbackManagerForToolRun = None  # type: ignore[assignment,misc]
    AsyncCallbackManagerForToolRun = None  # type: ignore[assignment,misc]
    LANGCHAIN_AVAILABLE = False

from aiecs.tools.base_tool import BaseTool
from aiecs.tools import get_tool, list_tools, TOOL_CLASSES

logger = logging.getLogger(__name__)


class LangchainToolAdapter(LangchainBaseTool):
    """
    Langchain tool adapter for single operation

    Wraps one operation method of BaseTool as an independent Langchain tool.
    Supports both tool-level operations and provider-level operations.
    """

    # Define class attributes
    name: str = ""
    description: str = ""
    base_tool_name: str = ""
    operation_name: str = ""
    operation_schema: Optional[Type[BaseModel]] = None
    is_provider_operation: bool = False
    provider_name: Optional[str] = None
    method_name: Optional[str] = None

    def __init__(
        self,
        base_tool_name: str,
        operation_name: str,
        operation_schema: Optional[Type[BaseModel]] = None,
        description: Optional[str] = None,
        is_provider_operation: bool = False,
        provider_name: Optional[str] = None,
        method_name: Optional[str] = None,
    ):
        """
        Initialize adapter

        Args:
            base_tool_name: Original tool name
            operation_name: Operation name
            operation_schema: Pydantic Schema for the operation
            description: Tool description
            is_provider_operation: Whether this is a provider-level operation
            provider_name: Provider name (for provider operations)
            method_name: Original method name (for provider operations)
        """
        # Construct tool name and description
        tool_name = f"{base_tool_name}_{operation_name}"
        tool_description = description or f"Execute {operation_name} operation from {base_tool_name} tool"

        # Initialize parent class with all required fields
        super().__init__(
            name=tool_name,
            description=tool_description,
            base_tool_name=base_tool_name,
            operation_name=operation_name,
            operation_schema=operation_schema,
            args_schema=operation_schema,
            is_provider_operation=is_provider_operation,
            provider_name=provider_name,
            method_name=method_name,
        )

    def _run(
        self,
        run_manager: Optional[CallbackManagerForToolRun] = None,
        **kwargs: Any,
    ) -> Any:
        """Execute operation synchronously"""
        try:
            # Get original tool instance
            base_tool = get_tool(self.base_tool_name)

            # Handle provider operations differently
            if self.is_provider_operation:
                # For provider operations, call the query method with provider
                # and operation
                result = base_tool.run(
                    "query",
                    provider=self.provider_name,
                    operation=self.method_name,
                    params=kwargs,
                )
            else:
                # For tool-level operations, call directly
                result = base_tool.run(self.operation_name, **kwargs)

            logger.info(f"Successfully executed {self.name} with result type: {type(result)}")
            return result

        except Exception as e:
            logger.error(f"Error executing {self.name}: {str(e)}")
            raise

    async def _arun(
        self,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
        **kwargs: Any,
    ) -> Any:
        """Execute operation asynchronously"""
        try:
            # Get original tool instance
            base_tool = get_tool(self.base_tool_name)

            # Execute asynchronous operation
            result = await base_tool.run_async(self.operation_name, **kwargs)

            logger.info(f"Successfully executed {self.name} async with result type: {type(result)}")
            return result

        except Exception as e:
            logger.error(f"Error executing {self.name} async: {str(e)}")
            raise


class ToolRegistry:
    """Tool Registry: Manages conversion from BaseTool to Langchain tools"""

    def __init__(self) -> None:
        self._langchain_tools: Dict[str, LangchainToolAdapter] = {}

    def discover_operations(self, base_tool_class: Type[BaseTool]) -> List[Dict[str, Any]]:
        """
        Discover all operation methods and Schemas of BaseTool class.

        Enhanced to support provider-level operations for tools like APISourceTool
        that expose fine-grained operations from underlying providers.

        Args:
            base_tool_class: BaseTool subclass

        Returns:
            List of operation information, including method names, Schemas, descriptions, etc.
        """
        operations = []

        # 1. Discover tool-level operations (existing logic)
        tool_operations = self._discover_tool_operations(base_tool_class)
        operations.extend(tool_operations)

        # 2. Discover provider-level operations (new logic)
        if hasattr(base_tool_class, "_discover_provider_operations"):
            try:
                provider_operations = base_tool_class._discover_provider_operations()

                # Convert provider operations to the expected format
                for provider_op in provider_operations:
                    operation_info = {
                        "name": provider_op["name"],
                        "method": None,  # Will be handled specially in create_langchain_tools
                        "schema": provider_op["schema"],
                        "description": provider_op["description"],
                        "is_async": False,
                        "is_provider_operation": True,  # Mark as provider operation
                        "provider_name": provider_op.get("provider_name"),
                        "method_name": provider_op.get("method_name"),
                    }
                    operations.append(operation_info)
                    logger.debug(f"Added provider operation: {provider_op['name']}")

                logger.info(f"Discovered {len(provider_operations)} provider operations for {base_tool_class.__name__}")

            except Exception as e:
                logger.warning(f"Error discovering provider operations for {base_tool_class.__name__}: {e}")

        return operations

    def _discover_tool_operations(self, base_tool_class: Type[BaseTool]) -> List[Dict[str, Any]]:
        """
        Discover tool-level operations (original logic extracted to separate method).

        Args:
            base_tool_class: BaseTool subclass

        Returns:
            List of tool-level operation information
        """
        operations = []

        # Get all Schema classes
        # Build a mapping from normalized names to Schema classes
        # Check both class-level and module-level schemas
        schemas = {}

        # 1. Check class-level schemas (e.g., ChartTool)
        for attr_name in dir(base_tool_class):
            attr = getattr(base_tool_class, attr_name)
            if isinstance(attr, type) and issubclass(attr, BaseModel) and attr.__name__.endswith("Schema"):
                # Normalize: remove 'Schema' suffix, convert to lowercase,
                # remove underscores
                schema_base_name = attr.__name__.replace("Schema", "")
                normalized_name = schema_base_name.replace("_", "").lower()
                schemas[normalized_name] = attr
                logger.debug(f"Found class-level schema {attr.__name__} -> normalized: {normalized_name}")

        # 2. Check module-level schemas (e.g., ImageTool)
        tool_module = inspect.getmodule(base_tool_class)
        if tool_module:
            for attr_name in dir(tool_module):
                if attr_name.startswith("_"):
                    continue
                attr = getattr(tool_module, attr_name)
                if isinstance(attr, type) and issubclass(attr, BaseModel) and attr.__name__.endswith("Schema"):
                    # Skip if already found at class level
                    schema_base_name = attr.__name__.replace("Schema", "")
                    normalized_name = schema_base_name.replace("_", "").lower()
                    if normalized_name not in schemas:
                        schemas[normalized_name] = attr
                        logger.debug(f"Found module-level schema {attr.__name__} -> normalized: {normalized_name}")

        # Get all public methods
        for method_name in dir(base_tool_class):
            if method_name.startswith("_"):
                continue

            method = getattr(base_tool_class, method_name)
            if not callable(method):
                continue

            # Skip base class methods and Schema classes themselves
            if method_name in ["run", "run_async", "run_batch"]:
                continue

            # Skip if it's a class (like Config or Schema classes)
            if isinstance(method, type):
                continue

            # Normalize method name: remove underscores and convert to
            # lowercase
            normalized_method_name = method_name.replace("_", "").lower()

            # Try to find matching schema
            matching_schema = schemas.get(normalized_method_name)

            if matching_schema:
                logger.debug(f"Matched method {method_name} with manual schema {matching_schema.__name__}")
            else:
                # Auto-generate schema if not found
                auto_schema = generate_schema_from_method(method, method_name)
                if auto_schema:
                    matching_schema = auto_schema
                    logger.debug(f"Auto-generated schema for method {method_name}: {auto_schema.__name__}")
                else:
                    logger.debug(f"No schema found or generated for method {method_name}")

            # Get method information
            operation_info = {
                "name": method_name,
                "method": method,
                "schema": matching_schema,
                "description": inspect.getdoc(method) or f"Execute {method_name} operation",
                "is_async": inspect.iscoroutinefunction(method),
                "is_provider_operation": False,  # Mark as tool-level operation
            }

            operations.append(operation_info)

        return operations

    def _extract_description(
        self,
        method,
        base_tool_name: str,
        operation_name: str,
        schema: Optional[Type[BaseModel]] = None,
    ) -> str:
        """Extract detailed description from method docstring and schema"""
        doc = inspect.getdoc(method)

        # Base description
        if doc:
            base_desc = doc.split("\n")[0].strip()
        else:
            base_desc = f"Execute {operation_name} operation"

        # Enhanced description - add specific tool functionality description
        enhanced_desc = f"{base_desc}"

        # Add specific descriptions based on tool name and operation
        if base_tool_name == "chart":
            if operation_name == "read_data":
                enhanced_desc = "Read and analyze data files in multiple formats (CSV, Excel, JSON, Parquet, etc.). Returns data structure summary, preview, and optional export functionality."
            elif operation_name == "visualize":
                enhanced_desc = (
                    "Create data visualizations including histograms, scatter plots, bar charts, line charts, "
                    "heatmaps, and pair plots. Supports customizable styling, colors, and high-resolution output."
                )
            elif operation_name == "export_data":
                enhanced_desc = "Export data to various formats (JSON, CSV, HTML, Excel, Markdown) with optional variable selection and path customization."
        elif base_tool_name == "pandas":
            enhanced_desc = f"Pandas data manipulation: {base_desc}. Supports DataFrame operations with built-in validation and error handling."
        elif base_tool_name == "stats":
            enhanced_desc = f"Statistical analysis: {base_desc}. Provides statistical tests, regression analysis, and data preprocessing capabilities."

        # Add parameter information
        if schema:
            try:
                fields_raw: Any = schema.__fields__ if hasattr(schema, "__fields__") else {}
                # Type narrowing: ensure fields is a dict
                fields: Dict[str, Any] = fields_raw if isinstance(fields_raw, dict) else {}
                if isinstance(fields, dict) and fields:
                    required_params = [name for name, field in fields.items() if field.is_required()]
                    optional_params = [name for name, field in fields.items() if not field.is_required()]

                    param_desc = ""
                    if required_params:
                        param_desc += f" Required: {', '.join(required_params)}."
                    if optional_params:
                        param_desc += f" Optional: {', '.join(optional_params)}."

                    enhanced_desc += param_desc
            except Exception:
                pass

        return enhanced_desc

    def create_langchain_tools(self, tool_name: str) -> List[LangchainToolAdapter]:
        """
        Create all Langchain adapters for specified tool

        Args:
            tool_name: Tool name

        Returns:
            List of Langchain tool adapters
        """
        if not LANGCHAIN_AVAILABLE:
            raise ImportError("langchain is not installed. Please install it to use this adapter.")

        if tool_name not in TOOL_CLASSES:
            raise ValueError(f"Tool '{tool_name}' not found in registry")

        base_tool_class = TOOL_CLASSES[tool_name]
        operations = self.discover_operations(base_tool_class)

        langchain_tools = []
        for op_info in operations:
            # Generate enhanced description
            # For provider operations, use the description directly
            if op_info.get("is_provider_operation", False):
                enhanced_description = op_info["description"]
            else:
                enhanced_description = self._extract_description(
                    op_info["method"],
                    tool_name,
                    op_info["name"],
                    op_info["schema"],
                )

            # Create adapter with provider operation support
            adapter = LangchainToolAdapter(
                base_tool_name=tool_name,
                operation_name=op_info["name"],
                operation_schema=op_info["schema"],
                description=enhanced_description,
                is_provider_operation=op_info.get("is_provider_operation", False),
                provider_name=op_info.get("provider_name"),
                method_name=op_info.get("method_name"),
            )

            langchain_tools.append(adapter)
            self._langchain_tools[adapter.name] = adapter

        logger.info(f"Created {len(langchain_tools)} Langchain tools for {tool_name}")
        return langchain_tools

    def create_all_langchain_tools(self) -> List[LangchainToolAdapter]:
        """
        Create Langchain adapters for all registered BaseTools

        Returns:
            List of all Langchain tool adapters
        """
        all_tools = []

        # list_tools() returns a list of dicts, extract tool names
        tool_infos = list_tools()
        for tool_info in tool_infos:
            tool_name = tool_info["name"]
            try:
                tools = self.create_langchain_tools(tool_name)
                all_tools.extend(tools)
            except Exception as e:
                logger.error(f"Failed to create Langchain tools for {tool_name}: {e}")

        logger.info(f"Created total {len(all_tools)} Langchain tools from {len(tool_infos)} base tools")
        return all_tools

    def get_tool(self, name: str) -> Optional[LangchainToolAdapter]:
        """Get Langchain tool with specified name"""
        return self._langchain_tools.get(name)

    def list_langchain_tools(self) -> List[str]:
        """List all Langchain tool names"""
        return list(self._langchain_tools.keys())


# Global registry instance
tool_registry = ToolRegistry()


def get_langchain_tools(
    tool_names: Optional[List[str]] = None,
) -> List[LangchainToolAdapter]:
    """
    Get Langchain tool collection

    Args:
        tool_names: List of tool names to convert, None means convert all tools

    Returns:
        List of Langchain tool adapters
    """
    if tool_names is None:
        return tool_registry.create_all_langchain_tools()

    all_tools = []
    for tool_name in tool_names:
        tools = tool_registry.create_langchain_tools(tool_name)
        all_tools.extend(tools)

    return all_tools


def create_react_agent_tools() -> List[LangchainToolAdapter]:
    """
    Create complete tool collection for ReAct Agent

    Returns:
        List of adapted Langchain tools
    """
    return get_langchain_tools()


def create_tool_calling_agent_tools() -> List[LangchainToolAdapter]:
    """
    Create complete tool collection for Tool Calling Agent

    Returns:
        List of adapted Langchain tools optimized for tool calling
    """
    return get_langchain_tools()


# Compatibility check functionality


def check_langchain_compatibility() -> Dict[str, Any]:
    """
    Check compatibility between current environment and Langchain

    Returns:
        Compatibility check results
    """
    result: Dict[str, Any] = {
        "langchain_available": LANGCHAIN_AVAILABLE,
        "total_base_tools": len(list_tools()),
        "compatible_tools": [],
        "incompatible_tools": [],
        "total_operations": 0,
    }

    if not LANGCHAIN_AVAILABLE:
        result["error"] = "Langchain not installed"
        return result

    for tool_name in list_tools():
        try:
            tool_class = TOOL_CLASSES[tool_name]
            operations = tool_registry.discover_operations(tool_class)

            result["compatible_tools"].append(
                {
                    "name": tool_name,
                    "operations_count": len(operations),
                    "operations": [op["name"] for op in operations],
                }
            )
            total_ops = result.get("total_operations", 0)
            if isinstance(total_ops, (int, float)):
                result["total_operations"] = total_ops + len(operations)

        except Exception as e:
            result["incompatible_tools"].append({"name": tool_name, "error": str(e)})

    return result
