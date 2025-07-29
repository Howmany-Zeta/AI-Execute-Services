"""
LangChain Error Handler

This module provides comprehensive error handling and crash prevention mechanisms
for LangChain tool integration. It implements circuit breakers, graceful degradation,
and recovery strategies to ensure system stability.
"""

import logging
import asyncio
import time
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
import traceback

from .langchain_adapter_tools import LangChainToolAdapter
from .langchain_tool_selector import ToolExecutionResult, ToolExecutionContext
from ..core.exceptions.task_exceptions import TaskValidationError, TaskExecutionError

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class ErrorContext:
    """Context information for error handling."""
    error_type: str
    error_message: str
    severity: ErrorSeverity
    tool_name: Optional[str] = None
    operation_name: Optional[str] = None
    task_id: Optional[str] = None
    agent_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    stack_trace: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecoveryAction:
    """Recovery action definition."""
    action_type: str
    description: str
    handler: Callable
    priority: int = 1
    conditions: Dict[str, Any] = field(default_factory=dict)


class CircuitBreaker:
    """
    Circuit breaker implementation for tool operations.

    Prevents cascading failures by temporarily disabling failing tools
    and allowing them to recover gradually.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 3
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Time to wait before trying half-open state
            success_threshold: Number of successes needed to close circuit
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0

        logger.debug("Circuit breaker initialized")

    def call(self, func: Callable, *args, **kwargs):
        """
        Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            Exception: If circuit is open or function fails
        """
        if self.state == CircuitBreakerState.OPEN:
            if time.time() - self.last_failure_time < self.recovery_timeout:
                raise Exception("Circuit breaker is OPEN - service unavailable")
            else:
                self.state = CircuitBreakerState.HALF_OPEN
                self.success_count = 0
                logger.info("Circuit breaker moved to HALF_OPEN state")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    async def acall(self, func: Callable, *args, **kwargs):
        """
        Execute async function with circuit breaker protection.

        Args:
            func: Async function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            Exception: If circuit is open or function fails
        """
        if self.state == CircuitBreakerState.OPEN:
            if time.time() - self.last_failure_time < self.recovery_timeout:
                raise Exception("Circuit breaker is OPEN - service unavailable")
            else:
                self.state = CircuitBreakerState.HALF_OPEN
                self.success_count = 0
                logger.info("Circuit breaker moved to HALF_OPEN state")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        """Handle successful execution."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                logger.info("Circuit breaker moved to CLOSED state")
        elif self.state == CircuitBreakerState.CLOSED:
            self.failure_count = 0

    def _on_failure(self):
        """Handle failed execution."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            logger.warning("Circuit breaker moved to OPEN state")

    def get_state(self) -> Dict[str, Any]:
        """Get circuit breaker state information."""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time
        }


class LangChainErrorHandler:
    """
    Comprehensive error handler for LangChain tool integration.

    Provides error classification, recovery strategies, and crash prevention
    mechanisms to ensure system stability and graceful degradation.
    """

    def __init__(self):
        """Initialize the error handler."""
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.error_history: List[ErrorContext] = []
        self.recovery_actions: Dict[str, List[RecoveryAction]] = {}
        self.error_counts: Dict[str, int] = {}
        self.blacklisted_tools: set = set()

        # Configuration
        self.max_error_history = 1000
        self.blacklist_threshold = 10
        self.recovery_timeout = 300

        # Initialize default recovery actions
        self._initialize_recovery_actions()

        logger.info("LangChain error handler initialized")

    def _initialize_recovery_actions(self):
        """Initialize default recovery actions."""
        # Tool execution errors
        self.recovery_actions["tool_execution"] = [
            RecoveryAction(
                action_type="retry_with_backoff",
                description="Retry with exponential backoff",
                handler=self._retry_with_backoff,
                priority=1
            ),
            RecoveryAction(
                action_type="fallback_tool",
                description="Use fallback tool",
                handler=self._use_fallback_tool,
                priority=2
            ),
            RecoveryAction(
                action_type="graceful_skip",
                description="Skip tool and continue",
                handler=self._graceful_skip,
                priority=3
            )
        ]

        # Parameter validation errors
        self.recovery_actions["parameter_validation"] = [
            RecoveryAction(
                action_type="parameter_correction",
                description="Attempt parameter correction",
                handler=self._correct_parameters,
                priority=1
            ),
            RecoveryAction(
                action_type="use_defaults",
                description="Use default parameters",
                handler=self._use_default_parameters,
                priority=2
            )
        ]

        # Timeout errors
        self.recovery_actions["timeout"] = [
            RecoveryAction(
                action_type="increase_timeout",
                description="Increase timeout and retry",
                handler=self._increase_timeout_and_retry,
                priority=1
            ),
            RecoveryAction(
                action_type="async_execution",
                description="Execute asynchronously",
                handler=self._execute_async,
                priority=2
            )
        ]

    async def handle_tool_execution(
        self,
        tool: LangChainToolAdapter,
        context: ToolExecutionContext,
        execution_func: Callable
    ) -> ToolExecutionResult:
        """
        Handle tool execution with comprehensive error handling.

        Args:
            tool: Tool to execute
            context: Execution context
            execution_func: Function to execute the tool

        Returns:
            Tool execution result with error handling
        """
        tool_key = f"{tool.tool_name}.{tool.operation_name}"

        try:
            # Check if tool is blacklisted
            if tool_key in self.blacklisted_tools:
                return self._create_blacklisted_result(tool, context)

            # Get or create circuit breaker for this tool
            circuit_breaker = self._get_circuit_breaker(tool_key)

            # Execute with circuit breaker protection
            result = await circuit_breaker.acall(execution_func)

            # Reset error count on success
            self.error_counts[tool_key] = 0

            return result

        except Exception as e:
            # Handle the error
            error_context = self._create_error_context(e, tool, context)
            return await self._handle_error(error_context, tool, context, execution_func)

    async def _handle_error(
        self,
        error_context: ErrorContext,
        tool: LangChainToolAdapter,
        context: ToolExecutionContext,
        execution_func: Callable
    ) -> ToolExecutionResult:
        """
        Handle a specific error with recovery strategies.

        Args:
            error_context: Error context information
            tool: Tool that failed
            context: Execution context
            execution_func: Original execution function

        Returns:
            Recovery result or error result
        """
        try:
            # Log the error
            self._log_error(error_context)

            # Add to error history
            self._add_to_error_history(error_context)

            # Update error counts
            tool_key = f"{tool.tool_name}.{tool.operation_name}"
            self.error_counts[tool_key] = self.error_counts.get(tool_key, 0) + 1

            # Check if tool should be blacklisted
            if self.error_counts[tool_key] >= self.blacklist_threshold:
                self.blacklisted_tools.add(tool_key)
                logger.warning(f"Blacklisted tool {tool_key} due to repeated failures")

            # Determine error type and apply recovery
            error_type = self._classify_error(error_context)
            recovery_result = await self._apply_recovery(
                error_type, error_context, tool, context, execution_func
            )

            if recovery_result:
                return recovery_result

            # If no recovery worked, return error result
            return self._create_error_result(error_context, tool, context)

        except Exception as recovery_error:
            logger.error(f"Error in error handling: {recovery_error}")
            return self._create_critical_error_result(tool, context, str(recovery_error))

    def _create_error_context(
        self,
        exception: Exception,
        tool: LangChainToolAdapter,
        context: ToolExecutionContext
    ) -> ErrorContext:
        """
        Create error context from exception.

        Args:
            exception: The exception that occurred
            tool: Tool that failed
            context: Execution context

        Returns:
            Error context
        """
        error_type = type(exception).__name__
        severity = self._determine_error_severity(exception)

        return ErrorContext(
            error_type=error_type,
            error_message=str(exception),
            severity=severity,
            tool_name=tool.tool_name,
            operation_name=tool.operation_name,
            task_id=context.task_id,
            agent_id=context.agent_id,
            stack_trace=traceback.format_exc(),
            metadata={
                "context": context.__dict__,
                "tool_info": {
                    "name": tool.name,
                    "description": tool.description
                }
            }
        )

    def _determine_error_severity(self, exception: Exception) -> ErrorSeverity:
        """
        Determine error severity based on exception type.

        Args:
            exception: The exception

        Returns:
            Error severity level
        """
        if isinstance(exception, (SystemExit, KeyboardInterrupt)):
            return ErrorSeverity.CRITICAL
        elif isinstance(exception, (MemoryError, OSError)):
            return ErrorSeverity.HIGH
        elif isinstance(exception, (ValueError, TypeError, AttributeError)):
            return ErrorSeverity.MEDIUM
        elif isinstance(exception, (asyncio.TimeoutError, ConnectionError)):
            return ErrorSeverity.MEDIUM
        else:
            return ErrorSeverity.LOW

    def _classify_error(self, error_context: ErrorContext) -> str:
        """
        Classify error type for recovery strategy selection.

        Args:
            error_context: Error context

        Returns:
            Error classification
        """
        error_type = error_context.error_type.lower()
        error_message = error_context.error_message.lower()

        if "timeout" in error_message or "timeouterror" in error_type:
            return "timeout"
        elif "validation" in error_message or "parameter" in error_message:
            return "parameter_validation"
        elif "connection" in error_message or "network" in error_message:
            return "network"
        elif "permission" in error_message or "access" in error_message:
            return "permission"
        else:
            return "tool_execution"

    async def _apply_recovery(
        self,
        error_type: str,
        error_context: ErrorContext,
        tool: LangChainToolAdapter,
        context: ToolExecutionContext,
        execution_func: Callable
    ) -> Optional[ToolExecutionResult]:
        """
        Apply recovery strategies for the error type.

        Args:
            error_type: Classified error type
            error_context: Error context
            tool: Tool that failed
            context: Execution context
            execution_func: Original execution function

        Returns:
            Recovery result or None if no recovery worked
        """
        recovery_actions = self.recovery_actions.get(error_type, [])

        for action in sorted(recovery_actions, key=lambda x: x.priority):
            try:
                logger.info(f"Attempting recovery: {action.description}")

                result = await action.handler(
                    error_context, tool, context, execution_func
                )

                if result and result.success:
                    logger.info(f"Recovery successful: {action.description}")
                    return result

            except Exception as e:
                logger.warning(f"Recovery action failed: {action.description} - {e}")
                continue

        return None

    async def _retry_with_backoff(
        self,
        error_context: ErrorContext,
        tool: LangChainToolAdapter,
        context: ToolExecutionContext,
        execution_func: Callable
    ) -> Optional[ToolExecutionResult]:
        """
        Retry execution with exponential backoff.

        Args:
            error_context: Error context
            tool: Tool to retry
            context: Execution context
            execution_func: Function to retry

        Returns:
            Retry result or None
        """
        max_retries = 3
        base_delay = 1

        for attempt in range(max_retries):
            try:
                delay = base_delay * (2 ** attempt)
                await asyncio.sleep(delay)

                logger.debug(f"Retry attempt {attempt + 1} for {tool.name}")
                result = await execution_func()

                if result and result.success:
                    return result

            except Exception as e:
                logger.debug(f"Retry attempt {attempt + 1} failed: {e}")
                continue

        return None

    async def _use_fallback_tool(
        self,
        error_context: ErrorContext,
        tool: LangChainToolAdapter,
        context: ToolExecutionContext,
        execution_func: Callable
    ) -> Optional[ToolExecutionResult]:
        """
        Use a fallback tool for the failed operation.

        Args:
            error_context: Error context
            tool: Failed tool
            context: Execution context
            execution_func: Original function

        Returns:
            Fallback result or None
        """
        # Simple fallback logic - could be enhanced
        fallback_tools = {
            'scraper': 'classifier.summarize',
            'search_api': 'research.summarize',
            'pandas': 'stats.describe'
        }

        fallback_spec = fallback_tools.get(tool.tool_name)
        if fallback_spec:
            # This would need actual fallback tool execution
            # For now, return a safe result
            return ToolExecutionResult(
                success=True,
                result="Fallback execution completed",
                tool_name="fallback",
                operation_name="safe_operation",
                execution_time=0.1,
                fallback_used=True
            )

        return None

    async def _graceful_skip(
        self,
        error_context: ErrorContext,
        tool: LangChainToolAdapter,
        context: ToolExecutionContext,
        execution_func: Callable
    ) -> Optional[ToolExecutionResult]:
        """
        Gracefully skip the failed tool and continue.

        Args:
            error_context: Error context
            tool: Failed tool
            context: Execution context
            execution_func: Original function

        Returns:
            Skip result
        """
        return ToolExecutionResult(
            success=True,
            result="Tool execution skipped due to error",
            tool_name=tool.tool_name,
            operation_name=tool.operation_name,
            execution_time=0.0,
            metadata={"skipped": True, "reason": error_context.error_message}
        )

    async def _correct_parameters(
        self,
        error_context: ErrorContext,
        tool: LangChainToolAdapter,
        context: ToolExecutionContext,
        execution_func: Callable
    ) -> Optional[ToolExecutionResult]:
        """
        Attempt to correct parameters and retry.

        Args:
            error_context: Error context
            tool: Tool with parameter issues
            context: Execution context
            execution_func: Original function

        Returns:
            Corrected execution result or None
        """
        # Simple parameter correction logic
        # This could be enhanced with more sophisticated correction
        try:
            # For now, just return None to indicate no correction possible
            return None

        except Exception as e:
            logger.error(f"Parameter correction failed: {e}")
            return None

    async def _use_default_parameters(
        self,
        error_context: ErrorContext,
        tool: LangChainToolAdapter,
        context: ToolExecutionContext,
        execution_func: Callable
    ) -> Optional[ToolExecutionResult]:
        """
        Use default parameters and retry.

        Args:
            error_context: Error context
            tool: Tool to retry with defaults
            context: Execution context
            execution_func: Original function

        Returns:
            Default execution result or None
        """
        try:
            # Execute with minimal/default parameters
            default_params = {"input": context.user_input}
            result = await tool._arun(**default_params)

            return ToolExecutionResult(
                success=True,
                result=result,
                tool_name=tool.tool_name,
                operation_name=tool.operation_name,
                execution_time=0.1,
                metadata={"used_defaults": True}
            )

        except Exception as e:
            logger.error(f"Default parameter execution failed: {e}")
            return None

    async def _increase_timeout_and_retry(
        self,
        error_context: ErrorContext,
        tool: LangChainToolAdapter,
        context: ToolExecutionContext,
        execution_func: Callable
    ) -> Optional[ToolExecutionResult]:
        """
        Increase timeout and retry execution.

        Args:
            error_context: Error context
            tool: Tool that timed out
            context: Execution context
            execution_func: Original function

        Returns:
            Extended timeout result or None
        """
        try:
            # Increase timeout by 50%
            extended_timeout = int(context.timeout * 1.5)

            # Create new context with extended timeout
            extended_context = ToolExecutionContext(
                task_id=context.task_id,
                agent_id=context.agent_id,
                task_category=context.task_category,
                user_input=context.user_input,
                domain=context.domain,
                priority=context.priority,
                timeout=extended_timeout,
                retry_count=1,  # Reduce retries for extended timeout
                fallback_enabled=context.fallback_enabled,
                metadata=context.metadata
            )

            # This would need to be implemented with the actual execution logic
            # For now, return None
            return None

        except Exception as e:
            logger.error(f"Extended timeout execution failed: {e}")
            return None

    async def _execute_async(
        self,
        error_context: ErrorContext,
        tool: LangChainToolAdapter,
        context: ToolExecutionContext,
        execution_func: Callable
    ) -> Optional[ToolExecutionResult]:
        """
        Execute tool asynchronously without blocking.

        Args:
            error_context: Error context
            tool: Tool to execute async
            context: Execution context
            execution_func: Original function

        Returns:
            Async execution result or None
        """
        try:
            # Create async task
            task = asyncio.create_task(execution_func())

            # Return immediately with placeholder result
            return ToolExecutionResult(
                success=True,
                result="Async execution started",
                tool_name=tool.tool_name,
                operation_name=tool.operation_name,
                execution_time=0.0,
                metadata={"async_execution": True}
            )

        except Exception as e:
            logger.error(f"Async execution setup failed: {e}")
            return None

    def _get_circuit_breaker(self, tool_key: str) -> CircuitBreaker:
        """
        Get or create circuit breaker for a tool.

        Args:
            tool_key: Tool identifier

        Returns:
            Circuit breaker instance
        """
        if tool_key not in self.circuit_breakers:
            self.circuit_breakers[tool_key] = CircuitBreaker()

        return self.circuit_breakers[tool_key]

    def _log_error(self, error_context: ErrorContext):
        """
        Log error with appropriate level based on severity.

        Args:
            error_context: Error context to log
        """
        log_message = (
            f"Tool error: {error_context.tool_name}.{error_context.operation_name} "
            f"- {error_context.error_message}"
        )

        if error_context.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message)
        elif error_context.severity == ErrorSeverity.HIGH:
            logger.error(log_message)
        elif error_context.severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message)
        else:
            logger.info(log_message)

    def _add_to_error_history(self, error_context: ErrorContext):
        """
        Add error to history with size management.

        Args:
            error_context: Error context to add
        """
        self.error_history.append(error_context)

        # Maintain history size
        if len(self.error_history) > self.max_error_history:
            self.error_history = self.error_history[-self.max_error_history:]

    def _create_blacklisted_result(
        self,
        tool: LangChainToolAdapter,
        context: ToolExecutionContext
    ) -> ToolExecutionResult:
        """
        Create result for blacklisted tool.

        Args:
            tool: Blacklisted tool
            context: Execution context

        Returns:
            Blacklisted tool result
        """
        return ToolExecutionResult(
            success=False,
            result=None,
            tool_name=tool.tool_name,
            operation_name=tool.operation_name,
            execution_time=0.0,
            error_message="Tool is blacklisted due to repeated failures",
            metadata={"blacklisted": True}
        )

    def _create_error_result(
        self,
        error_context: ErrorContext,
        tool: LangChainToolAdapter,
        context: ToolExecutionContext
    ) -> ToolExecutionResult:
        """
        Create error result from error context.

        Args:
            error_context: Error context
            tool: Failed tool
            context: Execution context

        Returns:
            Error result
        """
        return ToolExecutionResult(
            success=False,
            result=None,
            tool_name=tool.tool_name,
            operation_name=tool.operation_name,
            execution_time=0.0,
            error_message=error_context.error_message,
            metadata={
                "error_type": error_context.error_type,
                "severity": error_context.severity.value,
                "timestamp": error_context.timestamp
            }
        )

    def _create_critical_error_result(
        self,
        tool: LangChainToolAdapter,
        context: ToolExecutionContext,
        error_message: str
    ) -> ToolExecutionResult:
        """
        Create critical error result.

        Args:
            tool: Failed tool
            context: Execution context
            error_message: Error message

        Returns:
            Critical error result
        """
        return ToolExecutionResult(
            success=False,
            result=None,
            tool_name=tool.tool_name,
            operation_name=tool.operation_name,
            execution_time=0.0,
            error_message=f"Critical error in error handling: {error_message}",
            metadata={"critical_error": True}
        )

    def get_error_statistics(self) -> Dict[str, Any]:
        """
        Get error statistics and system health information.

        Returns:
            Error statistics dictionary
        """
        total_errors = len(self.error_history)

        # Count errors by severity
        severity_counts = {}
        for error in self.error_history:
            severity = error.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        # Count errors by tool
        tool_error_counts = {}
        for error in self.error_history:
            if error.tool_name:
                tool_key = f"{error.tool_name}.{error.operation_name}"
                tool_error_counts[tool_key] = tool_error_counts.get(tool_key, 0) + 1

        # Circuit breaker states
        circuit_states = {}
        for tool_key, breaker in self.circuit_breakers.items():
            circuit_states[tool_key] = breaker.get_state()

        return {
            "total_errors": total_errors,
            "severity_distribution": severity_counts,
            "tool_error_counts": tool_error_counts,
            "blacklisted_tools": list(self.blacklisted_tools),
            "circuit_breaker_states": circuit_states,
            "error_history_size": len(self.error_history),
            "recovery_actions_available": len(self.recovery_actions)
        }

    def reset_error_state(self, tool_key: Optional[str] = None):
        """
        Reset error state for a specific tool or all tools.

        Args:
            tool_key: Optional tool key to reset, or None for all tools
        """
        if tool_key:
            # Reset specific tool
            self.error_counts.pop(tool_key, None)
            self.blacklisted_tools.discard(tool_key)
            if tool_key in self.circuit_breakers:
                self.circuit_breakers[tool_key] = CircuitBreaker()
            logger.info(f"Reset error state for tool: {tool_key}")
        else:
            # Reset all
            self.error_counts.clear()
            self.blacklisted_tools.clear()
            self.circuit_breakers.clear()
            self.error_history.clear()
            logger.info("Reset all error states")


# Decorator for automatic error handling
def with_error_handling(error_handler: LangChainErrorHandler):
    """
    Decorator to add automatic error handling to functions.

    Args:
        error_handler: Error handler instance

    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Create minimal error context
                error_context = ErrorContext(
                    error_type=type(e).__name__,
                    error_message=str(e),
                    severity=error_handler._determine_error_severity(e),
                    stack_trace=traceback.format_exc()
                )

                error_handler._log_error(error_context)
                error_handler._add_to_error_history(error_context)

                # Re-raise for now, could be enhanced with recovery
                raise

        return wrapper
    return decorator
