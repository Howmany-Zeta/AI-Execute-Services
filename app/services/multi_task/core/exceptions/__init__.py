"""
Core Exceptions for Multi-Task Service

This module defines the exception hierarchy for the multi-task service,
providing structured error handling across all components.
"""

from .task_exceptions import (
    TaskException,
    TaskValidationError,
    TaskExecutionError,
    TaskTimeoutError,
    TaskNotFoundException,
    TaskCancellationError,
    TaskDependencyError,
    TaskQualityError,
    TaskResourceError
)

from .execution_exceptions import (
    ExecutionException,
    ExecutionValidationError,
    ExecutionRuntimeError,
    ExecutionTimeoutError,
    ExecutionNotFoundException,
    ExecutionPlanningError,
    ExecutionStateError,
    HookRegistrationError,
    HookNotFoundException,
    ExecutionResourceError,
    ExecutionConcurrencyError
)

from .data_exceptions import (
    DataException,
    DataRepositoryError,
    DataValidationError,
    DataSerializationError,
    StorageError,
    StorageConnectionError,
    StorageTimeoutError,
    StorageQuotaExceededError,
    DataNotFoundError,
    DataConflictError,
    DataIntegrityError,
    CacheError,
    CacheConnectionError,
    DataMigrationError,
    DataBackupError,
    DataRestoreError,
    DataCompressionError,
    DataEncryptionError,
    SerializationError,
    DeserializationError,
    DataLayerError
)

__all__ = [
    # Task Exceptions
    'TaskException',
    'TaskValidationError',
    'TaskExecutionError',
    'TaskTimeoutError',
    'TaskNotFoundException',
    'TaskCancellationError',
    'TaskDependencyError',
    'TaskQualityError',
    'TaskResourceError',

    # Execution Exceptions
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
    'ExecutionConcurrencyError',

    # Data Exceptions
    'DataException',
    'DataRepositoryError',
    'DataValidationError',
    'DataSerializationError',
    'StorageError',
    'StorageConnectionError',
    'StorageTimeoutError',
    'StorageQuotaExceededError',
    'DataNotFoundError',
    'DataConflictError',
    'DataIntegrityError',
    'CacheError',
    'CacheConnectionError',
    'DataMigrationError',
    'DataBackupError',
    'DataRestoreError',
    'DataCompressionError',
    'DataEncryptionError',
    'SerializationError',
    'DeserializationError',
    'DataLayerError'
]
