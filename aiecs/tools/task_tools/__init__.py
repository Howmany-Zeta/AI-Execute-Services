# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
# python-middleware/app/tools/task_tools/__init__.py

"""
Task Tools Module

Retained built-in task tools (temporary; pending MCP migration):
- image_tool: Image processing and manipulation operations
- research_tool: Research and information gathering operations

Core web search lives in the standalone package ``aiecs.tools.search_tool``.

.. deprecated:: 2026-07-01
    Built-in task tools in ``aiecs.tools.task_tools`` are being migrated to MCP server
    services and will be removed on 2026-07-01. Importing this package emits a
    :class:`DeprecationWarning`; please migrate to the corresponding MCP server tools.

Note:
- Legacy API source tools removed in AIECS 2.0.0 (fork or custom BaseTool)
- search_tool is a standalone package at aiecs.tools.search_tool
- chart/classfire/office/pandas/report/stats tools removed in AIECS 2.1.0 (slim)
- Legacy scraper tools removed in AIECS 2.0.0 (fork or custom BaseTool)
"""

from aiecs.tools._builtin_tool_deprecation import warn_builtin_tool_deprecated

warn_builtin_tool_deprecated("task_tools")

# Define available tools for lazy loading
_AVAILABLE_TOOLS = [
    "image_tool",
    "research_tool",
]

# Track which tools have been loaded
_LOADED_TOOLS = set()


def _lazy_load_tool(tool_name: str):
    """Lazy load a specific tool module"""
    if tool_name in _LOADED_TOOLS:
        return

    try:
        if tool_name == "image_tool":
            pass
        elif tool_name == "research_tool":
            pass

        _LOADED_TOOLS.add(tool_name)

    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to load tool {tool_name}: {e}")


def load_all_tools():
    """Load all available tools (for backward compatibility)"""
    for tool_name in _AVAILABLE_TOOLS:
        _lazy_load_tool(tool_name)


# Export the tool modules for external access
__all__ = _AVAILABLE_TOOLS + ["load_all_tools", "_lazy_load_tool"]
