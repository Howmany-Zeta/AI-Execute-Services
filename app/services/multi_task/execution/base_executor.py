"""
Base Executor

Abstract base class for all execution engines in the multi-task service.
Implements the IExecutor interface and provides common functionality.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, AsyncGenerator, Callable
import asyncio
import logging
from datetime import datetime
import uuid

from ..core.interfaces.executor import IExecutor
from ..core.models.execution_models import (
    ExecutionContext, ExecutionResult, ExecutionPlan, ExecutionStatus, ExecutionMode
)
from ..core.exceptions.execution_exceptions import (
    ExecutionError, ExecutionNotFoundException, PlanningError, ValidationError
)

logger = logging.getLogger(__name__)


class BaseExecutor(IExecutor, ABC):
    """
    Abstract base executor implementing common execution functionality.

    This class provides the foundation for all execution engines while
    following the Single Responsibility Principle - it handles common
    execution concerns while delegating specific execution logic to subclasses.
    """

    def __init__(self):
        """Initialize the base executor."""
        self.logger = logger
        self._executions: Dict[str, Dict[str, Any]] = {}
        self._execution_hooks: Dict[str, List[Callable]] = {
            'pre_execution': [],
            'post_execution': [],
            'on_error': []
        }
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the executor."""
        if self._initialized:
            return

        self.logger.info(f"Initializing {self.__class__.__name__}")
        await self._initialize_executor()
        self._initialized = True
        self.logger.info(f"{self.__class__.__name__} initialized successfully")

    @abstractmethod
    async def _initialize_executor(self) -> None:
        """Initialize executor-specific resources. Implemented by subclasses."""
        pass

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
        """
        execution_id = str(uuid.uuid4())
        start_time = datetime.utcnow()

        try:
            # Register execution
            self._register_execution(execution_id, 'task', context)

            # Execute pre-execution hooks
            await self._execute_hooks('pre_execution', task_definition, context)

            # Execute the task
            result = await self._execute_task_impl(task_definition, context)

            # Update execution status
            self._update_execution_status(execution_id, ExecutionStatus.COMPLETED)

            # Execute post-execution hooks
            await self._execute_hooks('post_execution', task_definition, context, result)

            return result

        except Exception as e:
            # Update execution status
            self._update_execution_status(execution_id, ExecutionStatus.FAILED)

            # Execute error hooks
            await self._execute_hooks('on_error', task_definition, context, e)

            # Create error result
            error_result = ExecutionResult(
                execution_id=execution_id,
                status=ExecutionStatus.FAILED,
                success=False,
                message=f"Task execution failed: {str(e)}",
                error_code="TASK_EXECUTION_ERROR",
                error_message=str(e),
                started_at=start_time,
                completed_at=datetime.utcnow()
            )

            self.logger.error(f"Task execution failed: {e}")
            return error_result

    @abstractmethod
    async def _execute_task_impl(
        self,
        task_definition: Dict[str, Any],
        context: ExecutionContext
    ) -> ExecutionResult:
        """Execute task implementation. Must be implemented by subclasses."""
        pass

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
        """
        execution_id = str(uuid.uuid4())

        try:
            # Register execution
            self._register_execution(execution_id, 'workflow', context)

            # Create execution plan
            plan = await self.create_execution_plan(workflow_definition)

            # Validate plan
            validation_result = await self.validate_execution_plan(plan)
            if not validation_result.get('valid', False):
                raise ValidationError(f"Invalid execution plan: {validation_result.get('errors', [])}")

            # Execute workflow steps
            async for result in self._execute_workflow_impl(workflow_definition, context, plan):
                yield result

        except Exception as e:
            self._update_execution_status(execution_id, ExecutionStatus.FAILED)
            error_result = ExecutionResult(
                execution_id=execution_id,
                status=ExecutionStatus.FAILED,
                success=False,
                message=f"Workflow execution failed: {str(e)}",
                error_code="WORKFLOW_EXECUTION_ERROR",
                error_message=str(e),
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow()
            )
            yield error_result

    @abstractmethod
    async def _execute_workflow_impl(
        self,
        workflow_definition: Dict[str, Any],
        context: ExecutionContext,
        plan: ExecutionPlan
    ) -> AsyncGenerator[ExecutionResult, None]:
        """Execute workflow implementation. Must be implemented by subclasses."""
        pass

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
        """
        execution_id = str(uuid.uuid4())

        try:
            # Register execution
            self._register_execution(execution_id, 'parallel_tasks', context)

            # Execute tasks in parallel
            tasks = [
                self._execute_task_impl(task_def, context)
                for task_def in task_definitions
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results and handle exceptions
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    error_result = ExecutionResult(
                        execution_id=f"{execution_id}_task_{i}",
                        status=ExecutionStatus.FAILED,
                        success=False,
                        message=f"Parallel task {i} failed: {str(result)}",
                        error_code="PARALLEL_TASK_ERROR",
                        error_message=str(result),
                        started_at=datetime.utcnow(),
                        completed_at=datetime.utcnow()
                    )
                    processed_results.append(error_result)
                else:
                    processed_results.append(result)

            self._update_execution_status(execution_id, ExecutionStatus.COMPLETED)
            return processed_results

        except Exception as e:
            self._update_execution_status(execution_id, ExecutionStatus.FAILED)
            self.logger.error(f"Parallel execution failed: {e}")
            raise ExecutionError(f"Parallel execution failed: {e}")

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
        """
        try:
            # Evaluate condition
            condition_result = await self._evaluate_condition(condition, context)

            # Choose branch to execute
            branch_to_execute = true_branch if condition_result else false_branch

            if branch_to_execute is None:
                return []

            # Execute chosen branch
            return await self.execute_parallel_tasks(branch_to_execute, context)

        except Exception as e:
            self.logger.error(f"Conditional execution failed: {e}")
            raise ExecutionError(f"Conditional execution failed: {e}")

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
        """
        try:
            return await self._execute_dsl_step_impl(step, context)
        except Exception as e:
            self.logger.error(f"DSL step execution failed: {e}")
            raise ExecutionError(f"DSL step execution failed: {e}")

    @abstractmethod
    async def _execute_dsl_step_impl(
        self,
        step: Dict[str, Any],
        context: ExecutionContext
    ) -> ExecutionResult:
        """Execute DSL step implementation. Must be implemented by subclasses."""
        pass

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
        """
        try:
            return await self._create_execution_plan_impl(workflow_definition)
        except Exception as e:
            self.logger.error(f"Execution plan creation failed: {e}")
            raise PlanningError(f"Execution plan creation failed: {e}")

    @abstractmethod
    async def _create_execution_plan_impl(
        self,
        workflow_definition: Dict[str, Any]
    ) -> ExecutionPlan:
        """Create execution plan implementation. Must be implemented by subclasses."""
        pass

    async def validate_execution_plan(self, plan: ExecutionPlan) -> Dict[str, Any]:
        """
        Validate an execution plan.

        Args:
            plan: Execution plan to validate

        Returns:
            Validation result with status and any error messages
        """
        try:
            return await self._validate_execution_plan_impl(plan)
        except Exception as e:
            self.logger.error(f"Execution plan validation failed: {e}")
            return {
                'valid': False,
                'errors': [f"Validation failed: {str(e)}"]
            }

    @abstractmethod
    async def _validate_execution_plan_impl(self, plan: ExecutionPlan) -> Dict[str, Any]:
        """Validate execution plan implementation. Must be implemented by subclasses."""
        pass

    # Execution management methods

    async def pause_execution(self, execution_id: str) -> bool:
        """Pause a running execution."""
        if execution_id not in self._executions:
            raise ExecutionNotFoundException(f"Execution {execution_id} not found")

        execution = self._executions[execution_id]
        if execution['status'] == ExecutionStatus.RUNNING:
            execution['status'] = ExecutionStatus.PAUSED
            self.logger.info(f"Execution {execution_id} paused")
            return True
        return False

    async def resume_execution(self, execution_id: str) -> bool:
        """Resume a paused execution."""
        if execution_id not in self._executions:
            raise ExecutionNotFoundException(f"Execution {execution_id} not found")

        execution = self._executions[execution_id]
        if execution['status'] == ExecutionStatus.PAUSED:
            execution['status'] = ExecutionStatus.RUNNING
            self.logger.info(f"Execution {execution_id} resumed")
            return True
        return False

    async def cancel_execution(self, execution_id: str, reason: Optional[str] = None) -> bool:
        """Cancel a running execution."""
        if execution_id not in self._executions:
            raise ExecutionNotFoundException(f"Execution {execution_id} not found")

        execution = self._executions[execution_id]
        execution['status'] = ExecutionStatus.CANCELLED
        execution['cancellation_reason'] = reason
        self.logger.info(f"Execution {execution_id} cancelled: {reason}")
        return True

    async def get_execution_status(self, execution_id: str) -> str:
        """Get the status of an execution."""
        if execution_id not in self._executions:
            raise ExecutionNotFoundException(f"Execution {execution_id} not found")

        return self._executions[execution_id]['status'].value

    async def get_execution_result(self, execution_id: str) -> Optional[ExecutionResult]:
        """Get the result of a completed execution."""
        if execution_id not in self._executions:
            raise ExecutionNotFoundException(f"Execution {execution_id} not found")

        return self._executions[execution_id].get('result')

    async def get_execution_history(self, execution_id: str) -> List[ExecutionResult]:
        """Get the execution history for a specific execution."""
        if execution_id not in self._executions:
            raise ExecutionNotFoundException(f"Execution {execution_id} not found")

        return self._executions[execution_id].get('history', [])

    # Hook management

    async def register_execution_hook(
        self,
        hook_type: str,
        hook_func: Callable
    ) -> bool:
        """Register an execution hook for custom processing."""
        if hook_type not in self._execution_hooks:
            return False

        self._execution_hooks[hook_type].append(hook_func)
        self.logger.info(f"Registered {hook_type} hook: {hook_func.__name__}")
        return True

    async def unregister_execution_hook(
        self,
        hook_type: str,
        hook_func: Callable
    ) -> bool:
        """Unregister an execution hook."""
        if hook_type not in self._execution_hooks:
            return False

        if hook_func in self._execution_hooks[hook_type]:
            self._execution_hooks[hook_type].remove(hook_func)
            self.logger.info(f"Unregistered {hook_type} hook: {hook_func.__name__}")
            return True
        return False

    async def get_execution_metrics(self, execution_id: str) -> Dict[str, Any]:
        """Get execution metrics for performance monitoring."""
        if execution_id not in self._executions:
            raise ExecutionNotFoundException(f"Execution {execution_id} not found")

        execution = self._executions[execution_id]
        return {
            'execution_id': execution_id,
            'status': execution['status'].value,
            'type': execution['type'],
            'created_at': execution['created_at'].isoformat(),
            'metrics': execution.get('metrics', {})
        }

    async def cleanup(self) -> None:
        """Clean up resources used by the executor."""
        self.logger.info(f"Cleaning up {self.__class__.__name__}")
        await self._cleanup_executor()
        self._executions.clear()
        self._execution_hooks.clear()
        self._initialized = False

    @abstractmethod
    async def _cleanup_executor(self) -> None:
        """Cleanup executor-specific resources. Implemented by subclasses."""
        pass

    # Helper methods

    def _register_execution(self, execution_id: str, execution_type: str, context: ExecutionContext) -> None:
        """Register a new execution."""
        self._executions[execution_id] = {
            'id': execution_id,
            'type': execution_type,
            'status': ExecutionStatus.RUNNING,
            'context': context,
            'created_at': datetime.utcnow(),
            'history': [],
            'metrics': {}
        }

    def _update_execution_status(self, execution_id: str, status: ExecutionStatus) -> None:
        """Update execution status."""
        if execution_id in self._executions:
            self._executions[execution_id]['status'] = status

    async def _execute_hooks(self, hook_type: str, *args, **kwargs) -> None:
        """Execute registered hooks of a specific type."""
        hooks = self._execution_hooks.get(hook_type, [])
        for hook in hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(*args, **kwargs)
                else:
                    hook(*args, **kwargs)
            except Exception as e:
                self.logger.error(f"Hook execution failed: {e}")

    async def _evaluate_condition(self, condition: str, context: ExecutionContext) -> bool:
        """Evaluate a condition expression."""
        # Basic condition evaluation - can be extended for complex expressions
        try:
            # Simple variable substitution from context
            variables = context.variables
            for var_name, var_value in variables.items():
                condition = condition.replace(f"${var_name}", str(var_value))

            # Evaluate the condition (basic implementation)
            return eval(condition)
        except Exception as e:
            self.logger.error(f"Condition evaluation failed: {e}")
            return False
