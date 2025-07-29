"""
Task Processor

Handles individual task processing, validation, and execution coordination.
Provides task lifecycle management and execution context handling.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable, Union
from datetime import datetime, timedelta
import uuid
from enum import Enum

from ...core.models.execution_models import (
    ExecutionContext, ExecutionResult, ExecutionStatus, ExecutionMode,
    TaskType, TaskPriority
)
from ...core.exceptions.execution_exceptions import ExecutionError, ValidationError
from ...core.interfaces.executor import IExecutor

logger = logging.getLogger(__name__)


class TaskProcessor:
    """
    Task processor for handling individual task execution and management.

    This processor provides:
    - Task validation and preprocessing
    - Execution context management
    - Task lifecycle tracking
    - Error handling and recovery
    - Performance monitoring
    """

    def __init__(self, executor: IExecutor):
        """
        Initialize the task processor.

        Args:
            executor: The executor to use for task execution
        """
        self.executor = executor
        self.logger = logging.getLogger(__name__)
        self._active_tasks = {}
        self._task_history = {}
        self._task_validators = {}
        self._task_transformers = {}
        self._performance_metrics = {}

    async def process_task(
        self,
        task_definition: Dict[str, Any],
        context: Optional[ExecutionContext] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        timeout_seconds: Optional[int] = None
    ) -> ExecutionResult:
        """
        Process a single task with full lifecycle management.

        Args:
            task_definition: Task definition dictionary
            context: Execution context (created if not provided)
            priority: Task priority level
            timeout_seconds: Task timeout in seconds

        Returns:
            ExecutionResult: Result of task execution
        """
        task_id = task_definition.get('id', str(uuid.uuid4()))
        start_time = datetime.utcnow()

        # Create context if not provided
        if context is None:
            context = ExecutionContext(
                execution_id=str(uuid.uuid4()),
                input_data=task_definition.get('input', {}),
                timeout_seconds=timeout_seconds or 300
            )

        try:
            # Track active task
            self._active_tasks[task_id] = {
                'definition': task_definition,
                'context': context,
                'priority': priority,
                'started_at': start_time,
                'status': ExecutionStatus.RUNNING
            }

            # Validate task
            validation_result = await self._validate_task(task_definition)
            if not validation_result['valid']:
                raise ValidationError(f"Task validation failed: {validation_result['errors']}")

            # Transform task if needed
            transformed_task = await self._transform_task(task_definition, context)

            # Execute task with timeout
            if timeout_seconds:
                result = await asyncio.wait_for(
                    self.executor.execute_task(transformed_task, context),
                    timeout=timeout_seconds
                )
            else:
                result = await self.executor.execute_task(transformed_task, context)

            # Post-process result
            processed_result = await self._post_process_result(result, task_definition, context)

            # Update metrics
            await self._update_performance_metrics(task_id, start_time, processed_result)

            # Store in history
            self._task_history[task_id] = {
                'definition': task_definition,
                'result': processed_result,
                'executed_at': start_time,
                'completed_at': datetime.utcnow(),
                'priority': priority
            }

            return processed_result

        except asyncio.TimeoutError:
            error_result = ExecutionResult(
                execution_id=context.execution_id,
                status=ExecutionStatus.TIMED_OUT,
                success=False,
                message=f"Task '{task_id}' timed out after {timeout_seconds} seconds",
                error_code="TASK_TIMEOUT",
                error_message=f"Task execution exceeded {timeout_seconds} seconds",
                started_at=start_time,
                completed_at=datetime.utcnow()
            )

            await self._update_performance_metrics(task_id, start_time, error_result)
            return error_result

        except Exception as e:
            self.logger.error(f"Task processing failed for {task_id}: {e}")
            error_result = ExecutionResult(
                execution_id=context.execution_id,
                status=ExecutionStatus.FAILED,
                success=False,
                message=f"Task processing failed: {str(e)}",
                error_code="TASK_PROCESSING_ERROR",
                error_message=str(e),
                started_at=start_time,
                completed_at=datetime.utcnow()
            )

            await self._update_performance_metrics(task_id, start_time, error_result)
            return error_result

        finally:
            # Remove from active tasks
            if task_id in self._active_tasks:
                del self._active_tasks[task_id]

    async def process_task_batch(
        self,
        task_definitions: List[Dict[str, Any]],
        context: Optional[ExecutionContext] = None,
        max_concurrency: int = 5,
        fail_fast: bool = False
    ) -> List[ExecutionResult]:
        """
        Process a batch of tasks with controlled concurrency.

        Args:
            task_definitions: List of task definitions
            context: Shared execution context
            max_concurrency: Maximum concurrent tasks
            fail_fast: Stop on first failure if True

        Returns:
            List[ExecutionResult]: Results from all tasks
        """
        if not task_definitions:
            return []

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrency)
        results = []

        async def process_with_semaphore(task_def: Dict[str, Any]) -> ExecutionResult:
            async with semaphore:
                return await self.process_task(task_def, context)

        if fail_fast:
            # Process tasks and stop on first failure
            for task_def in task_definitions:
                result = await process_with_semaphore(task_def)
                results.append(result)
                if not result.success:
                    break
        else:
            # Process all tasks concurrently
            tasks = [process_with_semaphore(task_def) for task_def in task_definitions]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Convert exceptions to error results
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    error_result = ExecutionResult(
                        execution_id=str(uuid.uuid4()),
                        status=ExecutionStatus.FAILED,
                        success=False,
                        message=f"Task batch processing failed: {str(result)}",
                        error_code="BATCH_PROCESSING_ERROR",
                        error_message=str(result),
                        started_at=datetime.utcnow(),
                        completed_at=datetime.utcnow()
                    )
                    processed_results.append(error_result)
                else:
                    processed_results.append(result)

            results = processed_results

        return results

    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel an active task.

        Args:
            task_id: ID of the task to cancel

        Returns:
            bool: True if task was cancelled, False if not found
        """
        if task_id in self._active_tasks:
            # Mark as cancelled
            self._active_tasks[task_id]['status'] = ExecutionStatus.CANCELLED

            # Try to cancel in executor if supported
            if hasattr(self.executor, 'cancel_execution'):
                await self.executor.cancel_execution(task_id)

            self.logger.info(f"Task {task_id} cancelled")
            return True

        return False

    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a task.

        Args:
            task_id: ID of the task

        Returns:
            Optional[Dict[str, Any]]: Task status information or None if not found
        """
        if task_id in self._active_tasks:
            task_info = self._active_tasks[task_id].copy()
            task_info['duration'] = datetime.utcnow() - task_info['started_at']
            return task_info

        if task_id in self._task_history:
            return self._task_history[task_id].copy()

        return None

    async def get_active_tasks(self) -> Dict[str, Dict[str, Any]]:
        """Get all currently active tasks."""
        active_tasks = {}
        for task_id, task_info in self._active_tasks.items():
            info = task_info.copy()
            info['duration'] = datetime.utcnow() - info['started_at']
            active_tasks[task_id] = info
        return active_tasks

    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for task processing."""
        return self._performance_metrics.copy()

    def register_task_validator(
        self,
        task_type: Union[TaskType, str],
        validator: Callable[[Dict[str, Any]], Dict[str, Any]]
    ) -> None:
        """
        Register a custom task validator.

        Args:
            task_type: Task type to validate
            validator: Validator function that returns validation result
        """
        task_type_key = task_type.value if isinstance(task_type, TaskType) else task_type
        self._task_validators[task_type_key] = validator
        self.logger.info(f"Registered validator for task type: {task_type_key}")

    def register_task_transformer(
        self,
        task_type: Union[TaskType, str],
        transformer: Callable[[Dict[str, Any], ExecutionContext], Dict[str, Any]]
    ) -> None:
        """
        Register a custom task transformer.

        Args:
            task_type: Task type to transform
            transformer: Transformer function that modifies task definition
        """
        task_type_key = task_type.value if isinstance(task_type, TaskType) else task_type
        self._task_transformers[task_type_key] = transformer
        self.logger.info(f"Registered transformer for task type: {task_type_key}")

    async def _validate_task(self, task_definition: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a task definition."""
        errors = []
        warnings = []

        # Basic validation
        if 'type' not in task_definition:
            errors.append("Task type is required")

        if 'name' not in task_definition:
            warnings.append("Task name is recommended")

        # Type-specific validation
        task_type = task_definition.get('type')
        if task_type in self._task_validators:
            try:
                type_validation = await asyncio.get_event_loop().run_in_executor(
                    None, self._task_validators[task_type], task_definition
                )
                errors.extend(type_validation.get('errors', []))
                warnings.extend(type_validation.get('warnings', []))
            except Exception as e:
                errors.append(f"Validation error: {str(e)}")

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }

    async def _transform_task(
        self,
        task_definition: Dict[str, Any],
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """Transform a task definition before execution."""
        task_type = task_definition.get('type')

        if task_type in self._task_transformers:
            try:
                return await asyncio.get_event_loop().run_in_executor(
                    None, self._task_transformers[task_type], task_definition, context
                )
            except Exception as e:
                self.logger.warning(f"Task transformation failed: {e}")

        return task_definition

    async def _post_process_result(
        self,
        result: ExecutionResult,
        task_definition: Dict[str, Any],
        context: ExecutionContext
    ) -> ExecutionResult:
        """Post-process task execution result."""
        # Add task metadata to result
        if result.result is None:
            result.result = {}

        if isinstance(result.result, dict):
            result.result['task_metadata'] = {
                'task_type': task_definition.get('type'),
                'task_name': task_definition.get('name'),
                'execution_context_id': context.execution_id
            }

        return result

    async def _update_performance_metrics(
        self,
        task_id: str,
        start_time: datetime,
        result: ExecutionResult
    ) -> None:
        """Update performance metrics for task execution."""
        duration = datetime.utcnow() - start_time

        if 'task_executions' not in self._performance_metrics:
            self._performance_metrics['task_executions'] = {
                'total_count': 0,
                'success_count': 0,
                'failure_count': 0,
                'timeout_count': 0,
                'total_duration': timedelta(),
                'average_duration': timedelta(),
                'min_duration': None,
                'max_duration': None
            }

        metrics = self._performance_metrics['task_executions']
        metrics['total_count'] += 1
        metrics['total_duration'] += duration

        if result.success:
            metrics['success_count'] += 1
        elif result.status == ExecutionStatus.TIMED_OUT:
            metrics['timeout_count'] += 1
        else:
            metrics['failure_count'] += 1

        # Update duration statistics
        metrics['average_duration'] = metrics['total_duration'] / metrics['total_count']

        if metrics['min_duration'] is None or duration < metrics['min_duration']:
            metrics['min_duration'] = duration

        if metrics['max_duration'] is None or duration > metrics['max_duration']:
            metrics['max_duration'] = duration
