"""
Execution Exceptions

Exception classes for execution-related errors in the multi-task service.
"""

from typing import Optional, Dict, Any, List


class ExecutionException(Exception):
    """
    Base exception class for all execution-related errors.

    This is the root exception for all execution-specific errors in the multi-task service.
    All other execution exceptions should inherit from this class.
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        execution_id: Optional[str] = None
    ):
        """
        Initialize an execution exception.

        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            details: Additional error details
            execution_id: ID of the execution that caused the error
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "EXECUTION_ERROR"
        self.details = details or {}
        self.execution_id = execution_id

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
            "execution_id": self.execution_id
        }


class ExecutionValidationError(ExecutionException):
    """
    Exception raised when execution validation fails.

    This exception is raised when execution plans, configurations,
    or parameters fail validation checks.
    """

    def __init__(
        self,
        message: str,
        validation_errors: Optional[Dict[str, Any]] = None,
        execution_id: Optional[str] = None
    ):
        """
        Initialize an execution validation error.

        Args:
            message: Human-readable error message
            validation_errors: Detailed validation error information
            execution_id: ID of the execution that failed validation
        """
        super().__init__(
            message=message,
            error_code="EXECUTION_VALIDATION_ERROR",
            details={"validation_errors": validation_errors or {}},
            execution_id=execution_id
        )
        self.validation_errors = validation_errors or {}


