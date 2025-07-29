"""
Executor Interface

Defines the contract for execution engine implementations in the multi-task architecture.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, AsyncGenerator, Callable
from ..models.execution_models import ExecutionContext, ExecutionResult, ExecutionPlan


class IExecutor(ABC):
    """
    Abstract interface for execution engine implementations.

    This interface defines the core contract for executing tasks,
    workflows, and operations in the multi-task system.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the executor.

        Sets up execution environment, resources, and prepares
        the executor for task execution.

        Raises:
            Exception: If initialization fails
        """
        pass

    @abstractmethod
    async def execute_task(
        self,
        task_definition: Dict[str, Any],
        context: ExecutionContext
    ) -> ExecutionResult:
        """
        Execute a single task.

        Args:
            task_definition: Definition of the task to execute
            context: Execution context with metadata and state

        Returns:
            Result of the task execution

        Raises:
            ExecutionError: If task execution fails
        """
        pass

    @abstractmethod
    async def execute_workflow(
        self,
        workflow_definition: Dict[str, Any],
        context: ExecutionContext
    ) -> AsyncGenerator[ExecutionResult, None]:
        """
        Execute a complete workflow.

        Args:
            workflow_definition: Definition of the workflow to execute
            context: Execution context with metadata and state

        Yields:
            ExecutionResult: Results from each step of the workflow

        Raises:
            ExecutionError: If workflow execution fails
        """
        pass

    @abstractmethod
    async def execute_parallel_tasks(
        self,
        task_definitions: List[Dict[str, Any]],
        context: ExecutionContext
    ) -> List[ExecutionResult]:
        """
        Execute multiple tasks in parallel.

        Args:
            task_definitions: List of task definitions to execute
            context: Execution context with metadata and state

        Returns:
            List of execution results in the same order as input tasks

        Raises:
            ExecutionError: If any task execution fails
        """
        pass

    @abstractmethod
    async def execute_conditional(
        self,
        condition: str,
        true_branch: List[Dict[str, Any]],
        false_branch: Optional[List[Dict[str, Any]]],
        context: ExecutionContext
    ) -> List[ExecutionResult]:
        """
        Execute conditional logic.

        Args:
            condition: Condition expression to evaluate
            true_branch: Tasks to execute if condition is true
            false_branch: Tasks to execute if condition is false
            context: Execution context with metadata and state

        Returns:
            List of execution results from the executed branch

        Raises:
            ExecutionError: If conditional execution fails
        """
        pass

    @abstractmethod
    async def execute_dsl_step(
        self,
        step: Dict[str, Any],
        context: ExecutionContext
    ) -> ExecutionResult:
        """
        Execute a Domain Specific Language (DSL) step.

        Args:
            step: DSL step definition
            context: Execution context with metadata and state

        Returns:
            Result of the DSL step execution

        Raises:
            ExecutionError: If DSL step execution fails
        """
        pass

    @abstractmethod
    async def create_execution_plan(
        self,
        workflow_definition: Dict[str, Any]
    ) -> ExecutionPlan:
        """
        Create an execution plan from a workflow definition.

        Args:
            workflow_definition: Definition of the workflow

        Returns:
            Optimized execution plan

        Raises:
            PlanningError: If execution planning fails
        """
        pass

    @abstractmethod
    async def validate_execution_plan(self, plan: ExecutionPlan) -> Dict[str, Any]:
        """
        Validate an execution plan.

        Args:
            plan: Execution plan to validate

        Returns:
            Validation result with status and any error messages

        Raises:
            ValidationError: If validation process fails
        """
        pass

    @abstractmethod
    async def pause_execution(self, execution_id: str) -> bool:
        """
        Pause a running execution.

        Args:
            execution_id: Unique identifier of the execution

        Returns:
            True if execution was successfully paused, False otherwise

        Raises:
            ExecutionNotFoundException: If execution is not found
            ExecutionError: If pause operation fails
        """
        pass

    @abstractmethod
    async def resume_execution(self, execution_id: str) -> bool:
        """
        Resume a paused execution.

        Args:
            execution_id: Unique identifier of the execution

        Returns:
            True if execution was successfully resumed, False otherwise

        Raises:
            ExecutionNotFoundException: If execution is not found
            ExecutionError: If resume operation fails
        """
        pass

    @abstractmethod
    async def cancel_execution(self, execution_id: str, reason: Optional[str] = None) -> bool:
        """
        Cancel a running execution.

        Args:
            execution_id: Unique identifier of the execution
            reason: Optional reason for cancellation

        Returns:
            True if execution was successfully cancelled, False otherwise

        Raises:
            ExecutionNotFoundException: If execution is not found
            ExecutionError: If cancellation fails
        """
        pass

    @abstractmethod
    async def get_execution_status(self, execution_id: str) -> str:
        """
        Get the status of an execution.

        Args:
            execution_id: Unique identifier of the execution

        Returns:
            Current execution status (pending, running, paused, completed, failed, cancelled)

        Raises:
            ExecutionNotFoundException: If execution is not found
            ExecutionError: If status retrieval fails
        """
        pass

    @abstractmethod
    async def get_execution_result(self, execution_id: str) -> Optional[ExecutionResult]:
        """
        Get the result of a completed execution.

        Args:
            execution_id: Unique identifier of the execution

        Returns:
            Execution result if available, None otherwise

        Raises:
            ExecutionNotFoundException: If execution is not found
            ExecutionError: If result retrieval fails
        """
        pass

    @abstractmethod
    async def get_execution_history(self, execution_id: str) -> List[ExecutionResult]:
        """
        Get the execution history for a specific execution.

        Args:
            execution_id: Unique identifier of the execution

        Returns:
            List of execution results representing the history

        Raises:
            ExecutionNotFoundException: If execution is not found
            ExecutionError: If history retrieval fails
        """
        pass

    @abstractmethod
    async def register_execution_hook(
        self,
        hook_type: str,
        hook_func: Callable
    ) -> bool:
        """
        Register an execution hook for custom processing.

        Args:
            hook_type: Type of hook (pre_execution, post_execution, on_error)
            hook_func: Function to call for the hook

        Returns:
            True if hook was successfully registered, False otherwise

        Raises:
            HookRegistrationError: If registration fails
        """
        pass

    @abstractmethod
    async def unregister_execution_hook(
        self,
        hook_type: str,
        hook_func: Callable
    ) -> bool:
        """
        Unregister an execution hook.

        Args:
            hook_type: Type of hook to unregister
            hook_func: Function to unregister

        Returns:
            True if hook was successfully unregistered, False otherwise

        Raises:
            HookNotFoundException: If hook is not found
        """
        pass

    @abstractmethod
    async def get_execution_metrics(self, execution_id: str) -> Dict[str, Any]:
        """
        Get execution metrics for performance monitoring.

        Args:
            execution_id: Unique identifier of the execution

        Returns:
            Dictionary containing execution metrics

        Raises:
            ExecutionNotFoundException: If execution is not found
            ExecutionError: If metrics retrieval fails
        """
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """
        Clean up resources used by the executor.

        This method should be called when the executor is being shut down
        to properly release any held resources.
        """
        pass
