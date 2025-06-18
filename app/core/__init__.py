"""
Core module for the Python middleware application.

This module provides the core functionality including:
- Service execution and orchestration
- Database management
- WebSocket communication
- Metrics and monitoring
- Distributed tracing
- DSL processing
- Operation execution
"""

from .config import get_settings
from .execution_interface import ExecutionInterface
from .execution_utils import ExecutionUtils
from .prompt_loader import get_prompt
from .registry import register_ai_service, get_ai_service
from .task_context import TaskContext, task_context, build_context
from .tool_executor import ToolExecutor

# New modular components
from .executor_metrics import ExecutorMetrics
from .database_manager import DatabaseManager, TaskStepResult, TaskStatus
from .websocket_manager import WebSocketManager, UserConfirmation
from .celery_task_manager import CeleryTaskManager
from .operation_executor import OperationExecutor
from .dsl_processor import DSLProcessor
from .tracing_manager import TracingManager

# Main service executor (refactored)
from .service_executor import ServiceExecutor, ExecutorConfig, get_executor, initialize_executor

__all__ = [
    # Configuration and utilities
    'get_settings',
    'ExecutionInterface',
    'ExecutionUtils',
    'get_prompt',
    'register_ai_service',
    'get_ai_service',
    'TaskContext',
    'task_context',
    'build_context',
    'ToolExecutor',

    # Modular components
    'ExecutorMetrics',
    'DatabaseManager',
    'WebSocketManager',
    'CeleryTaskManager',
    'OperationExecutor',
    'DSLProcessor',
    'TracingManager',

    # Models and enums
    'TaskStepResult',
    'TaskStatus',
    'UserConfirmation',

    # Main service executor
    'ServiceExecutor',
    'ExecutorConfig',
    'get_executor',
    'initialize_executor',
]

# Version information
__version__ = "1.0.0"
__author__ = "Python Middleware Team"
__description__ = "Modular core components for service execution and orchestration"
