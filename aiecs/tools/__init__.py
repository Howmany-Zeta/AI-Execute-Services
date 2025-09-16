# python-middleware/app/tools/__init__.py

import importlib
import inspect
import logging
import os
import pkgutil
from typing import Any, Dict, List, Optional, Type

from aiecs.tools.base_tool import BaseTool

logger = logging.getLogger(__name__)

# 全局工具注册表
TOOL_REGISTRY = {}
TOOL_CLASSES = {}
TOOL_CONFIGS = {}

def register_tool(name):
    """
    装饰器，用于注册工具类

    Args:
        name: 工具名称

    Returns:
        装饰后的类
    """
    def wrapper(cls):
        # 存储工具类，但不立即实例化
        TOOL_CLASSES[name] = cls
        # 兼容旧版本：如果类继承自BaseTool，则不立即实例化
        if not issubclass(cls, BaseTool):
            TOOL_REGISTRY[name] = cls()
        return cls
    return wrapper

def get_tool(name):
    """
    获取工具实例

    Args:
        name: 工具名称

    Returns:
        工具实例

    Raises:
        ValueError: 如果工具未注册
    """
    if name not in TOOL_REGISTRY and name in TOOL_CLASSES:
        # 延迟实例化BaseTool子类
        tool_class = TOOL_CLASSES[name]
        config = TOOL_CONFIGS.get(name, {})
        TOOL_REGISTRY[name] = tool_class(config)

    if name not in TOOL_REGISTRY:
        raise ValueError(f"Tool '{name}' is not registered")

    return TOOL_REGISTRY[name]

def list_tools():
    """
    列出所有已注册的工具

    Returns:
        工具信息字典列表
    """
    tools = []
    all_tool_names = list(set(list(TOOL_REGISTRY.keys()) + list(TOOL_CLASSES.keys())))
    
    for tool_name in all_tool_names:
        try:
            # 优先使用已有实例的信息
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
                # 从类定义获取信息，但不实例化
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
            # 提供基本信息
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
    发现并注册包中的所有工具

    Args:
        package_path: 要搜索的包路径
    """
    package = importlib.import_module(package_path)
    package_dir = os.path.dirname(package.__file__)

    for _, module_name, is_pkg in pkgutil.iter_modules([package_dir]):
        if is_pkg:
            # 递归搜索子包中的工具
            discover_tools(f"{package_path}.{module_name}")
        else:
            # 导入模块
            try:
                importlib.import_module(f"{package_path}.{module_name}")
            except Exception as e:
                logger.error(f"Error importing module {module_name}: {e}")

# 导入基础工具类供继承使用
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
    
    known_tools = [
        ("chart_tool", "Chart and visualization operations"),
        ("classfire_tool", "Text classification and keyword extraction"),
        ("image_tool", "Image processing and OCR operations"),
        ("office_tool", "Office document processing"),
        ("pandas_tool", "Data analysis and manipulation"), 
        ("report_tool", "Report generation and formatting"),
        ("research_tool", "Research and information gathering"),
        ("scraper_tool", "Web scraping and data extraction"),
        ("search_api", "Search API integration"),
        ("stats_tool", "Statistical analysis and computation")
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
