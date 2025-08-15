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
- search_api: Search API integration operations
- stats_tool: Statistical analysis and computation operations
"""

# Import all task tools to ensure they are registered
import os

from . import chart_tool
from . import classfire_tool
from . import image_tool

# Conditionally import office_tool to avoid PyO3 conflicts in testing
if not os.getenv('SKIP_OFFICE_TOOL', '').lower() in ('true', '1', 'yes'):
    from . import office_tool

from . import pandas_tool
from . import report_tool
from . import research_tool
from . import scraper_tool
from . import search_api
from . import stats_tool

# Export the tool modules for external access
__all__ = [
    'chart_tool',
    'classfire_tool',
    'image_tool',
    'pandas_tool',
    'report_tool',
    'research_tool',
    'scraper_tool',
    'search_api',
    'stats_tool'
]

# Conditionally add office_tool to exports
if not os.getenv('SKIP_OFFICE_TOOL', '').lower() in ('true', '1', 'yes'):
    __all__.append('office_tool')
