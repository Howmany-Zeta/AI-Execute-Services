"""
Workflow Orchestrator

Orchestrates the execution of multi-task workflows by coordinating DSL parsing,
validation, and execution with proper error handling and monitoring.
"""

import asyncio
import uuid
from typing import Dict, List, Any, Optional, Callable
import logging
import time

from .base_workflow import IWorkflow, BaseWorkflow
from .dsl import DSLParser, DSLValidator, DSLExecutor
from ..core.models.workflow_models import (
    DSLExecutionContext, ValidationResult, WorkflowExecutionMode,
    WorkflowExecutionRequest, WorkflowExecutionResponse
)
from ..core.interfaces.executor import IExecutor
from ..core.interfaces.task_service import ITaskService
from ..core.models.execution_models import (
    WorkflowExecution, WorkflowStatus, ExecutionResult, ExecutionStatus
)
from ..core.exceptions.execution_exceptions import (
    ExecutionError, ExecutionValidationError, ExecutionTimeoutError
)

logger = logging.getLogger(__name__)


class WorkflowOrchestrator:
    """
    Orchestrates workflow execution with comprehensive management capabilities.

    Features:
    - DSL parsing and validation
    - Execution mode support (validate, dry-run, execute)
    - Concurrent workflow execution
    - Progress monitoring and callbacks
    - Error handling and recovery
    - Resource management
    - Execution history and metrics
    """

    def __init__(
        self,
        task_executor: IExecutor,
        task_service: ITaskService,
        max_concurrent_workflows: int = 10
    ):
        """
        Initialize the workflow orchestrator.

        Args:
            task_executor: Executor for individual tasks
            task_service: Service for task management
            max_concurrent_workflows: Maximum concurrent workflow executions
        """
        self.task_executor = task_executor
        self.task_service = task_service
        self.max_concurrent_workflows = max_concurrent_workflows

        self.logger = logger
        self._dsl_parser = DSLParser()
        self._dsl_validator = DSLValidator()
        self._dsl_executor = DSLExecutor(task_executor)

        # Execution tracking
        self._active_executions: Dict[str, WorkflowExecution] = {}
        self._execution_semaphore = asyncio.Semaphore(max_concurrent_workflows)
        self._execution_callbacks: Dict[str, List[Callable]] = {}

        # Initialize available tasks and tools
        self._initialize_available_resources()

    def _initialize_available_resources(self) -> None:
        """Initialize available tasks and tools for validation."""
        try:
            # Get available tasks from task service
            available_tasks = self.task_service.get_available_tasks()
            task_dict = {task.name: task.to_dict() for task in available_tasks}

            # Get available tools (this would come from tool service)
            # For now, we'll use a basic set
            available_tools = {
                "search.web": {"description": "Web search tool"},
                "search.academic": {"description": "Academic search tool"},
                "file.read": {"description": "File reading tool"},
                "file.write": {"description": "File writing tool"},
                "analysis.text": {"description": "Text analysis tool"},
                "analysis.data": {"description": "Data analysis tool"}
            }

            # Configure parser and validator
            self._dsl_parser.set_available_tasks(list(task_dict.keys()))
            self._dsl_parser.set_available_tools(list(available_tools.keys()))

            self._dsl_validator.set_available_tasks(task_dict)
            self._dsl_validator.set_available_tools(available_tools)
            self._dsl_validator.set_resource_limits({
                "max_execution_duration": 3600,  # 1 hour
                "max_parallel_tasks": 10,
                "max_workflow_depth": 20
            })

        except Exception as e:
            self.logger.warning(f"Failed to initialize available resources: {e}")

    async def execute_workflow(
        self,
        request: WorkflowExecutionRequest
    ) -> WorkflowExecutionResponse:
        """
        Execute a workflow based on the provided request.

        Args:
            request: Workflow execution request

        Returns:
            WorkflowExecutionResponse with execution results
        """
        execution_id = str(uuid.uuid4())
        workflow_id = request.workflow_definition.get("id", str(uuid.uuid4()))
        start_time = time.time()

        self.logger.info(f"Starting workflow execution: {workflow_id} ({execution_id})")

        try:
            # Create workflow execution record
            workflow_execution = WorkflowExecution(
                execution_id=execution_id,
                workflow_id=workflow_id,
                status=WorkflowStatus.RUNNING,
                start_time=start_time,
                parameters=request.parameters,
                metadata=request.metadata
            )

            self._active_executions[execution_id] = workflow_execution

            # Parse DSL
            parse_result = self._dsl_parser.parse(request.workflow_definition.get("steps", []))
            if not parse_result.success:
                raise ExecutionValidationError(f"DSL parsing failed: {parse_result.errors}")

            # Validate DSL
            validation_result = self._dsl_validator.validate(parse_result.root_node)

            # Handle validation-only mode
            if request.execution_mode == WorkflowExecutionMode.VALIDATE_ONLY:
                return WorkflowExecutionResponse(
                    execution_id=execution_id,
                    workflow_id=workflow_id,
                    status=WorkflowStatus.COMPLETED if validation_result.is_valid else WorkflowStatus.FAILED,
                    validation_result=validation_result,
                    execution_time=time.time() - start_time
                )

            # Check validation results
            if not validation_result.is_valid:
                error_messages = [issue.message for issue in validation_result.issues
                                if issue.severity.value == "error"]
                raise ExecutionValidationError(f"Workflow validation failed: {error_messages}")

            # Handle dry-run mode
            if request.execution_mode == WorkflowExecutionMode.DRY_RUN:
                return await self._execute_dry_run(
                    execution_id, workflow_id, parse_result.root_node,
                    validation_result, request, start_time
                )

            # Execute workflow
            return await self._execute_workflow_full(
                execution_id, workflow_id, parse_result.root_node,
                validation_result, request, start_time
            )

        except Exception as e:
            self.logger.error(f"Workflow execution failed: {workflow_id}, error: {e}")

            # Update execution record
            if execution_id in self._active_executions:
                self._active_executions[execution_id].status = WorkflowStatus.FAILED
                self._active_executions[execution_id].error = str(e)
                self._active_executions[execution_id].end_time = time.time()

            return WorkflowExecutionResponse(
                execution_id=execution_id,
                workflow_id=workflow_id,
                status=WorkflowStatus.FAILED,
                error=str(e),
                execution_time=time.time() - start_time
            )

        finally:
            # Cleanup
            if execution_id in self._active_executions:
                del self._active_executions[execution_id]

    async def _execute_dry_run(
        self,
        execution_id: str,
        workflow_id: str,
        root_node,
        validation_result: ValidationResult,
        request: WorkflowExecutionRequest,
        start_time: float
    ) -> WorkflowExecutionResponse:
        """Execute workflow in dry-run mode."""
        self.logger.info(f"Executing workflow dry-run: {workflow_id}")

        # Simulate execution without actually running tasks
        dry_run_result = {
            "execution_plan": validation_result.execution_order,
            "estimated_duration": validation_result.estimated_duration,
            "dependency_graph": validation_result.dependency_graph,
            "validation_issues": [
                {
                    "severity": issue.severity.value,
                    "message": issue.message,
                    "node_id": issue.node_id,
                    "suggestion": issue.suggestion
                }
                for issue in validation_result.issues
            ]
        }

        return WorkflowExecutionResponse(
            execution_id=execution_id,
            workflow_id=workflow_id,
            status=WorkflowStatus.COMPLETED,
            result=dry_run_result,
            validation_result=validation_result,
            execution_time=time.time() - start_time
        )

    async def _execute_workflow_full(
        self,
        execution_id: str,
        workflow_id: str,
        root_node,
        validation_result: ValidationResult,
        request: WorkflowExecutionRequest,
        start_time: float
    ) -> WorkflowExecutionResponse:
        """Execute workflow in full execution mode."""
        async with self._execution_semaphore:
            self.logger.info(f"Executing workflow: {workflow_id}")

            # Create execution context
            execution_context = DSLExecutionContext(
                workflow_id=workflow_id,
                execution_id=execution_id,
                variables=request.parameters.copy()
            )

            # Execute workflow with retry logic
            retry_count = 0
            last_error = None

            while retry_count <= request.max_retries:
                try:
                    # Execute the workflow
                    execution_result = await self._dsl_executor.execute_workflow(
                        root_node=root_node,
                        context=execution_context,
                        timeout=request.timeout
                    )

                    # Update execution record
                    workflow_execution = self._active_executions[execution_id]
                    workflow_execution.status = (
                        WorkflowStatus.COMPLETED if execution_result.status == ExecutionStatus.COMPLETED
                        else WorkflowStatus.FAILED
                    )
                    workflow_execution.result = execution_result.result
                    workflow_execution.end_time = time.time()

                    # Trigger callbacks
                    await self._trigger_callbacks(execution_id, workflow_execution)

                    return WorkflowExecutionResponse(
                        execution_id=execution_id,
                        workflow_id=workflow_id,
                        status=workflow_execution.status,
                        result=execution_result.result,
                        validation_result=validation_result,
                        execution_time=time.time() - start_time,
                        metadata=execution_result.metadata
                    )

                except Exception as e:
                    last_error = e
                    retry_count += 1

                    if retry_count <= request.max_retries:
                        self.logger.warning(
                            f"Workflow execution failed, retrying ({retry_count}/{request.max_retries}): {e}"
                        )
                        await asyncio.sleep(2 ** retry_count)  # Exponential backoff
                    else:
                        self.logger.error(f"Workflow execution failed after {request.max_retries} retries: {e}")
                        raise

            # If we get here, all retries failed
            raise last_error

    async def cancel_workflow(self, execution_id: str) -> bool:
        """
        Cancel a running workflow execution.

        Args:
            execution_id: ID of the execution to cancel

        Returns:
            True if cancellation was successful, False otherwise
        """
        if execution_id not in self._active_executions:
            return False

        try:
            workflow_execution = self._active_executions[execution_id]
            workflow_execution.status = WorkflowStatus.CANCELLED

            # Cancel the DSL execution
            execution_context = DSLExecutionContext(
                workflow_id=workflow_execution.workflow_id,
                execution_id=execution_id
            )
            await self._dsl_executor.cancel_execution(execution_context)

            self.logger.info(f"Workflow execution cancelled: {execution_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to cancel workflow execution {execution_id}: {e}")
            return False

    def get_execution_status(self, execution_id: str) -> Optional[WorkflowExecution]:
        """
        Get the current status of a workflow execution.

        Args:
            execution_id: ID of the execution

        Returns:
            WorkflowExecution object or None if not found
        """
        return self._active_executions.get(execution_id)

    def list_active_executions(self) -> List[WorkflowExecution]:
        """
        List all currently active workflow executions.

        Returns:
            List of active WorkflowExecution objects
        """
        return list(self._active_executions.values())

    def register_execution_callback(
        self,
        execution_id: str,
        callback: Callable[[WorkflowExecution], None]
    ) -> None:
        """
        Register a callback for workflow execution events.

        Args:
            execution_id: ID of the execution
            callback: Callback function to register
        """
        if execution_id not in self._execution_callbacks:
            self._execution_callbacks[execution_id] = []
        self._execution_callbacks[execution_id].append(callback)

    async def _trigger_callbacks(self, execution_id: str, workflow_execution: WorkflowExecution) -> None:
        """Trigger registered callbacks for an execution."""
        callbacks = self._execution_callbacks.get(execution_id, [])

        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(workflow_execution)
                else:
                    callback(workflow_execution)
            except Exception as e:
                self.logger.error(f"Callback execution failed for {execution_id}: {e}")

    def get_execution_metrics(self) -> Dict[str, Any]:
        """
        Get execution metrics and statistics.

        Returns:
            Dictionary containing execution metrics
        """
        active_count = len(self._active_executions)
        status_counts = {}

        for execution in self._active_executions.values():
            status = execution.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "active_executions": active_count,
            "max_concurrent": self.max_concurrent_workflows,
            "available_slots": self.max_concurrent_workflows - active_count,
            "status_distribution": status_counts,
            "semaphore_value": self._execution_semaphore._value
        }
