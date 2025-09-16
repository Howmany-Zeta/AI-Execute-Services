"""
Core module for the Python middleware application.

This module provides the core interfaces and abstractions including:
- Execution interfaces
- Core abstractions
"""

# Core interfaces
from .interface.execution_interface import (
    ExecutionInterface,
    IToolProvider,
    IToolExecutor,
    ICacheProvider,
    IOperationExecutor
)

from .interface.storage_interface import (
    ISessionStorage,
    IConversationStorage,
    ICheckpointStorage,
    ITaskContextStorage,
    IStorageBackend,
    ICheckpointerBackend
)

__all__ = [
    # Execution interfaces
    'ExecutionInterface',
    'IToolProvider',
    'IToolExecutor',
    'ICacheProvider',
    'IOperationExecutor',
    # Storage interfaces
    'ISessionStorage',
    'IConversationStorage',
    'ICheckpointStorage',
    'ITaskContextStorage',
    'IStorageBackend',
    'ICheckpointerBackend',
]

# Version information
__version__ = "1.0.0"
__author__ = "Python Middleware Team"
__description__ = "Core interfaces and abstractions for the middleware architecture"
