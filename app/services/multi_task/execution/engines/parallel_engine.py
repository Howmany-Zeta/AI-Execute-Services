"""
Parallel Engine

Optimized parallel execution engine for concurrent task processing.
Handles task scheduling, resource management, and parallel coordination.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, AsyncGenerator, Set, Tuple
from datetime import datetime
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from ..base_executor import BaseExecutor
from ...core.models.execution_models import (
    ExecutionContext, ExecutionResult, ExecutionPlan, ExecutionStatus, ExecutionMode
)
from ...core.exceptions.execution_exceptions import ExecutionError, ValidationError

logger = logging.getLogger(__name__)


@dataclass
class TaskNode:
    """Represents a task node in the execution graph."""
    task_id: str
    task_definition: Dict[str, Any]
    dependencies: Set[str]
    dependents: Set[str]
    status: ExecutionStatus = ExecutionStatus.PENDING
    result: Optional[ExecutionResult] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class ExecutionBatch:
    """Represents a batch of tasks that can be executed in parallel."""
    batch_id: str
    tasks: List[TaskNode]
    max_concurrency: int = 5
    priority: int = 0


class ParallelEngine(BaseExecutor):
    """
    Parallel execution engine for optimized concurrent task processing.

    This engine provides:
    - Dependency-aware task scheduling
    - Resource-constrained parallel execution
    - Dynamic load balancing
    - Execution graph optimization
    - Deadlock detection and prevention
    """

    def __init__(self, max_workers: int = 10, max_concurrent_tasks: int = 5):
        """
        Initialize the Parallel engine.

        Args:
            max_workers: Maximum number of worker threads
            max_concurrent_tasks: Maximum concurrent tasks per batch
        """
        super().__init__()
        self.max_workers = max_workers
        self.max_concurrent_tasks = max_concurrent_tasks
        self._executor = None
        self._execution_graphs = {}
        self._active_batches = {}
        self._resource_locks = {}

    async def _initialize_executor(self) -> None:
        """Initialize Parallel engine specific resources."""
        self._executor = ThreadPoolExecutor(max_workers=self.max_workers)
        self.logger.info(f"Parallel Engine initialized with {self.max_workers} workers")

    async def _cleanup_executor(self) -> None:
        """Cleanup Parallel engine specific resources."""
        if self._executor:
            self._executor.shutdown(wait=True)
            self._executor = None

        self._execution_graphs.clear()
        self._active_batches.clear()
        self._resource_locks.clear()
        self.logger.info("Parallel Engine cleaned up")

    async def _execute_task_impl(
        self,
        task_definition: Dict[str, Any],
        context: ExecutionContext
    ) -> ExecutionResult:
        """
        Execute a single task in parallel context.

        Args:
            task_definition: Task definition
            context: Execution context

        Returns:
            ExecutionResult: Result of task execution
        """
        execution_id = str(uuid.uuid4())
        start_time = datetime.utcnow()

        try:
            # Extract task information
            task_name = task_definition.get('name', 'unnamed_task')
            task_type = task_definition.get('type', 'generic')
            resources = task_definition.get('resources', [])

            # Acquire resources if needed
            acquired_resources = []
            try:
                for resource in resources:
                    await self._acquire_resource(resource)
                    acquired_resources.append(resource)

                # Execute task based on type
                if task_type == 'async':
                    result = await self._execute_async_task(task_definition, context)
                elif task_type == 'sync':
                    result = await self._execute_sync_task(task_definition, context)
                else:
                    result = await self._execute_generic_task(task_definition, context)

                return ExecutionResult(
                    execution_id=execution_id,
                    status=ExecutionStatus.COMPLETED,
                    success=True,
                    message=f"Parallel task '{task_name}' completed successfully",
                    result=result,
                    started_at=start_time,
                    completed_at=datetime.utcnow()
                )

            finally:
                # Release acquired resources
                for resource in acquired_resources:
                    await self._release_resource(resource)

        except Exception as e:
            self.logger.error(f"Parallel task execution failed: {e}")
            return ExecutionResult(
                execution_id=execution_id,
                status=ExecutionStatus.FAILED,
                success=False,
                message=f"Parallel task execution failed: {str(e)}",
                error_code="PARALLEL_TASK_ERROR",
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
        Execute a workflow with optimized parallel processing.

        Args:
            workflow_definition: Workflow definition
            context: Execution context
            plan: Execution plan

        Yields:
            ExecutionResult: Results from each workflow step
        """
        workflow_id = workflow_definition.get('workflow_id', str(uuid.uuid4()))

        try:
            # Build execution graph
            execution_graph = await self._build_execution_graph(workflow_definition, plan)
            self._execution_graphs[workflow_id] = execution_graph

            # Create execution batches
            batches = await self._create_execution_batches(execution_graph)

            # Execute batches in order
            for batch in batches:
                self._active_batches[batch.batch_id] = batch

                try:
                    # Execute batch in parallel
                    async for result in self._execute_batch(batch, context):
                        yield result

                        # Update execution graph
                        await self._update_execution_graph(workflow_id, result)

                finally:
                    # Clean up batch
                    if batch.batch_id in self._active_batches:
                        del self._active_batches[batch.batch_id]

            # Yield final workflow result
            final_result = ExecutionResult(
                execution_id=workflow_id,
                status=ExecutionStatus.COMPLETED,
                success=True,
                message=f"Parallel workflow completed successfully",
                result={'workflow_id': workflow_id, 'batches_executed': len(batches)},
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow()
            )
            yield final_result

        except Exception as e:
            error_result = ExecutionResult(
                execution_id=workflow_id,
                status=ExecutionStatus.FAILED,
                success=False,
                message=f"Parallel workflow execution failed: {str(e)}",
                error_code="PARALLEL_WORKFLOW_ERROR",
                error_message=str(e),
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow()
            )
            yield error_result

        finally:
            # Clean up execution graph
            if workflow_id in self._execution_graphs:
                del self._execution_graphs[workflow_id]

    async def _execute_dsl_step_impl(
        self,
        step: Dict[str, Any],
        context: ExecutionContext
    ) -> ExecutionResult:
        """
        Execute a DSL step with parallel optimization.

        Args:
            step: DSL step definition
            context: Execution context

        Returns:
            ExecutionResult: Result of step execution
        """
        if 'parallel' in step:
            # Handle parallel block
            return await self._execute_parallel_block(step['parallel'], context)
        else:
            # Handle single task with parallel context
            return await self._execute_task_impl(step, context)

    async def _create_execution_plan_impl(
        self,
        workflow_definition: Dict[str, Any]
    ) -> ExecutionPlan:
        """Create an optimized execution plan for parallel processing."""
        plan_id = str(uuid.uuid4())
        workflow_id = workflow_definition.get('workflow_id', str(uuid.uuid4()))

        tasks = workflow_definition.get('tasks', [])
        dependencies = workflow_definition.get('dependencies', {})

        # Analyze task dependencies and create parallel groups
        parallel_groups = await self._analyze_parallelization_opportunities(tasks, dependencies)

        # Optimize execution order
        optimized_steps = await self._optimize_execution_order(tasks, dependencies, parallel_groups)

        return ExecutionPlan(
            plan_id=plan_id,
            workflow_id=workflow_id,
            steps=optimized_steps,
            dependencies=dependencies,
            parallel_groups=parallel_groups,
            execution_mode=ExecutionMode.PARALLEL,
            optimized=True,
            validated=False,
            created_by="parallel_engine"
        )

    async def _validate_execution_plan_impl(self, plan: ExecutionPlan) -> Dict[str, Any]:
        """Validate a parallel execution plan."""
        errors = []
        warnings = []

        # Check for circular dependencies
        circular_deps = await self._detect_circular_dependencies(plan.dependencies)
        if circular_deps:
            errors.extend([f"Circular dependency detected: {dep}" for dep in circular_deps])

        # Check for resource conflicts
        resource_conflicts = await self._detect_resource_conflicts(plan.steps)
        if resource_conflicts:
            warnings.extend([f"Resource conflict detected: {conflict}" for conflict in resource_conflicts])

        # Validate parallel groups
        for group_idx, group in enumerate(plan.parallel_groups):
            if len(group) > self.max_concurrent_tasks:
                warnings.append(f"Parallel group {group_idx} exceeds max concurrent tasks ({self.max_concurrent_tasks})")

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }

    async def _build_execution_graph(
        self,
        workflow_definition: Dict[str, Any],
        plan: ExecutionPlan
    ) -> Dict[str, TaskNode]:
        """Build an execution graph from workflow definition and plan."""
        graph = {}

        for step_idx, step in enumerate(plan.steps):
            task_id = step.get('id', f"task_{step_idx}")
            dependencies = set(plan.dependencies.get(task_id, []))

            node = TaskNode(
                task_id=task_id,
                task_definition=step,
                dependencies=dependencies,
                dependents=set()
            )
            graph[task_id] = node

        # Build dependent relationships
        for task_id, node in graph.items():
            for dep_id in node.dependencies:
                if dep_id in graph:
                    graph[dep_id].dependents.add(task_id)

        return graph

    async def _create_execution_batches(
        self,
        execution_graph: Dict[str, TaskNode]
    ) -> List[ExecutionBatch]:
        """Create execution batches from the execution graph."""
        batches = []
        remaining_tasks = set(execution_graph.keys())
        batch_counter = 0

        while remaining_tasks:
            # Find tasks with no pending dependencies
            ready_tasks = []
            for task_id in remaining_tasks:
                node = execution_graph[task_id]
                if not node.dependencies or all(
                    execution_graph[dep_id].status == ExecutionStatus.COMPLETED
                    for dep_id in node.dependencies
                    if dep_id in execution_graph
                ):
                    ready_tasks.append(node)

            if not ready_tasks:
                # Deadlock detection
                raise ExecutionError(f"Deadlock detected in execution graph. Remaining tasks: {remaining_tasks}")

            # Create batch
            batch = ExecutionBatch(
                batch_id=f"batch_{batch_counter}",
                tasks=ready_tasks,
                max_concurrency=min(len(ready_tasks), self.max_concurrent_tasks),
                priority=batch_counter
            )
            batches.append(batch)

            # Remove tasks from remaining
            for task in ready_tasks:
                remaining_tasks.discard(task.task_id)

            batch_counter += 1

        return batches

    async def _execute_batch(
        self,
        batch: ExecutionBatch,
        context: ExecutionContext
    ) -> AsyncGenerator[ExecutionResult, None]:
        """Execute a batch of tasks in parallel."""
        semaphore = asyncio.Semaphore(batch.max_concurrency)

        async def execute_task_with_semaphore(task_node: TaskNode) -> ExecutionResult:
            async with semaphore:
                task_node.status = ExecutionStatus.RUNNING
                task_node.started_at = datetime.utcnow()

                try:
                    result = await self._execute_task_impl(task_node.task_definition, context)
                    task_node.result = result
                    task_node.status = ExecutionStatus.COMPLETED if result.success else ExecutionStatus.FAILED
                    return result
                finally:
                    task_node.completed_at = datetime.utcnow()

        # Create tasks
        tasks = [execute_task_with_semaphore(task_node) for task_node in batch.tasks]

        # Execute tasks and yield results as they complete
        for coro in asyncio.as_completed(tasks):
            result = await coro
            yield result

    async def _execute_parallel_block(
        self,
        parallel_tasks: List[Dict[str, Any]],
        context: ExecutionContext
    ) -> ExecutionResult:
        """Execute a parallel block of tasks."""
        execution_id = str(uuid.uuid4())
        start_time = datetime.utcnow()

        try:
            # Create semaphore for concurrency control
            semaphore = asyncio.Semaphore(self.max_concurrent_tasks)

            async def execute_with_semaphore(task_def: Dict[str, Any]) -> ExecutionResult:
                async with semaphore:
                    return await self._execute_task_impl(task_def, context)

            # Execute all tasks in parallel
            tasks = [execute_with_semaphore(task_def) for task_def in parallel_tasks]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            successful_results = []
            failed_results = []

            for result in results:
                if isinstance(result, Exception):
                    failed_results.append(str(result))
                elif isinstance(result, ExecutionResult):
                    if result.success:
                        successful_results.append(result)
                    else:
                        failed_results.append(result.error_message or "Unknown error")

            success = len(failed_results) == 0

            return ExecutionResult(
                execution_id=execution_id,
                status=ExecutionStatus.COMPLETED if success else ExecutionStatus.FAILED,
                success=success,
                message=f"Parallel block completed: {len(successful_results)} successful, {len(failed_results)} failed",
                result={
                    'successful_count': len(successful_results),
                    'failed_count': len(failed_results),
                    'results': successful_results,
                    'errors': failed_results
                },
                started_at=start_time,
                completed_at=datetime.utcnow()
            )

        except Exception as e:
            return ExecutionResult(
                execution_id=execution_id,
                status=ExecutionStatus.FAILED,
                success=False,
                message=f"Parallel block execution failed: {str(e)}",
                error_code="PARALLEL_BLOCK_ERROR",
                error_message=str(e),
                started_at=start_time,
                completed_at=datetime.utcnow()
            )

    async def _execute_async_task(
        self,
        task_definition: Dict[str, Any],
        context: ExecutionContext
    ) -> Any:
        """Execute an async task."""
        # Implementation depends on task type
        return {"status": "completed", "type": "async"}

    async def _execute_sync_task(
        self,
        task_definition: Dict[str, Any],
        context: ExecutionContext
    ) -> Any:
        """Execute a sync task in thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self._sync_task_wrapper,
            task_definition,
            context
        )

    def _sync_task_wrapper(
        self,
        task_definition: Dict[str, Any],
        context: ExecutionContext
    ) -> Any:
        """Wrapper for sync task execution."""
        # Implementation depends on task type
        return {"status": "completed", "type": "sync"}

    async def _execute_generic_task(
        self,
        task_definition: Dict[str, Any],
        context: ExecutionContext
    ) -> Any:
        """Execute a generic task."""
        # Implementation depends on task type
        return {"status": "completed", "type": "generic"}

    async def _acquire_resource(self, resource: str) -> None:
        """Acquire a resource lock."""
        if resource not in self._resource_locks:
            self._resource_locks[resource] = asyncio.Lock()
        await self._resource_locks[resource].acquire()

    async def _release_resource(self, resource: str) -> None:
        """Release a resource lock."""
        if resource in self._resource_locks:
            self._resource_locks[resource].release()

    async def _update_execution_graph(
        self,
        workflow_id: str,
        result: ExecutionResult
    ) -> None:
        """Update execution graph with task result."""
        if workflow_id in self._execution_graphs:
            graph = self._execution_graphs[workflow_id]
            # Update task status based on result
            for task_id, node in graph.items():
                if node.result and node.result.execution_id == result.execution_id:
                    node.status = result.status
                    break

    async def _analyze_parallelization_opportunities(
        self,
        tasks: List[Dict[str, Any]],
        dependencies: Dict[str, List[str]]
    ) -> List[List[str]]:
        """Analyze tasks to find parallelization opportunities."""
        parallel_groups = []

        # Simple implementation: group tasks with no dependencies
        independent_tasks = []
        for task_idx, task in enumerate(tasks):
            task_id = task.get('id', f"task_{task_idx}")
            if task_id not in dependencies or not dependencies[task_id]:
                independent_tasks.append(task_id)

        if independent_tasks:
            parallel_groups.append(independent_tasks)

        return parallel_groups

    async def _optimize_execution_order(
        self,
        tasks: List[Dict[str, Any]],
        dependencies: Dict[str, List[str]],
        parallel_groups: List[List[str]]
    ) -> List[Dict[str, Any]]:
        """Optimize task execution order for parallel processing."""
        # For now, return tasks as-is
        # In a full implementation, this would reorder tasks for optimal parallelization
        return tasks

    async def _detect_circular_dependencies(
        self,
        dependencies: Dict[str, List[str]]
    ) -> List[str]:
        """Detect circular dependencies in the dependency graph."""
        visited = set()
        rec_stack = set()
        circular_deps = []

        def dfs(node: str, path: List[str]) -> bool:
            if node in rec_stack:
                # Found a cycle
                cycle_start = path.index(node)
                circular_deps.append(" -> ".join(path[cycle_start:] + [node]))
                return True

            if node in visited:
                return False

            visited.add(node)
            rec_stack.add(node)

            for neighbor in dependencies.get(node, []):
                if dfs(neighbor, path + [node]):
                    return True

            rec_stack.remove(node)
            return False

        for node in dependencies:
            if node not in visited:
                dfs(node, [])

        return circular_deps

    async def _detect_resource_conflicts(
        self,
        tasks: List[Dict[str, Any]]
    ) -> List[str]:
        """Detect potential resource conflicts between tasks."""
        conflicts = []
        resource_usage = {}

        for task_idx, task in enumerate(tasks):
            task_id = task.get('id', f"task_{task_idx}")
            resources = task.get('resources', [])

            for resource in resources:
                if resource in resource_usage:
                    conflicts.append(f"Resource '{resource}' used by both {resource_usage[resource]} and {task_id}")
                else:
                    resource_usage[resource] = task_id

        return conflicts
