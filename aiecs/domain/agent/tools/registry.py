"""
Skill Script Registry

Thread-safe registry for managing tools created from skill scripts.
Separate from the global TOOL_REGISTRY in aiecs/tools which manages
BaseTool instances for the tool execution framework.
"""

import logging
import threading
from typing import Dict, List, Optional

from .models import Tool

logger = logging.getLogger(__name__)


class SkillScriptRegistryError(Exception):
    """Raised when registry operations fail."""
    pass


class SkillScriptRegistry:
    """
    Thread-safe registry for tools created from skill scripts.
    
    This registry manages lightweight Tool instances that wrap skill scripts,
    separate from the global TOOL_REGISTRY which manages BaseTool instances.
    
    Key differences from aiecs/tools TOOL_REGISTRY:
    1. Manages Tool dataclass instances (not BaseTool classes)
    2. Tools are registered at runtime from skills (not via decorators)
    3. Thread-safe instance registry (not a global dict)
    4. Designed for skill script integration
    
    Usage:
        registry = SkillScriptRegistry()
        
        # Register a tool from a skill script
        tool = Tool(
            name="validate-python",
            description="Validate Python syntax",
            execute=validate_func,
            source="python-skill"
        )
        registry.register_tool(tool)
        
        # Get tool by name
        tool = registry.get_tool("validate-python")
        
        # List tools by tag or source
        tools = registry.list_tools(tags=["python"])
        tools = registry.list_tools(source="python-skill")
    
    Attributes:
        _tools: Internal tool storage
        _lock: Threading lock for thread-safe access
    """
    
    def __init__(self):
        """Initialize an empty registry."""
        self._tools: Dict[str, Tool] = {}
        self._lock = threading.RLock()
    
    def register_tool(self, tool: Tool, replace: bool = False) -> None:
        """
        Register a tool in the registry.
        
        Args:
            tool: Tool to register
            replace: If True, replace existing tool with same name
            
        Raises:
            SkillScriptRegistryError: If tool with same name exists and replace=False
        """
        with self._lock:
            if tool.name in self._tools and not replace:
                raise SkillScriptRegistryError(
                    f"Tool '{tool.name}' already registered. Use replace=True to overwrite."
                )
            self._tools[tool.name] = tool
            logger.debug(f"Registered tool: {tool.name}")
    
    def unregister_tool(self, name: str) -> bool:
        """
        Unregister a tool from the registry.
        
        Args:
            name: Tool name to unregister
            
        Returns:
            True if tool was removed, False if it didn't exist
        """
        with self._lock:
            if name in self._tools:
                del self._tools[name]
                logger.debug(f"Unregistered tool: {name}")
                return True
            return False
    
    def get_tool(self, name: str) -> Optional[Tool]:
        """
        Get a tool by name.
        
        Args:
            name: Tool name
            
        Returns:
            Tool if found, None otherwise
        """
        with self._lock:
            return self._tools.get(name)
    
    def has_tool(self, name: str) -> bool:
        """
        Check if a tool exists in the registry.
        
        Args:
            name: Tool name
            
        Returns:
            True if tool exists, False otherwise
        """
        with self._lock:
            return name in self._tools
    
    def list_tools(
        self,
        tags: Optional[List[str]] = None,
        source: Optional[str] = None
    ) -> List[Tool]:
        """
        List tools with optional filtering.
        
        Args:
            tags: Filter by tags (any match)
            source: Filter by source identifier
            
        Returns:
            List of matching tools
        """
        with self._lock:
            tools = list(self._tools.values())
            
            if tags:
                tools = [
                    t for t in tools
                    if t.tags and any(tag in t.tags for tag in tags)
                ]
            
            if source:
                tools = [t for t in tools if t.source == source]
            
            return tools
    
    def list_tool_names(self) -> List[str]:
        """
        List all registered tool names.

        Returns:
            List of tool names
        """
        with self._lock:
            return list(self._tools.keys())

    def get_all_tools(self) -> Dict[str, Tool]:
        """
        Get a copy of all registered tools.

        Returns:
            Dictionary of tool name to Tool
        """
        with self._lock:
            return dict(self._tools)

    def get_tools_by_source(self, source: str) -> List[Tool]:
        """
        Get all tools from a specific source (e.g., skill name).

        Args:
            source: Source identifier

        Returns:
            List of tools from that source
        """
        return self.list_tools(source=source)

    def tool_count(self) -> int:
        """
        Get the number of registered tools.

        Returns:
            Number of tools
        """
        with self._lock:
            return len(self._tools)

    def clear(self) -> int:
        """
        Remove all tools from the registry.

        Returns:
            Number of tools removed
        """
        with self._lock:
            count = len(self._tools)
            self._tools.clear()
            logger.debug(f"Cleared {count} tools from registry")
            return count

    def unregister_by_source(self, source: str) -> int:
        """
        Unregister all tools from a specific source.

        Useful when detaching a skill to clean up its tools.

        Args:
            source: Source identifier

        Returns:
            Number of tools removed
        """
        with self._lock:
            to_remove = [
                name for name, tool in self._tools.items()
                if tool.source == source
            ]
            for name in to_remove:
                del self._tools[name]
            if to_remove:
                logger.debug(f"Unregistered {len(to_remove)} tools from source: {source}")
            return len(to_remove)

