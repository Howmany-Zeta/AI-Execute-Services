"""
Base Workflow

Abstract base class for all workflow implementations in the multi-task service.
Implements the IWorkflow interface and provides common workflow functionality.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, AsyncGenerator, Callable
import asyncio
import logging
import uuid
from datetime import datetime

from ..core.interfaces.workflow_interfaces import IWorkflow
from ..core.interfaces.executor import IExecutor
from ..core.models.execution_models import (
    ExecutionContext, ExecutionResult, ExecutionPlan, ExecutionStatus, WorkflowExecution,
    WorkflowStep, WorkflowStatus, WorkflowType
)
from ..core.models.task_models import TaskRequest, TaskResponse
from ..core.exceptions.execution_exceptions import (
    ExecutionError, ExecutionValidationError, ExecutionPlanningError
)

logger = logging.getLogger(__name__)


class BaseWorkflow(IWorkflow, ABC):
    """
    Abstract base workflow implementing common workflow functionality.

    This class provides the foundation for all workflow implementations while
    following the Single Responsibility Principle - it handles common
    workflow concerns while delegating specific workflow logic to subclasses.
    """

    def __init__(self, executor: IExecutor):
        """Initialize the base workflow."""
        self.logger = logger
        self.executor = executor
        self._executions: Dict[str, WorkflowExecution] = {}
        self._workflow_hooks: Dict[str, List[Callable]] = {
            'pre_workflow': [],
            'post_workflow': [],
            'pre_step': [],
            'post_step': [],
            'on_error': []
        }
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the workflow."""
        if self._initialized:
            return

        self.logger.info(f"Initializing {self.__class__.__name__}")
        await self._initialize_workflow()
        self._initialized = True
        self.logger.info(f"{self.__class__.__name__} initialized successfully")

    @abstractmethod
    async def _initialize_workflow(self) -> None:
        """Initialize workflow-specific resources. Implemented by subclasses."""
        pass

    async def execute(
        self,
        request: TaskRequest,
        context: ExecutionContext
    ) -> AsyncGenerator[TaskResponse, None]:
        """
        Execute the workflow using the template method pattern.

        Args:
            request: The task request containing workflow definition
            context: Execution context with metadata and state

        Yields:
            TaskResponse: Status updates and results during workflow execution
        """
        execution_id = str(uuid.uuid4())
        start_time = datetime.utcnow()

        try:
            # Create workflow execution
            workflow_execution = await self._create_workflow_execution(
                execution_id, request, context
            )

            # Register execution
            self._register_execution(execution_id, workflow_execution)

            # Execute pre-workflow hooks
            await self._execute_hooks('pre_workflow', request, context)

            # Validate workflow
            validation_result = await self.validate_workflow(request.input_data)
            if not validation_result.get('valid', False):
                raise ExecutionValidationError(
                    f"Invalid workflow: {validation_result.get('errors', [])}",
                    validation_errors=validation_result.get('errors', []),
                    execution_id=execution_id
                )

            # Execute workflow steps
            async for response in self._execute_workflow_impl(
                workflow_execution, request, context
            ):
                yield response

            # Update execution status
            self._update_execution_status(execution_id, WorkflowStatus.COMPLETED)

            # Execute post-workflow hooks
            await self._execute_hooks('post_workflow', request, context, workflow_execution)

        except Exception as e:
            # Update execution status
            self._update_execution_status(execution_id, WorkflowStatus.FAILED)

            # Execute error hooks
            await self._execute_hooks('on_error', request, context, e)

            # Create error response
            error_response = TaskResponse(
                task_id=request.task_id or execution_id,
                status=ExecutionStatus.FAILED,
                message=f"Workflow execution failed: {str(e)}",
                error_code="WORKFLOW_EXECUTION_ERROR",
                error_message=str(e),
                started_at=start_time,
                completed_at=datetime.utcnow()
            )

            self.logger.error(f"Workflow execution failed: {e}")
            yield error_response

    @abstractmethod
    async def _execute_workflow_impl(
        self,
        workflow_execution: WorkflowExecution,
        request: TaskRequest,
        context: ExecutionContext
    ) -> AsyncGenerator[TaskResponse, None]:
        """Execute workflow implementation. Must be implemented by subclasses."""
        pass

    async def validate_workflow(self, workflow_definition: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a workflow definition.

        Args:
            workflow_definition: Definition of the workflow to validate

        Returns:
            Validation result with status and any error messages
        """
        try:
            return await self._validate_workflow_impl(workflow_definition)
        except Exception as e:
            self.logger.error(f"Workflow validation failed: {e}")
            return {
                'valid': False,
                'errors': [f"Validation failed: {str(e)}"]
            }

    @abstractmethod
    async def _validate_workflow_impl(self, workflow_definition: Dict[str, Any]) -> Dict[str, Any]:
        """Validate workflow implementation. Must be implemented by subclasses."""
        pass

    async def pause(self, execution_id: str) -> bool:
        """Pause workflow execution."""
        if execution_id not in self._executions:
            return False

        execution = self._executions[execution_id]
        if execution.status == WorkflowStatus.RUNNING:
            execution.status = WorkflowStatus.PAUSED
            self.logger.info(f"Workflow execution {execution_id} paused")
            return True
        return False

    async def resume(self, execution_id: str) -> bool:
        """Resume workflow execution."""
        if execution_id not in self._executions:
            return False

        execution = self._executions[execution_id]
        if execution.status == WorkflowStatus.PAUSED:
            execution.status = WorkflowStatus.RUNNING
            self.logger.info(f"Workflow execution {execution_id} resumed")
            return True
        return False

    async def cancel(self, execution_id: str, reason: Optional[str] = None) -> bool:
        """Cancel workflow execution."""
        if execution_id not in self._executions:
            return False

        execution = self._executions[execution_id]
        execution.status = WorkflowStatus.CANCELLED
        execution.metadata['cancellation_reason'] = reason
        self.logger.info(f"Workflow execution {execution_id} cancelled: {reason}")
        return True

    async def get_status(self, execution_id: str) -> str:
        """Get workflow execution status."""
        if execution_id not in self._executions:
            raise ExecutionError(f"Workflow execution {execution_id} not found")

        return self._executions[execution_id].status.value

    async def cleanup(self) -> None:
        """Clean up workflow resources."""
        self.logger.info(f"Cleaning up {self.__class__.__name__}")
        await self._cleanup_workflow()
        self._executions.clear()
        self._workflow_hooks.clear()
        self._initialized = False

    @abstractmethod
    async def _cleanup_workflow(self) -> None:
        """Cleanup workflow-specific resources. Implemented by subclasses."""
        pass

    # Helper methods

    async def _create_workflow_execution(
        self,
        execution_id: str,
        request: TaskRequest,
        context: ExecutionContext
    ) -> WorkflowExecution:
        """Create a workflow execution instance."""
        return WorkflowExecution(
            execution_id=execution_id,
            workflow_id=request.workflow_id or execution_id,
            name=request.name or "Unnamed Workflow",
            status=WorkflowStatus.RUNNING,
            execution_mode=WorkflowType.SEQUENTIAL,  # Default, can be overridden
            context=context,
            created_at=datetime.utcnow(),
            started_at=datetime.utcnow()
        )

    def _register_execution(self, execution_id: str, workflow_execution: WorkflowExecution) -> None:
        """Register a new workflow execution."""
        self._executions[execution_id] = workflow_execution

    def _update_execution_status(self, execution_id: str, status: WorkflowStatus) -> None:
        """Update workflow execution status."""
        if execution_id in self._executions:
            self._executions[execution_id].status = status
            if status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED]:
                self._executions[execution_id].completed_at = datetime.utcnow()

    async def _execute_hooks(self, hook_type: str, *args, **kwargs) -> None:
        """Execute registered hooks of a specific type."""
        hooks = self._workflow_hooks.get(hook_type, [])
        for hook in hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(*args, **kwargs)
                else:
                    hook(*args, **kwargs)
            except Exception as e:
                self.logger.error(f"Hook execution failed: {e}")

    async def register_workflow_hook(
        self,
        hook_type: str,
        hook_func: Callable
    ) -> bool:
        """Register a workflow hook for custom processing."""
        if hook_type not in self._workflow_hooks:
            return False

        self._workflow_hooks[hook_type].append(hook_func)
        self.logger.info(f"Registered {hook_type} hook: {hook_func.__name__}")
        return True

    async def unregister_workflow_hook(
        self,
        hook_type: str,
        hook_func: Callable
    ) -> bool:
        """Unregister a workflow hook."""
        if hook_type not in self._workflow_hooks:
            return False

        if hook_func in self._workflow_hooks[hook_type]:
            self._workflow_hooks[hook_type].remove(hook_func)
            self.logger.info(f"Unregistered {hook_type} hook: {hook_func.__name__}")
            return True
        return False

    async def get_execution_metrics(self, execution_id: str) -> Dict[str, Any]:
        """Get workflow execution metrics."""
        if execution_id not in self._executions:
            raise ExecutionError(f"Workflow execution {execution_id} not found")

        execution = self._executions[execution_id]
        return {
            'execution_id': execution_id,
            'workflow_id': execution.workflow_id,
            'status': execution.status.value,
            'progress': execution.progress,
            'created_at': execution.created_at.isoformat(),
            'started_at': execution.started_at.isoformat() if execution.started_at else None,
            'completed_at': execution.completed_at.isoformat() if execution.completed_at else None,
            'step_count': len(execution.steps),
            'completed_steps': len([s for s in execution.step_results.values() if s.status == ExecutionStatus.COMPLETED])
        }
