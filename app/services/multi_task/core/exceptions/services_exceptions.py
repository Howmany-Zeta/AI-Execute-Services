"""
Services Exceptions

This module contains all the exception classes used across the multi-task services.
These exceptions have been extracted from individual service files for unified maintenance.
"""

from typing import Dict, Any, Optional


class ServiceException(Exception):
    """Base exception for all service-related errors."""

    def __init__(self, message: str, service_name: str = None, context: Dict[str, Any] = None):
        super().__init__(message)
        self.service_name = service_name
        self.context = context or {}


class ValidationError(ServiceException):
    """Exception raised when validation fails."""

    def __init__(self, message: str, plan: Dict[str, Any] = None, validation_type: str = None, context: Dict[str, Any] = None):
        super().__init__(message, "ValidationService", context)
        self.plan = plan
        self.validation_type = validation_type


class PlanValidationError(ValidationError):
    """Specific exception for plan validation errors."""

    def __init__(self, message: str, plan: Dict[str, Any] = None, validation_issues: list = None, context: Dict[str, Any] = None):
        super().__init__(message, plan, "plan_validation", context)
        self.validation_issues = validation_issues or []


class ExaminationError(ServiceException):
    """Exception raised when examination process fails."""

    def __init__(self, message: str, task_name: str = None, category: str = None, context: Dict[str, Any] = None):
        super().__init__(message, "ExamineOutcomeService", context)
        self.task_name = task_name
        self.category = category


class AcceptanceError(ServiceException):
    """Exception raised when acceptance process fails."""

    def __init__(self, message: str, task_name: str = None, category: str = None, context: Dict[str, Any] = None):
        super().__init__(message, "AcceptOutcomeService", context)
        self.task_name = task_name
        self.category = category


class InteractionError(ServiceException):
    """Exception raised when user interaction validation fails."""

    def __init__(self, message: str, user_input: str = None, request_type: str = None, context: Dict[str, Any] = None):
        super().__init__(message, "InteracterService", context)
        self.user_input = user_input
        self.request_type = request_type


class MiningError(ServiceException):
    """Exception raised when mining process fails."""

    def __init__(self, message: str, user_input: str = None, demand_state: str = None, context: Dict[str, Any] = None):
        super().__init__(message, "MiningService", context)
        self.user_input = user_input
        self.demand_state = demand_state


class WorkflowPlanningError(ServiceException):
    """Exception raised when workflow planning fails."""

    def __init__(self, message: str, task_id: str = None, planning_stage: str = None, context: Dict[str, Any] = None):
        super().__init__(message, "WorkflowPlanningService", context)
        self.task_id = task_id
        self.planning_stage = planning_stage


class AgentInitializationError(ServiceException):
    """Exception raised when agent initialization fails."""

    def __init__(self, message: str, agent_name: str = None, agent_role: str = None, context: Dict[str, Any] = None):
        super().__init__(message, "AgentService", context)
        self.agent_name = agent_name
        self.agent_role = agent_role


class ConfigurationError(ServiceException):
    """Exception raised when configuration is invalid or missing."""

    def __init__(self, message: str, config_key: str = None, config_file: str = None, context: Dict[str, Any] = None):
        super().__init__(message, "ConfigurationService", context)
        self.config_key = config_key
        self.config_file = config_file


class LLMIntegrationError(ServiceException):
    """Exception raised when LLM integration fails."""

    def __init__(self, message: str, llm_provider: str = None, operation: str = None, context: Dict[str, Any] = None):
        super().__init__(message, "LLMIntegrationService", context)
        self.llm_provider = llm_provider
        self.operation = operation


class QualityProcessorError(ServiceException):
    """Exception raised when quality processing fails."""

    def __init__(self, message: str, quality_check: str = None, task_category: str = None, context: Dict[str, Any] = None):
        super().__init__(message, "QualityProcessor", context)
        self.quality_check = quality_check
        self.task_category = task_category


class DSLSyntaxError(ValidationError):
    """Exception raised when DSL syntax is invalid."""

    def __init__(self, message: str, dsl_step: str = None, line_number: int = None, context: Dict[str, Any] = None):
        super().__init__(message, None, "dsl_syntax", context)
        self.dsl_step = dsl_step
        self.line_number = line_number


class DependencyError(ValidationError):
    """Exception raised when dependency validation fails."""

    def __init__(self, message: str, dependency_chain: list = None, circular_deps: list = None, context: Dict[str, Any] = None):
        super().__init__(message, None, "dependency", context)
        self.dependency_chain = dependency_chain or []
        self.circular_deps = circular_deps or []


class ResourceConstraintError(ServiceException):
    """Exception raised when resource constraints are violated."""

    def __init__(self, message: str, resource_type: str = None, required: Any = None, available: Any = None, context: Dict[str, Any] = None):
        super().__init__(message, "ResourceManager", context)
        self.resource_type = resource_type
        self.required = required
        self.available = available


class TimeoutError(ServiceException):
    """Exception raised when operations timeout."""

    def __init__(self, message: str, operation: str = None, timeout_seconds: float = None, context: Dict[str, Any] = None):
        super().__init__(message, "TimeoutManager", context)
        self.operation = operation
        self.timeout_seconds = timeout_seconds


class SecurityError(ServiceException):
    """Exception raised when security violations are detected."""

    def __init__(self, message: str, security_check: str = None, violation_type: str = None, context: Dict[str, Any] = None):
        super().__init__(message, "SecurityService", context)
        self.security_check = security_check
        self.violation_type = violation_type


class SummarizerError(ServiceException):
    """Exception raised when summarizer operations fail."""

    def __init__(self, message: str, session_id: str = None, step: str = None, context: Dict[str, Any] = None):
        super().__init__(message, "SummarizerService", context)
        self.session_id = session_id
        self.step = step


class WorkflowExecutionError(ServiceException):
    """Exception raised when workflow execution fails."""

    def __init__(self, message: str, workflow_id: str = None, execution_step: str = None, context: Dict[str, Any] = None):
        super().__init__(message, "WorkflowExecutor", context)
        self.workflow_id = workflow_id
        self.execution_step = execution_step


class StreamingError(ServiceException):
    """Exception raised when streaming operations fail."""

    def __init__(self, message: str, session_id: str = None, stream_type: str = None, context: Dict[str, Any] = None):
        super().__init__(message, "StreamingService", context)
        self.session_id = session_id
        self.stream_type = stream_type


class SessionManagementError(ServiceException):
    """Exception raised when session management fails."""

    def __init__(self, message: str, session_id: str = None, operation: str = None, context: Dict[str, Any] = None):
        super().__init__(message, "SessionManager", context)
        self.session_id = session_id
        self.operation = operation
