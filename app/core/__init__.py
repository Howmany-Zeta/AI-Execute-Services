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

__all__ = [
    # Core interfaces
    'ExecutionInterface',
    'IToolProvider',
    'IToolExecutor',
    'ICacheProvider',
    'IOperationExecutor',
]

# Version information
__version__ = "2.0.0"
__author__ = "Python Middleware Team"
__description__ = "Core interfaces and abstractions for the middleware architecture"
