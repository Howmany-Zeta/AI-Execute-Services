"""
Task Exceptions

Exception classes for task-related errors in the multi-task service.
"""

from typing import Optional, Dict, Any


class TaskException(Exception):
    """
    Base exception class for all task-related errors.

    This is the root exception for all task-specific errors in the multi-task service.
    All other task exceptions should inherit from this class.
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None
    ):
        """
        Initialize a task exception.

        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            details: Additional error details
            task_id: ID of the task that caused the error
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "TASK_ERROR"
        self.details = details or {}
        self.task_id = task_id

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the exception to a dictionary representation.

        Returns:
            Dictionary containing exception details
        """
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "details": self.details,
            "task_id": self.task_id
        }


class TaskValidationError(TaskException):
    """
    Exception raised when task validation fails.

    This exception is raised when task input data, configuration,
    or parameters fail validation checks.
    """

    def __init__(
        self,
        message: str,
        validation_errors: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None
    ):
        """
        Initialize a task validation error.

        Args:
            message: Human-readable error message
            validation_errors: Detailed validation error information
            task_id: ID of the task that failed validation
        """
        super().__init__(
            message=message,
            error_code="TASK_VALIDATION_ERROR",
            details={"validation_errors": validation_errors or {}},
            task_id=task_id
        )
        self.validation_errors = validation_errors or {}


class TaskExecutionError(TaskException):
    """
    Exception raised when task execution fails.

    This exception is raised when a task fails during execution,
    including agent failures, tool failures, or other runtime errors.
    """

    def __init__(
        self,
        message: str,
        step: Optional[str] = None,
        cause: Optional[Exception] = None,
        task_id: Optional[str] = None,
        retry_count: int = 0
    ):
        """
        Initialize a task execution error.

        Args:
            message: Human-readable error message
            step: The execution step where the error occurred
            cause: The underlying exception that caused this error
            task_id: ID of the task that failed execution
            retry_count: Number of retries attempted
        """
        details = {
            "step": step,
            "retry_count": retry_count
        }
        if cause:
            details["cause"] = str(cause)
            details["cause_type"] = type(cause).__name__

        super().__init__(
            message=message,
            error_code="TASK_EXECUTION_ERROR",
            details=details,
            task_id=task_id
        )
        self.step = step
        self.cause = cause
        self.retry_count = retry_count


class TaskTimeoutError(TaskException):
    """
    Exception raised when task execution times out.

    This exception is raised when a task exceeds its configured
    timeout duration during execution.
    """

    def __init__(
        self,
        message: str,
        timeout_seconds: Optional[int] = None,
        elapsed_seconds: Optional[float] = None,
        task_id: Optional[str] = None
    ):
        """
        Initialize a task timeout error.

        Args:
            message: Human-readable error message
            timeout_seconds: The configured timeout duration
            elapsed_seconds: The actual elapsed time before timeout
            task_id: ID of the task that timed out
        """
        super().__init__(
            message=message,
            error_code="TASK_TIMEOUT_ERROR",
            details={
                "timeout_seconds": timeout_seconds,
                "elapsed_seconds": elapsed_seconds
            },
            task_id=task_id
        )
        self.timeout_seconds = timeout_seconds
        self.elapsed_seconds = elapsed_seconds


class TaskNotFoundException(TaskException):
    """
    Exception raised when a requested task is not found.

    This exception is raised when attempting to access, update,
    or delete a task that doesn't exist in the system.
    """

    def __init__(
        self,
        task_id: str,
        operation: Optional[str] = None
    ):
        """
        Initialize a task not found error.

        Args:
            task_id: ID of the task that was not found
            operation: The operation that was attempted
        """
        message = f"Task with ID '{task_id}' not found"
        if operation:
            message += f" during {operation}"

        super().__init__(
            message=message,
            error_code="TASK_NOT_FOUND",
            details={"operation": operation},
            task_id=task_id
        )
        self.operation = operation


class TaskCancellationError(TaskException):
    """
    Exception raised when task cancellation fails or is invalid.

    This exception is raised when attempting to cancel a task
    that cannot be cancelled or when cancellation fails.
    """

    def __init__(
        self,
        message: str,
        task_status: Optional[str] = None,
        reason: Optional[str] = None,
        task_id: Optional[str] = None
    ):
        """
        Initialize a task cancellation error.

        Args:
            message: Human-readable error message
            task_status: Current status of the task
            reason: Reason why cancellation failed
            task_id: ID of the task that couldn't be cancelled
        """
        super().__init__(
            message=message,
            error_code="TASK_CANCELLATION_ERROR",
            details={
                "task_status": task_status,
                "reason": reason
            },
            task_id=task_id
        )
        self.task_status = task_status
        self.reason = reason


class TaskDependencyError(TaskException):
    """
    Exception raised when task dependency resolution fails.

    This exception is raised when a task's dependencies cannot
    be resolved or when there are circular dependencies.
    """

    def __init__(
        self,
        message: str,
        dependencies: Optional[list] = None,
        circular_deps: Optional[list] = None,
        task_id: Optional[str] = None
    ):
        """
        Initialize a task dependency error.

        Args:
            message: Human-readable error message
            dependencies: List of unresolved dependencies
            circular_deps: List of circular dependencies detected
            task_id: ID of the task with dependency issues
        """
        super().__init__(
            message=message,
            error_code="TASK_DEPENDENCY_ERROR",
            details={
                "dependencies": dependencies or [],
                "circular_dependencies": circular_deps or []
            },
            task_id=task_id
        )
        self.dependencies = dependencies or []
        self.circular_deps = circular_deps or []


class TaskQualityError(TaskException):
    """
    Exception raised when task result quality is below threshold.

    This exception is raised when a task's output fails quality
    control checks or doesn't meet the required quality standards.
    """

    def __init__(
        self,
        message: str,
        quality_score: Optional[float] = None,
        threshold: Optional[float] = None,
        quality_issues: Optional[list] = None,
        task_id: Optional[str] = None
    ):
        """
        Initialize a task quality error.

        Args:
            message: Human-readable error message
            quality_score: Actual quality score achieved
            threshold: Required quality threshold
            quality_issues: List of specific quality issues
            task_id: ID of the task with quality issues
        """
        super().__init__(
            message=message,
            error_code="TASK_QUALITY_ERROR",
            details={
                "quality_score": quality_score,
                "threshold": threshold,
                "quality_issues": quality_issues or []
            },
            task_id=task_id
        )
        self.quality_score = quality_score
        self.threshold = threshold
        self.quality_issues = quality_issues or []


class TaskResourceError(TaskException):
    """
    Exception raised when task execution fails due to resource constraints.

    This exception is raised when a task cannot be executed due to
    insufficient resources (memory, CPU, storage, etc.).
    """

    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        required: Optional[Any] = None,
        available: Optional[Any] = None,
        task_id: Optional[str] = None
    ):
        """
        Initialize a task resource error.

        Args:
            message: Human-readable error message
            resource_type: Type of resource that is insufficient
            required: Required amount of the resource
            available: Available amount of the resource
            task_id: ID of the task that couldn't get resources
        """
        super().__init__(
            message=message,
            error_code="TASK_RESOURCE_ERROR",
            details={
                "resource_type": resource_type,
                "required": required,
                "available": available
            },
            task_id=task_id
        )
        self.resource_type = resource_type
        self.required = required
        self.available = available
