"""
DSL Engine

Domain Specific Language execution engine for multi-task workflows.
Handles DSL step execution, conditional logic, and parallel processing.
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, AsyncGenerator, Callable
from datetime import datetime
import uuid

from ..base_executor import BaseExecutor
from ...core.models.execution_models import (
    ExecutionContext, ExecutionResult, ExecutionPlan, ExecutionStatus, ExecutionMode
)
from ...core.exceptions.execution_exceptions import ExecutionError, ValidationError

logger = logging.getLogger(__name__)


class DSLEngine(BaseExecutor):
    """
    DSL execution engine that processes Domain Specific Language workflows.

    This engine is specifically designed to handle the DSL format used by
    the MultiTaskSummarizerRefactored, supporting:
    - Conditional branching: {'if': 'condition', 'then': [steps]}
    - Parallel blocks: {'parallel': [task_names]}
    - Single tasks: {'task': 'task_name', 'tools': ['tool1.operation']}
    """

    def __init__(self, task_executor: Optional[Callable] = None, batch_executor: Optional[Callable] = None):
        """
        Initialize the DSL engine.

        Args:
            task_executor: Function to execute single tasks
            batch_executor: Function to execute batch tasks
        """
        super().__init__()
        self._task_executor = task_executor
        self._batch_executor = batch_executor
        self._supported_dsl_types = {
            'task', 'parallel', 'if', 'sequence', 'condition'
        }

    async def _initialize_executor(self) -> None:
        """Initialize DSL engine specific resources."""
        self.logger.info("DSL Engine initialized")

    async def _cleanup_executor(self) -> None:
        """Cleanup DSL engine specific resources."""
        self.logger.info("DSL Engine cleaned up")

    async def _execute_task_impl(
        self,
        task_definition: Dict[str, Any],
        context: ExecutionContext
    ) -> ExecutionResult:
        """
        Execute a single task using DSL format.

        Args:
            task_definition: DSL task definition
            context: Execution context

        Returns:
            ExecutionResult: Result of task execution
        """
        execution_id = str(uuid.uuid4())
        start_time = datetime.utcnow()

        try:
            # Execute DSL step
            result = await self._execute_dsl_step_impl(task_definition, context)
            return result

        except Exception as e:
            self.logger.error(f"DSL task execution failed: {e}")
            return ExecutionResult(
                execution_id=execution_id,
                status=ExecutionStatus.FAILED,
                success=False,
                message=f"DSL task execution failed: {str(e)}",
                error_code="DSL_TASK_ERROR",
                error_message=str(e),
                started_at=start_time,
                completed_at=datetime.utcnow()
            )

    async def _execute_workflow_impl(
        self,
        workflow_definition: Dict[str, Any],
        context: ExecutionContext,
        plan: ExecutionPlan
    ) -> AsyncGenerator[ExecutionResult, None]:
        """
        Execute a DSL workflow.

        Args:
            workflow_definition: DSL workflow definition
            context: Execution context
            plan: Execution plan

        Yields:
            ExecutionResult: Results from each workflow step
        """
        steps = workflow_definition.get('steps', [])

        for step_idx, step in enumerate(steps):
            try:
                self.logger.info(f"Executing DSL workflow step {step_idx + 1}/{len(steps)}")

                # Execute the step
                result = await self._execute_dsl_step_impl(step, context)

                # Update context with step result
                context.shared_data[f'step_{step_idx}_result'] = result.result

                yield result

            except Exception as e:
                error_result = ExecutionResult(
                    execution_id=str(uuid.uuid4()),
                    step_id=f"step_{step_idx}",
                    status=ExecutionStatus.FAILED,
                    success=False,
                    message=f"DSL workflow step {step_idx} failed: {str(e)}",
                    error_code="DSL_WORKFLOW_STEP_ERROR",
                    error_message=str(e),
                    started_at=datetime.utcnow(),
                    completed_at=datetime.utcnow()
                )
                yield error_result
                break

    async def _execute_dsl_step_impl(
        self,
        step: Dict[str, Any],
        context: ExecutionContext
    ) -> ExecutionResult:
        """
        Execute a single DSL step.

        Args:
            step: DSL step definition
            context: Execution context

        Returns:
            ExecutionResult: Result of step execution
        """
        execution_id = str(uuid.uuid4())
        start_time = datetime.utcnow()

        try:
            # Determine step type and execute accordingly
            if 'task' in step:
                return await self._execute_single_task_step(step, context, execution_id, start_time)
            elif 'parallel' in step:
                return await self._execute_parallel_step(step, context, execution_id, start_time)
            elif 'if' in step:
                return await self._execute_conditional_step(step, context, execution_id, start_time)
            elif 'sequence' in step:
                return await self._execute_sequence_step(step, context, execution_id, start_time)
            else:
                # Try to execute as a generic task
                return await self._execute_generic_step(step, context, execution_id, start_time)

        except Exception as e:
            self.logger.error(f"DSL step execution failed: {e}")
            return ExecutionResult(
                execution_id=execution_id,
                status=ExecutionStatus.FAILED,
                success=False,
                message=f"DSL step execution failed: {str(e)}",
                error_code="DSL_STEP_ERROR",
                error_message=str(e),
                started_at=start_time,
                completed_at=datetime.utcnow()
            )

    async def _execute_single_task_step(
        self,
        step: Dict[str, Any],
        context: ExecutionContext,
        execution_id: str,
        start_time: datetime
    ) -> ExecutionResult:
        """Execute a single task step."""
        task_name = step['task']
        tools = step.get('tools', [])

        if self._task_executor:
            try:
                # Use the provided task executor (from summarizer)
                result = await self._task_executor(
                    task_name,
                    context.input_data,
                    context.shared_data
                )

                return ExecutionResult(
                    execution_id=execution_id,
                    status=ExecutionStatus.COMPLETED,
                    success=True,
                    message=f"Task {task_name} completed successfully",
                    result=result,
                    started_at=start_time,
                    completed_at=datetime.utcnow()
                )

            except Exception as e:
                raise ExecutionError(f"Task executor failed for {task_name}: {e}")
        else:
            # Fallback execution
            return ExecutionResult(
                execution_id=execution_id,
                status=ExecutionStatus.COMPLETED,
                success=True,
                message=f"Task {task_name} executed (fallback)",
                result={'task': task_name, 'tools': tools},
                started_at=start_time,
                completed_at=datetime.utcnow()
            )

    async def _execute_parallel_step(
        self,
        step: Dict[str, Any],
        context: ExecutionContext,
        execution_id: str,
        start_time: datetime
    ) -> ExecutionResult:
        """Execute a parallel step."""
        parallel_tasks = step['parallel']

        if self._batch_executor:
            try:
                # Convert to batch format
                batch_tasks = [{'task': task_name} for task_name in parallel_tasks]

                # Use the provided batch executor
                results = await self._batch_executor(
                    batch_tasks,
                    context.input_data,
                    context.shared_data
                )

                return ExecutionResult(
                    execution_id=execution_id,
                    status=ExecutionStatus.COMPLETED,
                    success=True,
                    message=f"Parallel execution of {len(parallel_tasks)} tasks completed",
                    result={'parallel_results': results},
                    started_at=start_time,
                    completed_at=datetime.utcnow()
                )

            except Exception as e:
                raise ExecutionError(f"Batch executor failed for parallel tasks: {e}")
        else:
            # Fallback: execute sequentially
            results = []
            for task_name in parallel_tasks:
                task_step = {'task': task_name}
                result = await self._execute_single_task_step(
                    task_step, context, f"{execution_id}_{task_name}", start_time
                )
                results.append(result.result)

            return ExecutionResult(
                execution_id=execution_id,
                status=ExecutionStatus.COMPLETED,
                success=True,
                message=f"Sequential execution of {len(parallel_tasks)} tasks completed",
                result={'sequential_results': results},
                started_at=start_time,
                completed_at=datetime.utcnow()
            )

    async def _execute_conditional_step(
        self,
        step: Dict[str, Any],
        context: ExecutionContext,
        execution_id: str,
        start_time: datetime
    ) -> ExecutionResult:
        """Execute a conditional step."""
        condition = step['if']
        then_steps = step.get('then', [])
        else_steps = step.get('else', [])

        try:
            # Evaluate condition
            condition_result = await self._evaluate_condition(condition, context)

            # Choose steps to execute
            steps_to_execute = then_steps if condition_result else else_steps

            if not steps_to_execute:
                return ExecutionResult(
                    execution_id=execution_id,
                    status=ExecutionStatus.COMPLETED,
                    success=True,
                    message=f"Conditional step completed (condition: {condition_result}, no steps to execute)",
                    result={'condition_result': condition_result, 'executed_steps': []},
                    started_at=start_time,
                    completed_at=datetime.utcnow()
                )

            # Execute chosen steps
            results = []
            for step_idx, sub_step in enumerate(steps_to_execute):
                sub_result = await self._execute_dsl_step_impl(sub_step, context)
                results.append(sub_result.result)

            return ExecutionResult(
                execution_id=execution_id,
                status=ExecutionStatus.COMPLETED,
                success=True,
                message=f"Conditional step completed (condition: {condition_result})",
                result={'condition_result': condition_result, 'step_results': results},
                started_at=start_time,
                completed_at=datetime.utcnow()
            )

        except Exception as e:
            raise ExecutionError(f"Conditional step execution failed: {e}")

    async def _execute_sequence_step(
        self,
        step: Dict[str, Any],
        context: ExecutionContext,
        execution_id: str,
        start_time: datetime
    ) -> ExecutionResult:
        """Execute a sequence of steps."""
        sequence_steps = step['sequence']

        results = []
        for step_idx, sub_step in enumerate(sequence_steps):
            try:
                sub_result = await self._execute_dsl_step_impl(sub_step, context)
                results.append(sub_result.result)

                # Update context with intermediate result
                context.shared_data[f'sequence_step_{step_idx}'] = sub_result.result

            except Exception as e:
                self.logger.error(f"Sequence step {step_idx} failed: {e}")
                break

        return ExecutionResult(
            execution_id=execution_id,
            status=ExecutionStatus.COMPLETED,
            success=True,
            message=f"Sequence of {len(results)} steps completed",
            result={'sequence_results': results},
            started_at=start_time,
            completed_at=datetime.utcnow()
        )

    async def _execute_generic_step(
        self,
        step: Dict[str, Any],
        context: ExecutionContext,
        execution_id: str,
        start_time: datetime
    ) -> ExecutionResult:
        """Execute a generic step that doesn't match known patterns."""
        return ExecutionResult(
            execution_id=execution_id,
            status=ExecutionStatus.COMPLETED,
            success=True,
            message="Generic step executed",
            result=step,
            started_at=start_time,
            completed_at=datetime.utcnow()
        )

    async def _create_execution_plan_impl(
        self,
        workflow_definition: Dict[str, Any]
    ) -> ExecutionPlan:
        """Create an execution plan for DSL workflow."""
        plan_id = str(uuid.uuid4())
        workflow_id = workflow_definition.get('workflow_id', str(uuid.uuid4()))

        steps = workflow_definition.get('steps', [])

        # Analyze steps for dependencies and parallelization opportunities
        dependencies = {}
        parallel_groups = []

        for step_idx, step in enumerate(steps):
            step_id = f"step_{step_idx}"

            # Check for parallel blocks
            if 'parallel' in step:
                parallel_group = []
                for task in step['parallel']:
                    parallel_group.append(f"{step_id}_{task}")
                parallel_groups.append(parallel_group)

            # Simple dependency: each step depends on the previous one
            if step_idx > 0:
                dependencies[step_id] = [f"step_{step_idx - 1}"]

        return ExecutionPlan(
            plan_id=plan_id,
            workflow_id=workflow_id,
            steps=steps,
            dependencies=dependencies,
            parallel_groups=parallel_groups,
            execution_mode=ExecutionMode.SEQUENTIAL,
            optimized=True,
            validated=False,
            created_by="dsl_engine"
        )

    async def _validate_execution_plan_impl(self, plan: ExecutionPlan) -> Dict[str, Any]:
        """Validate a DSL execution plan."""
        errors = []

        # Validate steps
        for step_idx, step in enumerate(plan.steps):
            if not isinstance(step, dict):
                errors.append(f"Step {step_idx} is not a dictionary")
                continue

            # Check for valid DSL structure
            valid_keys = {'task', 'parallel', 'if', 'sequence', 'then', 'else', 'tools'}
            step_keys = set(step.keys())

            if not step_keys.intersection({'task', 'parallel', 'if', 'sequence'}):
                errors.append(f"Step {step_idx} missing required DSL key (task, parallel, if, or sequence)")

        # Validate dependencies
        step_ids = {f"step_{i}" for i in range(len(plan.steps))}
        for step_id, deps in plan.dependencies.items():
            if step_id not in step_ids:
                errors.append(f"Dependency references unknown step: {step_id}")
            for dep in deps:
                if dep not in step_ids and not dep.startswith("step_"):
                    errors.append(f"Unknown dependency: {dep}")

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': []
        }

    def set_task_executor(self, executor: Callable) -> None:
        """Set the task executor function."""
        self._task_executor = executor

    def set_batch_executor(self, executor: Callable) -> None:
        """Set the batch executor function."""
        self._batch_executor = executor

    def get_supported_dsl_types(self) -> set:
        """Get supported DSL step types."""
        return self._supported_dsl_types.copy()