class ExecutionRuntimeError(ExecutionException):
    """
    Exception raised when execution fails at runtime.

    This exception is raised when an execution fails during runtime
    due to unexpected conditions, resource issues, or system errors.
    """

    def __init__(
        self,
        message: str,
        step: Optional[str] = None,
        cause: Optional[Exception] = None,
        execution_id: Optional[str] = None,
        retry_count: int = 0
    ):
        """
        Initialize an execution runtime error.

        Args:
            message: Human-readable error message
            step: The execution step where the error occurred
            cause: The underlying exception that caused this error
            execution_id: ID of the execution that failed
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
            error_code="EXECUTION_RUNTIME_ERROR",
            details=details,
            execution_id=execution_id
        )
        self.step = step
        self.cause = cause
        self.retry_count = retry_count


class ExecutionTimeoutError(ExecutionException):
    """
    Exception raised when execution times out.

    This exception is raised when an execution exceeds its configured
    timeout duration.
    """

    def __init__(
        self,
        message: str,
        timeout_seconds: Optional[int] = None,
        elapsed_seconds: Optional[float] = None,
        execution_id: Optional[str] = None
    ):
        """
        Initialize an execution timeout error.

        Args:
            message: Human-readable error message
            timeout_seconds: The configured timeout duration
            elapsed_seconds: The actual elapsed time before timeout
            execution_id: ID of the execution that timed out
        """
        super().__init__(
            message=message,
            error_code="EXECUTION_TIMEOUT_ERROR",
            details={
                "timeout_seconds": timeout_seconds,
                "elapsed_seconds": elapsed_seconds
            },
            execution_id=execution_id
        )
        self.timeout_seconds = timeout_seconds
        self.elapsed_seconds = elapsed_seconds


class ExecutionNotFoundException(ExecutionException):
    """
    Exception raised when a requested execution is not found.

    This exception is raised when attempting to access, update,
    or control an execution that doesn't exist in the system.
    """

    def __init__(
        self,
        execution_id: str,
        operation: Optional[str] = None
    ):
        """
        Initialize an execution not found error.

        Args:
            execution_id: ID of the execution that was not found
            operation: The operation that was attempted
        """
        message = f"Execution with ID '{execution_id}' not found"
        if operation:
            message += f" during {operation}"

        super().__init__(
            message=message,
            error_code="EXECUTION_NOT_FOUND",
            details={"operation": operation},
            execution_id=execution_id
        )
        self.operation = operation


class ExecutionPlanningError(ExecutionException):
    """
    Exception raised when execution planning fails.

    This exception is raised when the system cannot create a valid
    execution plan for a workflow or task sequence.
    """

    def __init__(
        self,
        message: str,
        planning_errors: Optional[List[str]] = None,
        workflow_id: Optional[str] = None,
        execution_id: Optional[str] = None
    ):
        """
        Initialize an execution planning error.

        Args:
            message: Human-readable error message
            planning_errors: List of specific planning errors
            workflow_id: ID of the workflow that couldn't be planned
            execution_id: ID of the execution context
        """
        super().__init__(
            message=message,
            error_code="EXECUTION_PLANNING_ERROR",
            details={
                "planning_errors": planning_errors or [],
                "workflow_id": workflow_id
            },
            execution_id=execution_id
        )
        self.planning_errors = planning_errors or []
        self.workflow_id = workflow_id


class ExecutionStateError(ExecutionException):
    """
    Exception raised when execution state is invalid for an operation.

    This exception is raised when attempting to perform an operation
    on an execution that is in an incompatible state.
    """

    def __init__(
        self,
        message: str,
        current_state: Optional[str] = None,
        required_state: Optional[str] = None,
        operation: Optional[str] = None,
        execution_id: Optional[str] = None
    ):
        """
        Initialize an execution state error.

        Args:
            message: Human-readable error message
            current_state: Current state of the execution
            required_state: Required state for the operation
            operation: The operation that was attempted
            execution_id: ID of the execution with invalid state
        """
        super().__init__(
            message=message,
            error_code="EXECUTION_STATE_ERROR",
            details={
                "current_state": current_state,
                "required_state": required_state,
                "operation": operation
            },
            execution_id=execution_id
        )
        self.current_state = current_state
        self.required_state = required_state
        self.operation = operation


class HookRegistrationError(ExecutionException):
    """
    Exception raised when execution hook registration fails.

    This exception is raised when attempting to register an execution
    hook that is invalid or conflicts with existing hooks.
    """

    def __init__(
        self,
        message: str,
        hook_type: Optional[str] = None,
        hook_name: Optional[str] = None,
        reason: Optional[str] = None
    ):
        """
        Initialize a hook registration error.

        Args:
            message: Human-readable error message
            hook_type: Type of hook that failed to register
            hook_name: Name of the hook that failed to register
            reason: Specific reason for registration failure
        """
        super().__init__(
            message=message,
            error_code="HOOK_REGISTRATION_ERROR",
            details={
                "hook_type": hook_type,
                "hook_name": hook_name,
                "reason": reason
            }
        )
        self.hook_type = hook_type
        self.hook_name = hook_name
        self.reason = reason


class HookNotFoundException(ExecutionException):
    """
    Exception raised when a requested execution hook is not found.

    This exception is raised when attempting to access or unregister
    an execution hook that doesn't exist.
    """

    def __init__(
        self,
        hook_type: str,
        hook_name: Optional[str] = None,
        operation: Optional[str] = None
    ):
        """
        Initialize a hook not found error.

        Args:
            hook_type: Type of hook that was not found
            hook_name: Name of the hook that was not found
            operation: The operation that was attempted
        """
        message = f"Hook of type '{hook_type}'"
        if hook_name:
            message += f" with name '{hook_name}'"
        message += " not found"
        if operation:
            message += f" during {operation}"

        super().__init__(
            message=message,
            error_code="HOOK_NOT_FOUND",
            details={
                "hook_type": hook_type,
                "hook_name": hook_name,
                "operation": operation
            }
        )
        self.hook_type = hook_type
        self.hook_name = hook_name
        self.operation = operation


class ExecutionResourceError(ExecutionException):
    """
    Exception raised when execution fails due to resource constraints.

    This exception is raised when an execution cannot proceed due to
    insufficient resources (memory, CPU, storage, etc.).
    """

    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        required: Optional[Any] = None,
        available: Optional[Any] = None,
        execution_id: Optional[str] = None
    ):
        """
        Initialize an execution resource error.

        Args:
            message: Human-readable error message
            resource_type: Type of resource that is insufficient
            required: Required amount of the resource
            available: Available amount of the resource
            execution_id: ID of the execution that couldn't get resources
        """
        super().__init__(
            message=message,
            error_code="EXECUTION_RESOURCE_ERROR",
            details={
                "resource_type": resource_type,
                "required": required,
                "available": available
            },
            execution_id=execution_id
        )
        self.resource_type = resource_type
        self.required = required
        self.available = available


class ExecutionConcurrencyError(ExecutionException):
    """
    Exception raised when execution fails due to concurrency issues.

    This exception is raised when parallel executions conflict or
    when there are race conditions in execution management.
    """

    def __init__(
        self,
        message: str,
        conflicting_executions: Optional[List[str]] = None,
        resource_conflict: Optional[str] = None,
        execution_id: Optional[str] = None
    ):
        """
        Initialize an execution concurrency error.

        Args:
            message: Human-readable error message
            conflicting_executions: List of conflicting execution IDs
            resource_conflict: Description of the resource conflict
            execution_id: ID of the execution that encountered the conflict
        """
        super().__init__(
            message=message,
            error_code="EXECUTION_CONCURRENCY_ERROR",
            details={
                "conflicting_executions": conflicting_executions or [],
                "resource_conflict": resource_conflict
            },
            execution_id=execution_id
        )
        self.conflicting_executions = conflicting_executions or []
        self.resource_conflict = resource_conflict


# Aliases for common exception names used in the execution layer
ExecutionError = ExecutionException
ValidationError = ExecutionValidationError
PlanningError = ExecutionPlanningError
