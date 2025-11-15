# python-middleware/aiecs/tools/docs/__init__.py

"""
Document Tools Module

This module contains specialized tools for document processing and analysis:
- document_parser_tool: Modern high-performance document parsing with AI
- ai_document_orchestrator: AI-powered document processing orchestrator
"""

# Lazy import all document tools to avoid heavy dependencies at import time
import os

# Define available document tools for lazy loading
_AVAILABLE_DOC_TOOLS = [
    "document_parser_tool",
    "ai_document_orchestrator",
    "document_writer_tool",
    "ai_document_writer_orchestrator",
    "document_creator_tool",
    "document_layout_tool",
    "content_insertion_tool",
]

# Track which tools have been loaded
_LOADED_DOC_TOOLS = set()


def _lazy_load_doc_tool(tool_name: str):
    """Lazy load a specific document tool module"""
    if tool_name in _LOADED_DOC_TOOLS:
        return

    # Mark as loading to prevent infinite recursion
    _LOADED_DOC_TOOLS.add(tool_name)

    try:
        if tool_name == "document_parser_tool":
            from . import document_parser_tool

            globals()["document_parser_tool"] = document_parser_tool
        elif tool_name == "ai_document_orchestrator":
            from . import ai_document_orchestrator

            globals()["ai_document_orchestrator"] = ai_document_orchestrator
        elif tool_name == "document_writer_tool":
            from . import document_writer_tool

            globals()["document_writer_tool"] = document_writer_tool
        elif tool_name == "ai_document_writer_orchestrator":
            from . import ai_document_writer_orchestrator

            globals()["ai_document_writer_orchestrator"] = ai_document_writer_orchestrator
        elif tool_name == "document_creator_tool":
            from . import document_creator_tool

            globals()["document_creator_tool"] = document_creator_tool
        elif tool_name == "document_layout_tool":
            from . import document_layout_tool

            globals()["document_layout_tool"] = document_layout_tool
        elif tool_name == "content_insertion_tool":
            from . import content_insertion_tool

            globals()["content_insertion_tool"] = content_insertion_tool

    except ImportError as e:
        # Remove from loaded set if import failed
        _LOADED_DOC_TOOLS.discard(tool_name)
        print(f"Warning: Could not import {tool_name}: {e}")


def __getattr__(name: str):
    """
    Lazy loading mechanism for document tools.

    This allows importing tools like:
    from aiecs.tools.docs import document_parser_tool
    """
    if name in _AVAILABLE_DOC_TOOLS:
        _lazy_load_doc_tool(name)
        if name in globals():
            return globals()[name]

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def list_doc_tools():
    """List all available document tools"""
    return _AVAILABLE_DOC_TOOLS.copy()


def load_all_doc_tools():
    """Load all available document tools"""
    for tool_name in _AVAILABLE_DOC_TOOLS:
        _lazy_load_doc_tool(tool_name)


# Auto-discovery of tool modules in this directory


def _discover_doc_tools():
    """Discover document tool modules in the current directory"""
    current_dir = os.path.dirname(__file__)
    if not current_dir:
        return

    for filename in os.listdir(current_dir):
        if filename.endswith("_tool.py") and not filename.startswith("__"):
            tool_name = filename[:-3]  # Remove .py extension
            if tool_name not in _AVAILABLE_DOC_TOOLS:
                _AVAILABLE_DOC_TOOLS.append(tool_name)


# Discover tools on import
_discover_doc_tools()

__all__ = [
    "list_doc_tools",
    "load_all_doc_tools",
] + _AVAILABLE_DOC_TOOLS
