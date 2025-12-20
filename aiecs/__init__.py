"""
AIECS - AI Execute Services

A powerful Python middleware framework for building AI-powered applications
with tool orchestration, task execution, and multi-provider LLM support.
"""

__version__ = "1.6.3"
__author__ = "AIECS Team"
__email__ = "iretbl@gmail.com"

# Core imports - these should work without configuration
from .aiecs_client import (
    AIECS,
    create_aiecs_client,
    create_simple_client,
    create_full_client,
)
from .domain.task.task_context import TaskContext

# Configuration
from .config.config import get_settings, validate_required_settings

# Tool system - safe to import
from .tools import discover_tools, list_tools, get_tool, register_tool

# Infrastructure components - can be imported safely (for advanced usage)
# These classes only require configuration when actually used
from .infrastructure.persistence.database_manager import DatabaseManager
from .infrastructure.messaging.celery_task_manager import CeleryTaskManager

# LLM providers
from .llm.client_factory import LLMClientFactory, AIProvider


def get_fastapi_app():
    """
    Get the FastAPI application instance (lazy loading)
    Only loads when explicitly requested to avoid import-time configuration validation
    """
    from .main import app

    return app


__all__ = [
    # Core API
    "AIECS",
    "create_aiecs_client",
    "create_simple_client",
    "create_full_client",
    "TaskContext",
    # FastAPI application (lazy loading)
    "get_fastapi_app",
    # Tool system
    "discover_tools",
    "list_tools",
    "get_tool",
    "register_tool",
    # Configuration
    "get_settings",
    "validate_required_settings",
    # Infrastructure (advanced)
    "DatabaseManager",
    "CeleryTaskManager",
    "LLMClientFactory",
    "AIProvider",
    # Metadata
    "__version__",
    "__author__",
    "__email__",
]
