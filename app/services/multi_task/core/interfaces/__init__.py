"""
Core Interfaces for Multi-Task Service

This module defines the abstract interfaces that all components
in the multi-task service must implement.
"""

from .task_service import ITaskService
from .agent_manager import IAgentManager
from .tool_manager import IToolManager
from .executor import IExecutor
from .data_repository import (
    IDataRepository, ITaskRepository, IResultRepository, IStorageProvider
)

__all__ = [
    'ITaskService',
    'IAgentManager',
    'IToolManager',
    'IExecutor',
    'IDataRepository',
    'ITaskRepository',
    'IResultRepository',
    'IStorageProvider'
]
