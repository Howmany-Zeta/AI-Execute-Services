# python-middleware/app/tools/__init__.py

import importlib
import inspect
import logging
import os
import pkgutil
from typing import Any, Dict, List, Optional, Type

from aiecs.tools.base_tool import BaseTool

logger = logging.getLogger(__name__)

# Global tool registry
TOOL_REGISTRY = {}
TOOL_CLASSES = {}
TOOL_CONFIGS = {}

def register_tool(name):
    """
    Decorator for registering tool classes

    Args:
        name: Tool name

    Returns:
        Decorated class
    """
    def wrapper(cls):
        # Store tool class but don't instantiate immediately
        TOOL_CLASSES[name] = cls
        # Backward compatibility: if class inherits from BaseTool, don't instantiate immediately
        if not issubclass(cls, BaseTool):
            TOOL_REGISTRY[name] = cls()
        return cls
    return wrapper

def get_tool(name):
    """
    Get tool instance

    Args:
        name: Tool name

    Returns:
        Tool instance

    Raises:
        ValueError: If tool is not registered
    """
    # Check if placeholder needs to be replaced or lazy instantiation is needed
    if name in TOOL_CLASSES:
        # If TOOL_REGISTRY contains placeholder or doesn't exist, instantiate real tool class
        current_tool = TOOL_REGISTRY.get(name)
        is_placeholder = getattr(current_tool, 'is_placeholder', False)

        if current_tool is None or is_placeholder:
            # Lazy instantiation of BaseTool subclasses, replace placeholder
            tool_class = TOOL_CLASSES[name]
            config = TOOL_CONFIGS.get(name, {})
            TOOL_REGISTRY[name] = tool_class(config)
            logger.debug(f"Instantiated tool '{name}' from class {tool_class.__name__}")

    if name not in TOOL_REGISTRY:
        raise ValueError(f"Tool '{name}' is not registered")

    return TOOL_REGISTRY[name]

def list_tools():
    """
    List all registered tools

    Returns:
        List of tool information dictionaries
    """
    tools = []
    all_tool_names = list(set(list(TOOL_REGISTRY.keys()) + list(TOOL_CLASSES.keys())))
    
    for tool_name in all_tool_names:
        try:
            # Prefer using information from existing instances
            if tool_name in TOOL_REGISTRY:
                tool_instance = TOOL_REGISTRY[tool_name]
                tool_info = {
                    "name": tool_name,
                    "description": getattr(tool_instance, 'description', f'{tool_name} tool'),
                    "category": getattr(tool_instance, 'category', 'general'),
                    "class_name": tool_instance.__class__.__name__,
                    "module": tool_instance.__class__.__module__,
                    "status": "loaded"
                }
            elif tool_name in TOOL_CLASSES:
                # Get information from class definition but don't instantiate
                tool_class = TOOL_CLASSES[tool_name]
                tool_info = {
                    "name": tool_name,
                    "description": getattr(tool_class, 'description', f'{tool_name} tool'),
                    "category": getattr(tool_class, 'category', 'general'),
                    "class_name": tool_class.__name__,
                    "module": tool_class.__module__,
                    "status": "available"
                }
            else:
                continue
            
            tools.append(tool_info)
            
        except Exception as e:
            logger.warning(f"Failed to get info for tool {tool_name}: {e}")
            # Provide basic information
            tools.append({
                "name": tool_name,
                "description": f"{tool_name} (info unavailable)",
                "category": "unknown",
                "class_name": "Unknown",
                "module": "unknown",
                "status": "error"
            })
    
    return tools

def discover_tools(package_path: str = "aiecs.tools"):
    """
    Discover and register all tools in the package

    Args:
        package_path: Package path to search
    """
    package = importlib.import_module(package_path)
    package_dir = os.path.dirname(package.__file__)

    for _, module_name, is_pkg in pkgutil.iter_modules([package_dir]):
        if is_pkg:
            # Recursively search for tools in subpackages
            discover_tools(f"{package_path}.{module_name}")
        else:
            # Import module
            try:
                importlib.import_module(f"{package_path}.{module_name}")
            except Exception as e:
                logger.error(f"Error importing module {module_name}: {e}")

# Import base tool class for inheritance
from aiecs.tools.base_tool import BaseTool

# Lazy loading strategy: don't import all tools at package init
# Tools will be loaded on-demand when requested

def _ensure_task_tools_available():
    """Ensure task_tools module is available for lazy loading"""
    try:
        from . import task_tools
        return True
    except ImportError as e:
        logger.error(f"Failed to import task_tools: {e}")
        return False

def _register_known_tools():
    """Register known tools without importing heavy dependencies"""
    # Pre-register tool classes for discovery without importing modules
    # This allows list_tools() to work before actual tool loading
    # 
    # NOTE: Tool names must match the names used in @register_tool decorators:
    # - chart (not chart_tool)
    # - classifier (not classfire_tool) 
    # - image (not image_tool)
    # - office (not office_tool)
    # - pandas (not pandas_tool)
    # - report (not report_tool)
    # - research (not research_tool)
    # - scraper (not scraper_tool)
    # - search_api (same)
    # - stats (not stats_tool)
    
    known_tools = [
        ("chart", "Chart and visualization operations"),
        ("classifier", "Text classification and keyword extraction"),
        ("image", "Image processing and OCR operations"),
        ("office", "Office document processing"),
        ("pandas", "Data analysis and manipulation"), 
        ("report", "Report generation and formatting"),
        ("research", "Research and information gathering"),
        ("scraper", "Web scraping and data extraction"),
        ("search_api", "Search API integration"),
        ("stats", "Statistical analysis and computation")
    ]
    
    # Register as placeholder until actually loaded
    for tool_name, description in known_tools:
        if tool_name not in TOOL_REGISTRY and tool_name not in TOOL_CLASSES:
            # Create a placeholder class for discovery
            class ToolPlaceholder:
                def __init__(self, name, desc):
                    self.name = name
                    self.description = desc
                    self.category = "task"
                    self.is_placeholder = True
            
            TOOL_REGISTRY[tool_name] = ToolPlaceholder(tool_name, description)

# Register known tools for discovery
_register_known_tools()

try:
    from . import db_api
except ImportError:
    pass

try:
    from . import vector_search
except ImportError:
    pass

# Don't auto-discover tools at import time for performance
# Tools will be discovered when explicitly requested via discover_tools() call
