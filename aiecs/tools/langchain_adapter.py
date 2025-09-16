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
from typing import Any, Dict, List, Optional, Type, Union, get_type_hints
from pydantic import BaseModel, Field

try:
    from langchain.tools import BaseTool as LangchainBaseTool
    from langchain.callbacks.manager import CallbackManagerForToolRun, AsyncCallbackManagerForToolRun
    LANGCHAIN_AVAILABLE = True
except ImportError:
    # If langchain is not installed, create simple base class for type checking
    class LangchainBaseTool:
        pass
    CallbackManagerForToolRun = None
    AsyncCallbackManagerForToolRun = None
    LANGCHAIN_AVAILABLE = False

from aiecs.tools.base_tool import BaseTool
from aiecs.tools import get_tool, list_tools, TOOL_CLASSES

logger = logging.getLogger(__name__)

class LangchainToolAdapter(LangchainBaseTool):
    """
    Langchain tool adapter for single operation
    
    Wraps one operation method of BaseTool as an independent Langchain tool
    """
    
    # Define class attributes
    name: str = ""
    description: str = ""
    
    def __init__(
        self, 
        base_tool_name: str,
        operation_name: str, 
        operation_schema: Optional[Type[BaseModel]] = None,
        description: Optional[str] = None
    ):
        """
        Initialize adapter
        
        Args:
            base_tool_name: Original tool name
            operation_name: Operation name
            operation_schema: Pydantic Schema for the operation
            description: Tool description
        """
        # Construct tool name and description
        self.name = f"{base_tool_name}_{operation_name}"
        self.description = description or f"Execute {operation_name} operation from {base_tool_name} tool"
        
        # Store tool information (use self.__dict__ to set directly to avoid pydantic validation)
        self.__dict__['base_tool_name'] = base_tool_name
        self.__dict__['operation_name'] = operation_name
        self.__dict__['operation_schema'] = operation_schema
        
        # Set parameter Schema
        if operation_schema:
            self.args_schema = operation_schema
        
        super().__init__()
    
    def _run(
        self, 
        run_manager: Optional[CallbackManagerForToolRun] = None, 
        **kwargs: Any
    ) -> Any:
        """Execute operation synchronously"""
        try:
            # Get original tool instance
            base_tool = get_tool(self.__dict__['base_tool_name'])
            
            # Execute operation
            result = base_tool.run(self.__dict__['operation_name'], **kwargs)
            
            logger.info(f"Successfully executed {self.name} with result type: {type(result)}")
            return result
            
        except Exception as e:
            logger.error(f"Error executing {self.name}: {str(e)}")
            raise
    
    async def _arun(
        self, 
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
        **kwargs: Any
    ) -> Any:
        """Execute operation asynchronously"""
        try:
            # Get original tool instance
            base_tool = get_tool(self.__dict__['base_tool_name'])
            
            # Execute asynchronous operation
            result = await base_tool.run_async(self.__dict__['operation_name'], **kwargs)
            
            logger.info(f"Successfully executed {self.name} async with result type: {type(result)}")
            return result
            
        except Exception as e:
            logger.error(f"Error executing {self.name} async: {str(e)}")
            raise

