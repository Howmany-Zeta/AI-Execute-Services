"""
Multi-Task Core Layer

This module provides the foundational interfaces, models, and exceptions
for the multi-task service architecture.
"""

from .interfaces import *
from .models import *
from .exceptions import *

__all__ = [
    # Interfaces
    'ITaskService',
    'IAgentManager',
    'IToolManager',
    'IExecutor',

    # Models
    'TaskModel',
    'TaskRequest',
    'TaskResponse',
    'TaskStep',
    'TaskWorkflow',
    'AgentModel',
    'AgentConfig',
    'AgentCapability',
    'AgentExecution',
    'AgentTeam',
    'ExecutionModel',
    'ExecutionContext',
    'ExecutionResult',
    'ExecutionPlan',
    'ToolConfig',
    'ToolResult',

    # Enums
    'TaskStatus',
    'TaskPriority',
    'TaskCategory',
    'TaskType',
    'AgentType',
    'AgentRole',
    'AgentStatus',
    'ExecutionStatus',
    'ExecutionMode',
    'ToolType',

    # Exceptions
    'TaskException',
    'TaskValidationError',
    'TaskExecutionError',
    'TaskTimeoutError',
    'TaskNotFoundException',
    'TaskCancellationError',
    'TaskDependencyError',
    'TaskQualityError',
    'TaskResourceError',
    'ExecutionException',
    'ExecutionValidationError',
    'ExecutionRuntimeError',
    'ExecutionTimeoutError',
    'ExecutionNotFoundException',
    'ExecutionPlanningError',
    'ExecutionStateError',
    'HookRegistrationError',
    'HookNotFoundException',
    'ExecutionResourceError',
    'ExecutionConcurrencyError'
]
