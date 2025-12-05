"""
Core module for the Python middleware application.

This module provides the core interfaces and abstractions including:
- Execution interfaces
- Core abstractions
- Service registry (no dependencies, safe to import anywhere)
"""

# Core interfaces
from .interface.execution_interface import (
    ExecutionInterface,
    IToolProvider,
    IToolExecutor,
    ICacheProvider,
    IOperationExecutor,
)

from .interface.storage_interface import (
    ISessionStorage,
    IConversationStorage,
    ICheckpointStorage,
    ITaskContextStorage,
    IStorageBackend,
    ICheckpointerBackend,
)

# Service registry (zero dependencies, safe for module-level imports)
from .registry import (
    AI_SERVICE_REGISTRY,
    register_ai_service,
    get_ai_service,
    list_registered_services,
    clear_registry,
)

__all__ = [
    # Execution interfaces
    "ExecutionInterface",
    "IToolProvider",
    "IToolExecutor",
    "ICacheProvider",
    "IOperationExecutor",
    # Storage interfaces
    "ISessionStorage",
    "IConversationStorage",
    "ICheckpointStorage",
    "ITaskContextStorage",
    "IStorageBackend",
    "ICheckpointerBackend",
    # Service registry
    "AI_SERVICE_REGISTRY",
    "register_ai_service",
    "get_ai_service",
    "list_registered_services",
    "clear_registry",
]

# Version information
__version__ = "1.0.0"
__author__ = "Python Middleware Team"
__description__ = "Core interfaces and abstractions for the middleware architecture"
