"""
Tool Layer for Multi-Task Service

This module provides tool management capabilities for the multi-task service,
including tool discovery, inspection, execution, and unified management.

The tool layer is organized into four main components:
- ToolDiscovery: Discovers available tools and their operations
- ToolInspector: Provides detailed information about tools and operations
- ToolExecutor: Executes tool operations with comprehensive error handling
- ToolManager: Unified interface that coordinates all tool functionality

Key Design Decisions:
1. Separation of concerns - each component has a single responsibility
2. No tool registration - tools are already registered in the main program
3. Focus on tool discovery, inspection, execution, and management
4. Leverage existing tool registry for core functionality
5. Maintain backward compatibility with original MultiTaskTools interface

Architecture:
- discovery/: Tool and operation discovery functionality
- inspector/: Tool and operation inspection and validation
- executor/: Tool operation execution (sync and async)
- manager/: Unified interface coordinating all components
"""

# Import all components
from .discovery.tool_discovery import ToolDiscovery
from .inspector.tool_inspector import ToolInspector
from .executor.tool_executor import ToolExecutor
from .tool_manager import ToolManager

# For backward compatibility, also import the original class
# This allows existing code to continue working while transitioning to new architecture
try:
    from .tools import MultiTaskTools
except ImportError:
    # If the original tools.py file has been removed or renamed
    MultiTaskTools = None

__all__ = [
    # New architecture components
    'ToolDiscovery',
    'ToolInspector',
    'ToolExecutor',
    'ToolManager',

    # Backward compatibility (if available)
    'MultiTaskTools'
]

# Remove None values from __all__ if MultiTaskTools is not available
__all__ = [item for item in __all__ if globals().get(item) is not None]

# Default export for convenience - ToolManager provides the unified interface
# This allows users to simply import ToolManager for all tool functionality
default_manager = None

def get_tool_manager() -> ToolManager:
    """
    Get a singleton instance of ToolManager.

    Returns:
        ToolManager: Singleton instance of the tool manager.
    """
    global default_manager
    if default_manager is None:
        default_manager = ToolManager()
    return default_manager

def create_tool_manager() -> ToolManager:
    """
    Create a new instance of ToolManager.

    Returns:
        ToolManager: New instance of the tool manager.
    """
    return ToolManager()

# Convenience functions for direct access to functionality
def get_available_tools():
    """Get list of available tools using the default manager."""
    return get_tool_manager().get_available_tools()

def get_available_operations(tool_name=None):
    """Get available operations using the default manager."""
    return get_tool_manager().get_available_operations(tool_name)

def execute_tool_sync(tool_name: str, operation_name: str, **params):
    """Execute a tool operation synchronously using the default manager."""
    return get_tool_manager().execute_tool_sync(tool_name, operation_name, **params)

async def execute_tool_async(tool_name: str, operation_name: str, **params):
    """Execute a tool operation asynchronously using the default manager."""
    return await get_tool_manager().execute_tool(tool_name, operation_name, **params)

def get_operation_info(operation_spec: str):
    """Get operation information using the default manager."""
    return get_tool_manager().get_operation_info(operation_spec)

def validate_operation_params(tool_name: str, operation_name: str, params: dict):
    """Validate operation parameters using the default manager."""
    return get_tool_manager().validate_operation_params(tool_name, operation_name, params)
