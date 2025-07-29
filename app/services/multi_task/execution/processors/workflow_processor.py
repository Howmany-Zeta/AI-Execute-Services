"""
Workflow Processor

Handles workflow orchestration, coordination, and execution management.
Provides workflow lifecycle management and execution flow control.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, AsyncGenerator, Set, Tuple, Callable
from datetime import datetime, timedelta
import uuid
from enum import Enum
from dataclasses import dataclass

from ...core.models.execution_models import (
    ExecutionContext, ExecutionResult, ExecutionPlan, ExecutionStatus, ExecutionMode,
    WorkflowStatus, WorkflowType, WorkflowStep, WorkflowExecution
)
from ...core.exceptions.execution_exceptions import ExecutionError, ValidationError
from ...core.interfaces.executor import IExecutor
from .task_processor import TaskProcessor, TaskPriority

logger = logging.getLogger(__name__)


class WorkflowProcessor:
    """
    Workflow processor for handling workflow orchestration and execution.

    This processor provides:
    - Workflow validation and planning
    - Step dependency management
    - Execution flow control
    - Progress tracking and monitoring
    - Error handling and recovery
    - Workflow state management
    """

    def __init__(self, executor: IExecutor, task_processor: Optional[TaskProcessor] = None):
        """
        Initialize the workflow processor.

        Args:
            executor: The executor to use for workflow execution
            task_processor: Task processor for individual task handling
        """
        self.executor = executor
        self.task_processor = task_processor or TaskProcessor(executor)
        self.logger = logging.getLogger(__name__)
        self._active_workflows = {}
        self._workflow_history = {}
        self._workflow_templates = {}
        self._step_handlers = {}

    async def execute_workflow(
        self,
        workflow_definition: Dict[str, Any],
        context: Optional[ExecutionContext] = None,
        plan: Optional[ExecutionPlan] = None
    ) -> AsyncGenerator[ExecutionResult, None]:
        """
        Execute a workflow with full orchestration.

        Args:
            workflow_definition: Workflow definition dictionary
            context: Execution context (created if not provided)
            plan: Execution plan (created if not provided)

        Yields:
            ExecutionResult: Results from each workflow step
        """
        workflow_id = workflow_definition.get('workflow_id', str(uuid.uuid4()))
        execution_id = str(uuid.uuid4())

        # Create context if not provided
        if context is None:
            context = ExecutionContext(
                execution_id=execution_id,
                input_data=workflow_definition.get('input', {}),
                timeout_seconds=workflow_definition.get('timeout', 3600)
            )

        # Create plan if not provided
        if plan is None:
            plan = await self.executor.create_execution_plan(workflow_definition)

        try:
            # Validate workflow
            validation_result = await self._validate_workflow(workflow_definition, plan)
            if not validation_result['valid']:
                error_result = ExecutionResult(
                    execution_id=execution_id,
                    status=ExecutionStatus.FAILED,
                    success=False,
                    message=f"Workflow validation failed: {validation_result['errors']}",
                    error_code="WORKFLOW_VALIDATION_ERROR",
                    error_message=str(validation_result['errors']),
                    started_at=datetime.utcnow(),
                    completed_at=datetime.utcnow()
                )
                yield error_result
                return

            # Create workflow execution
            workflow_execution = await self._create_workflow_execution(
                workflow_id, execution_id, workflow_definition, context, plan
            )

            # Track active workflow
            self._active_workflows[workflow_id] = workflow_execution

            # Execute workflow based on type
            workflow_type = WorkflowType(workflow_definition.get('type', 'sequential'))

            if workflow_type == WorkflowType.SEQUENTIAL:
                async for result in self._execute_sequential_workflow(workflow_execution):
                    yield result
            elif workflow_type == WorkflowType.PARALLEL:
                async for result in self._execute_parallel_workflow(workflow_execution):
                    yield result
            elif workflow_type == WorkflowType.CONDITIONAL:
                async for result in self._execute_conditional_workflow(workflow_execution):
                    yield result
            elif workflow_type == WorkflowType.LOOP:
                async for result in self._execute_loop_workflow(workflow_execution):
                    yield result
            elif workflow_type == WorkflowType.HYBRID:
                async for result in self._execute_hybrid_workflow(workflow_execution):
                    yield result
            else:
                # Default to sequential
                async for result in self._execute_sequential_workflow(workflow_execution):
                    yield result

            # Mark workflow as completed
            workflow_execution.status = WorkflowStatus.COMPLETED
            workflow_execution.completed_at = datetime.utcnow()
            workflow_execution.progress = 1.0

            # Yield final workflow result
            final_result = ExecutionResult(
                execution_id=execution_id,
                status=ExecutionStatus.COMPLETED,
                success=True,
                message=f"Workflow '{workflow_id}' completed successfully",
                result={
                    'workflow_id': workflow_id,
                    'execution_id': execution_id,
                    'steps_completed': len([s for s in workflow_execution.steps.values() if s.status == ExecutionStatus.COMPLETED]),
                    'total_steps': len(workflow_execution.steps),
                    'progress': workflow_execution.progress
                },
                started_at=workflow_execution.started_at,
                completed_at=workflow_execution.completed_at
            )
            yield final_result

        except Exception as e:
            self.logger.error(f"Workflow execution failed for {workflow_id}: {e}")

            # Update workflow status
            if workflow_id in self._active_workflows:
                self._active_workflows[workflow_id].status = WorkflowStatus.FAILED
                self._active_workflows[workflow_id].error_message = str(e)
                self._active_workflows[workflow_id].completed_at = datetime.utcnow()

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

        finally:
            # Move to history and clean up
            if workflow_id in self._active_workflows:
                self._workflow_history[workflow_id] = self._active_workflows[workflow_id]
                del self._active_workflows[workflow_id]

    async def pause_workflow(self, workflow_id: str) -> bool:
        """
        Pause an active workflow.

        Args:
            workflow_id: ID of the workflow to pause

        Returns:
            bool: True if workflow was paused, False if not found
        """
        if workflow_id in self._active_workflows:
            workflow = self._active_workflows[workflow_id]
            if workflow.status == WorkflowStatus.RUNNING:
                workflow.status = WorkflowStatus.PAUSED
                self.logger.info(f"Workflow {workflow_id} paused")
                return True
        return False

    async def resume_workflow(self, workflow_id: str) -> bool:
        """
        Resume a paused workflow.

        Args:
            workflow_id: ID of the workflow to resume

        Returns:
            bool: True if workflow was resumed, False if not found or not paused
        """
        if workflow_id in self._active_workflows:
            workflow = self._active_workflows[workflow_id]
            if workflow.status == WorkflowStatus.PAUSED:
                workflow.status = WorkflowStatus.RUNNING
                self.logger.info(f"Workflow {workflow_id} resumed")
                return True
        return False

    async def cancel_workflow(self, workflow_id: str) -> bool:
        """
        Cancel an active workflow.

        Args:
            workflow_id: ID of the workflow to cancel

        Returns:
            bool: True if workflow was cancelled, False if not found
        """
        if workflow_id in self._active_workflows:
            workflow = self._active_workflows[workflow_id]
            workflow.status = WorkflowStatus.CANCELLED
            workflow.completed_at = datetime.utcnow()

            # Cancel running steps
            for step in workflow.steps.values():
                if step.status == ExecutionStatus.RUNNING:
                    step.status = ExecutionStatus.CANCELLED

            self.logger.info(f"Workflow {workflow_id} cancelled")
            return True
        return False

    async def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a workflow.

        Args:
            workflow_id: ID of the workflow

        Returns:
            Optional[Dict[str, Any]]: Workflow status information or None if not found
        """
        if workflow_id in self._active_workflows:
            workflow = self._active_workflows[workflow_id]
            return {
                'workflow_id': workflow.workflow_id,
                'execution_id': workflow.execution_id,
                'status': workflow.status.value,
                'progress': workflow.progress,
                'started_at': workflow.started_at,
                'steps': {
                    step_id: {
                        'status': step.status.value,
                        'started_at': step.started_at,
                        'completed_at': step.completed_at,
                        'retry_count': step.retry_count
                    }
                    for step_id, step in workflow.steps.items()
                },
                'error_message': workflow.error_message
            }

        if workflow_id in self._workflow_history:
            workflow = self._workflow_history[workflow_id]
            return {
                'workflow_id': workflow.workflow_id,
                'execution_id': workflow.execution_id,
                'status': workflow.status.value,
                'progress': workflow.progress,
                'started_at': workflow.started_at,
                'completed_at': workflow.completed_at,
                'error_message': workflow.error_message
            }

        return None

    async def get_active_workflows(self) -> Dict[str, Dict[str, Any]]:
        """Get all currently active workflows."""
        active_workflows = {}
        for workflow_id in self._active_workflows:
            status = await self.get_workflow_status(workflow_id)
            if status:
                active_workflows[workflow_id] = status
        return active_workflows

    def register_step_handler(
        self,
        step_type: str,
        handler: Callable[[Dict[str, Any], ExecutionContext], ExecutionResult]
    ) -> None:
        """
        Register a custom step handler.

        Args:
            step_type: Step type to handle
            handler: Handler function for the step type
        """
        self._step_handlers[step_type] = handler
        self.logger.info(f"Registered step handler for type: {step_type}")

    async def _create_workflow_execution(
        self,
        workflow_id: str,
        execution_id: str,
        workflow_definition: Dict[str, Any],
        context: ExecutionContext,
        plan: ExecutionPlan
    ) -> WorkflowExecution:
        """Create a workflow execution instance."""
        workflow_type = WorkflowType(workflow_definition.get('type', 'sequential'))

        # Create workflow steps
        steps = {}
        for step_idx, step_def in enumerate(plan.steps):
            step_id = step_def.get('id', f"step_{step_idx}")
            dependencies = set(plan.dependencies.get(step_id, []))

            step = WorkflowStep(
                step_id=step_id,
                step_type=step_def.get('type', 'task'),
                definition=step_def,
                dependencies=dependencies,
                max_retries=step_def.get('max_retries', 3)
            )
            steps[step_id] = step

        return WorkflowExecution(
            workflow_id=workflow_id,
            execution_id=execution_id,
            workflow_type=workflow_type,
            status=WorkflowStatus.RUNNING,
            steps=steps,
            context=context,
            plan=plan,
            started_at=datetime.utcnow()
        )

    async def _execute_sequential_workflow(
        self,
        workflow_execution: WorkflowExecution
    ) -> AsyncGenerator[ExecutionResult, None]:
        """Execute a sequential workflow."""
        steps = list(workflow_execution.steps.values())
        total_steps = len(steps)

        for step_idx, step in enumerate(steps):
            # Check if workflow is paused or cancelled
            if workflow_execution.status in [WorkflowStatus.PAUSED, WorkflowStatus.CANCELLED]:
                break

            # Execute step
            result = await self._execute_workflow_step(step, workflow_execution.context)
            step.result = result

            # Update progress
            workflow_execution.progress = (step_idx + 1) / total_steps

            yield result

            # Stop on failure if not configured to continue
            if not result.success and not step.definition.get('continue_on_failure', False):
                workflow_execution.status = WorkflowStatus.FAILED
                workflow_execution.error_message = result.error_message
                break

    async def _execute_parallel_workflow(
        self,
        workflow_execution: WorkflowExecution
    ) -> AsyncGenerator[ExecutionResult, None]:
        """Execute a parallel workflow."""
        steps = list(workflow_execution.steps.values())
        max_concurrency = workflow_execution.plan.parallel_groups[0] if workflow_execution.plan.parallel_groups else 5

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrency)

        async def execute_step_with_semaphore(step: WorkflowStep) -> ExecutionResult:
            async with semaphore:
                return await self._execute_workflow_step(step, workflow_execution.context)

        # Execute all steps in parallel
        tasks = [execute_step_with_semaphore(step) for step in steps]

        completed = 0
        total_steps = len(steps)

        for coro in asyncio.as_completed(tasks):
            result = await coro
            completed += 1
            workflow_execution.progress = completed / total_steps
            yield result

    async def _execute_conditional_workflow(
        self,
        workflow_execution: WorkflowExecution
    ) -> AsyncGenerator[ExecutionResult, None]:
        """Execute a conditional workflow."""
        # Implementation for conditional workflow execution
        # This would handle if/then/else logic based on step conditions
        async for result in self._execute_sequential_workflow(workflow_execution):
            yield result

    async def _execute_loop_workflow(
        self,
        workflow_execution: WorkflowExecution
    ) -> AsyncGenerator[ExecutionResult, None]:
        """Execute a loop workflow."""
        # Implementation for loop workflow execution
        # This would handle while/for loop logic
        async for result in self._execute_sequential_workflow(workflow_execution):
            yield result

    async def _execute_hybrid_workflow(
        self,
        workflow_execution: WorkflowExecution
    ) -> AsyncGenerator[ExecutionResult, None]:
        """Execute a hybrid workflow."""
        # Implementation for hybrid workflow execution
        # This would combine sequential, parallel, and conditional logic
        async for result in self._execute_sequential_workflow(workflow_execution):
            yield result

    async def _execute_workflow_step(
        self,
        step: WorkflowStep,
        context: ExecutionContext
    ) -> ExecutionResult:
        """Execute a single workflow step."""
        step.status = ExecutionStatus.RUNNING
        step.started_at = datetime.utcnow()

        try:
            # Check for custom step handler
            if step.step_type in self._step_handlers:
                result = await self._step_handlers[step.step_type](step.definition, context)
            else:
                # Use task processor for default execution
                result = await self.task_processor.process_task(step.definition, context)

            step.status = ExecutionStatus.COMPLETED if result.success else ExecutionStatus.FAILED
            step.completed_at = datetime.utcnow()

            return result

        except Exception as e:
            step.status = ExecutionStatus.FAILED
            step.completed_at = datetime.utcnow()

            return ExecutionResult(
                execution_id=context.execution_id,
                status=ExecutionStatus.FAILED,
                success=False,
                message=f"Step execution failed: {str(e)}",
                error_code="STEP_EXECUTION_ERROR",
                error_message=str(e),
                started_at=step.started_at,
                completed_at=step.completed_at
            )

    async def _validate_workflow(
        self,
        workflow_definition: Dict[str, Any],
        plan: ExecutionPlan
    ) -> Dict[str, Any]:
        """Validate a workflow definition and plan."""
        errors = []
        warnings = []

        # Basic validation
        if 'type' not in workflow_definition:
            warnings.append("Workflow type not specified, defaulting to sequential")

        if not plan.steps:
            errors.append("Workflow must have at least one step")

        # Validate step dependencies
        step_ids = {step.get('id', f"step_{i}") for i, step in enumerate(plan.steps)}
        for step_id, deps in plan.dependencies.items():
            for dep in deps:
                if dep not in step_ids:
                    errors.append(f"Step '{step_id}' depends on non-existent step '{dep}'")

        # Validate plan
        plan_validation = await self.executor.validate_execution_plan(plan)
        errors.extend(plan_validation.get('errors', []))
        warnings.extend(plan_validation.get('warnings', []))

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
