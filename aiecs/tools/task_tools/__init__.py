# python-middleware/app/tools/task_tools/__init__.py

"""
Task Tools Module

This module contains specialized tools for various task-oriented operations:
- chart_tool: Chart and visualization operations
- classfire_tool: Classification and categorization operations
- image_tool: Image processing and manipulation operations
- office_tool: Office document processing operations
- pandas_tool: Data analysis and manipulation operations
- report_tool: Report generation and formatting operations
- research_tool: Research and information gathering operations
- scraper_tool: Web scraping and data extraction operations
- stats_tool: Statistical analysis and computation operations

Note:
- apisource_tool is now a standalone package at aiecs.tools.apisource
- search_tool is now a standalone package at aiecs.tools.search_tool
"""

# Lazy import all task tools to avoid heavy dependencies at import time
import os

# Define available tools for lazy loading
_AVAILABLE_TOOLS = [
    'chart_tool',
    'classfire_tool',
    'image_tool',
    'pandas_tool',
    'report_tool',
    'research_tool',
    'scraper_tool',
    'stats_tool'
]

# Add office_tool conditionally
if not os.getenv('SKIP_OFFICE_TOOL', '').lower() in ('true', '1', 'yes'):
    _AVAILABLE_TOOLS.append('office_tool')

# Track which tools have been loaded
_LOADED_TOOLS = set()

def _lazy_load_tool(tool_name: str):
    """Lazy load a specific tool module"""
    if tool_name in _LOADED_TOOLS:
        return

    try:
        if tool_name == 'chart_tool':
            from . import chart_tool
        elif tool_name == 'classfire_tool':
            from . import classfire_tool
        elif tool_name == 'image_tool':
            from . import image_tool
        elif tool_name == 'office_tool':
            from . import office_tool
        elif tool_name == 'pandas_tool':
            from . import pandas_tool
        elif tool_name == 'report_tool':
            from . import report_tool
        elif tool_name == 'research_tool':
            from . import research_tool
        elif tool_name == 'scraper_tool':
            from . import scraper_tool
        elif tool_name == 'stats_tool':
            from . import stats_tool

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
__all__ = _AVAILABLE_TOOLS + ['load_all_tools', '_lazy_load_tool']
