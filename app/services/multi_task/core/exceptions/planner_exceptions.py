"""
Planner Layer Exceptions

Custom exception classes for the planner layer, providing specific error handling
for different types of planning failures.
"""

from typing import Optional, Dict, Any


class PlannerException(Exception):
    """
    Base exception for all planner-related errors.

    This serves as the root exception class for the planner layer,
    allowing for broad exception handling when needed.
    """

    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}


class IntentParsingError(PlannerException):
    """
    Exception raised when intent parsing fails.

    This exception is raised when the system cannot properly parse
    user input to determine intent categories.
    """

    def __init__(self, message: str, user_input: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="INTENT_PARSING_ERROR", **kwargs)
        self.user_input = user_input


class DecompositionError(PlannerException):
    """
    Exception raised when task decomposition fails.

    This exception is raised when the system cannot break down
    intent categories into executable sub-tasks.
    """

    def __init__(self, message: str, categories: Optional[list] = None, **kwargs):
        super().__init__(message, error_code="DECOMPOSITION_ERROR", **kwargs)
        self.categories = categories


class PlanningError(PlannerException):
    """
    Exception raised when sequence planning fails.

    This exception is raised when the system cannot create
    an execution plan from the decomposed sub-tasks.
    """

    def __init__(self, message: str, subtask_breakdown: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(message, error_code="PLANNING_ERROR", **kwargs)
        self.subtask_breakdown = subtask_breakdown


class ValidationError(PlannerException):
    """
    Exception raised when plan validation fails.

    This exception is raised when a generated plan fails
    validation checks for consistency or feasibility.
    """

    def __init__(self, message: str, plan: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(message, error_code="VALIDATION_ERROR", **kwargs)
        self.plan = plan


class ConfigurationError(PlannerException):
    """
    Exception raised when planner configuration is invalid.

    This exception is raised when the planner is initialized
    with invalid or missing configuration parameters.
    """

    def __init__(self, message: str, config_field: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="CONFIGURATION_ERROR", **kwargs)
        self.config_field = config_field


class ResourceError(PlannerException):
    """
    Exception raised when required resources are unavailable.

    This exception is raised when the planner cannot access
    required agents, tools, or other resources.
    """

    def __init__(self, message: str, resource_type: Optional[str] = None, resource_id: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="RESOURCE_ERROR", **kwargs)
        self.resource_type = resource_type
        self.resource_id = resource_id


class TimeoutError(PlannerException):
    """
    Exception raised when planning operations timeout.

    This exception is raised when planning operations exceed
    their allocated time limits.
    """

    def __init__(self, message: str, operation: Optional[str] = None, timeout_seconds: Optional[float] = None, **kwargs):
        super().__init__(message, error_code="TIMEOUT_ERROR", **kwargs)
        self.operation = operation
        self.timeout_seconds = timeout_seconds
