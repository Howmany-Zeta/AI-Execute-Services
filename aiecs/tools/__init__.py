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
        工具名称列表
    """
    return list(set(list(TOOL_REGISTRY.keys()) + list(TOOL_CLASSES.keys())))

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

# 导入所有工具模块以确保它们被注册
# 这些导入将通过装饰器触发工具的注册

# 导入任务工具模块 - 包含所有专门的任务工具
from . import task_tools

# 尝试导入其他可能存在的工具模块
try:
    from . import rag
except ImportError:
    pass

try:
    from . import embed
except ImportError:
    pass

try:
    from . import db_api
except ImportError:
    pass

try:
    from . import vector_search
except ImportError:
    pass

# 自动发现并注册所有工具
discover_tools("aiecs.tools")