class ToolRegistry:
    """Tool Registry: Manages conversion from BaseTool to Langchain tools"""
    
    def __init__(self):
        self._langchain_tools: Dict[str, LangchainToolAdapter] = {}
    
    def discover_operations(self, base_tool_class: Type[BaseTool]) -> List[Dict[str, Any]]:
        """
        Discover all operation methods and Schemas of BaseTool class
        
        Args:
            base_tool_class: BaseTool subclass
            
        Returns:
            List of operation information, including method names, Schemas, descriptions, etc.
        """
        operations = []
        
        # Get all Schema classes
        schemas = {}
        for attr_name in dir(base_tool_class):
            attr = getattr(base_tool_class, attr_name)
            if isinstance(attr, type) and issubclass(attr, BaseModel) and attr.__name__.endswith('Schema'):
                op_name = attr.__name__.replace('Schema', '').lower()
                schemas[op_name] = attr
        
        # Get all public methods
        for method_name in dir(base_tool_class):
            if method_name.startswith('_'):
                continue
                
            method = getattr(base_tool_class, method_name)
            if not callable(method):
                continue
                
            # Skip base class methods
            if method_name in ['run', 'run_async', 'run_batch']:
                continue
            
            # Get method information
            operation_info = {
                'name': method_name,
                'method': method,
                'schema': schemas.get(method_name),
                'description': inspect.getdoc(method) or f"Execute {method_name} operation",
                'is_async': inspect.iscoroutinefunction(method)
            }
            
            operations.append(operation_info)
        
        return operations
    
    def _extract_description(self, method, base_tool_name: str, operation_name: str, schema: Optional[Type[BaseModel]] = None) -> str:
        """Extract detailed description from method docstring and schema"""
        doc = inspect.getdoc(method)
        
        # Base description
        if doc:
            base_desc = doc.split('\n')[0].strip()
        else:
            base_desc = f"Execute {operation_name} operation"
        
        # Enhanced description - add specific tool functionality description
        enhanced_desc = f"{base_desc}"
        
        # Add specific descriptions based on tool name and operation
        if base_tool_name == "chart":
            if operation_name == "read_data":
                enhanced_desc = "Read and analyze data files in multiple formats (CSV, Excel, JSON, Parquet, etc.). Returns data structure summary, preview, and optional export functionality."
            elif operation_name == "visualize":
                enhanced_desc = "Create data visualizations including histograms, scatter plots, bar charts, line charts, heatmaps, and pair plots. Supports customizable styling, colors, and high-resolution output."
            elif operation_name == "export_data":
                enhanced_desc = "Export data to various formats (JSON, CSV, HTML, Excel, Markdown) with optional variable selection and path customization."
        elif base_tool_name == "pandas":
            enhanced_desc = f"Pandas data manipulation: {base_desc}. Supports DataFrame operations with built-in validation and error handling."
        elif base_tool_name == "stats":
            enhanced_desc = f"Statistical analysis: {base_desc}. Provides statistical tests, regression analysis, and data preprocessing capabilities."
        
        # Add parameter information
        if schema:
            try:
                fields = schema.__fields__ if hasattr(schema, '__fields__') else {}
                if fields:
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
            enhanced_description = self._extract_description(
                op_info['method'], 
                tool_name, 
                op_info['name'], 
                op_info['schema']
            )
            
            adapter = LangchainToolAdapter(
                base_tool_name=tool_name,
                operation_name=op_info['name'],
                operation_schema=op_info['schema'],
                description=enhanced_description
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
        
        for tool_name in list_tools():
            try:
                tools = self.create_langchain_tools(tool_name)
                all_tools.extend(tools)
            except Exception as e:
                logger.error(f"Failed to create Langchain tools for {tool_name}: {e}")
        
        logger.info(f"Created total {len(all_tools)} Langchain tools from {len(list_tools())} base tools")
        return all_tools
    
    def get_tool(self, name: str) -> Optional[LangchainToolAdapter]:
        """Get Langchain tool with specified name"""
        return self._langchain_tools.get(name)
    
    def list_langchain_tools(self) -> List[str]:
        """List all Langchain tool names"""
        return list(self._langchain_tools.keys())

# Global registry instance
tool_registry = ToolRegistry()

def get_langchain_tools(tool_names: Optional[List[str]] = None) -> List[LangchainToolAdapter]:
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
    result = {
        'langchain_available': LANGCHAIN_AVAILABLE,
        'total_base_tools': len(list_tools()),
        'compatible_tools': [],
        'incompatible_tools': [],
        'total_operations': 0
    }
    
    if not LANGCHAIN_AVAILABLE:
        result['error'] = 'Langchain not installed'
        return result
    
    for tool_name in list_tools():
        try:
            tool_class = TOOL_CLASSES[tool_name]
            operations = tool_registry.discover_operations(tool_class)
            
            result['compatible_tools'].append({
                'name': tool_name,
                'operations_count': len(operations),
                'operations': [op['name'] for op in operations]
            })
            result['total_operations'] += len(operations)
            
        except Exception as e:
            result['incompatible_tools'].append({
                'name': tool_name,
                'error': str(e)
            })
    
    return result
