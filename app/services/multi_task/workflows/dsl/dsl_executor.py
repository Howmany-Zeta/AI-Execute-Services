"""
DSL Executor

Executes parsed and validated DSL workflows with support for conditional branching,
parallel execution, loops, and error handling.
"""

import asyncio
from typing import Dict, List, Any, Optional, Callable, Set
import logging
import time
from contextlib import asynccontextmanager

from ...core.models.workflow_models import (
    DSLNode, DSLNodeType, ExecutionState, NodeExecutionContext,
    DSLExecutionContext, ConditionEvaluator, VariableResolver
)
from ...core.interfaces.executor import IExecutor
from ...core.models.execution_models import ExecutionResult, ExecutionStatus, WorkflowExecution
from ...core.exceptions.execution_exceptions import ExecutionError, ExecutionTimeoutError

logger = logging.getLogger(__name__)


class DSLExecutor:
    """
    Executes DSL workflows with support for all DSL constructs.

    Features:
    - Asynchronous execution with proper concurrency control
    - Conditional branching with expression evaluation
    - Parallel execution with configurable concurrency limits
    - Loop execution with break conditions
    - Error handling and retry mechanisms
    - Execution monitoring and cancellation
    - Result propagation and variable substitution
    """

    def __init__(self, task_executor: IExecutor):
        """
        Initialize the DSL executor.

        Args:
            task_executor: Executor for individual tasks
        """
        self.task_executor = task_executor
        self.logger = logger
        self._condition_evaluator = ConditionEvaluator()
        self._variable_resolver = VariableResolver()

    async def execute_workflow(
        self,
        root_node: DSLNode,
        context: DSLExecutionContext,
        timeout: Optional[float] = None
    ) -> ExecutionResult:
        """
        Execute a complete DSL workflow.

        Args:
            root_node: Root node of the DSL tree
            context: Execution context
            timeout: Optional timeout in seconds

        Returns:
            ExecutionResult with workflow execution results
        """
        try:
            self.logger.info(f"Starting DSL workflow execution: {context.workflow_id}")

            # Execute with timeout if specified
            if timeout:
                result = await asyncio.wait_for(
                    self._execute_node(root_node, context),
                    timeout=timeout
                )
            else:
                result = await self._execute_node(root_node, context)

            # Build final execution result
            execution_result = ExecutionResult(
                execution_id=context.execution_id,
                status=ExecutionStatus.COMPLETED if result else ExecutionStatus.FAILED,
                success=True,  # need success status to be True for completed workflows
                message="Workflow completed successfully.", # need message for completed workflows
                result=context.results,  # use context.results dit rectly
                metadata={
                    "workflow_id": context.workflow_id,
                    "total_duration": time.time() - context.start_time,
                    "node_count": len(context.node_contexts),
                    "completed_nodes": len([
                        ctx for ctx in context.node_contexts.values()
                        if ctx.state == ExecutionState.COMPLETED
                    ]),
                    "failed_nodes": len([
                        ctx for ctx in context.node_contexts.values()
                        if ctx.state == ExecutionState.FAILED
                    ])
                }
            )

            self.logger.info(f"DSL workflow execution completed: {context.workflow_id}")
            return execution_result

        except asyncio.TimeoutError:
            self.logger.error(f"DSL workflow execution timed out: {context.workflow_id}")
            context.cancelled = True
            raise ExecutionTimeoutError(f"Workflow execution timed out after {timeout}s")

        except Exception as e:
            self.logger.error(f"DSL workflow execution failed: {context.workflow_id}, error: {e}")
            return ExecutionResult(
                execution_id=context.execution_id,
                status=ExecutionStatus.FAILED,
                success=False, # add success status to be False for failed workflows
                message=f"Workflow failed: {str(e)}", # add message for failed workflows
                error=str(e),
                metadata={
                    "workflow_id": context.workflow_id,
                    "error_type": type(e).__name__
                }
            )

    async def _execute_node(self, node: DSLNode, context: DSLExecutionContext) -> Any:
        """Execute a single DSL node."""
        if context.cancelled:
            return None

        node_context = context.get_node_context(node.node_id)
        node_context.state = ExecutionState.RUNNING
        node_context.start_time = time.time()

        try:
            self.logger.debug(f"Executing node: {node.node_id} ({node.node_type.value})")

            # Execute based on node type
            if node.node_type == DSLNodeType.TASK:
                result = await self._execute_task_node(node, context)
            elif node.node_type == DSLNodeType.SEQUENCE:
                result = await self._execute_sequence_node(node, context)
            elif node.node_type == DSLNodeType.PARALLEL:
                result = await self._execute_parallel_node(node, context)
            elif node.node_type == DSLNodeType.CONDITION:
                result = await self._execute_condition_node(node, context)
            elif node.node_type == DSLNodeType.LOOP:
                result = await self._execute_loop_node(node, context)
            elif node.node_type == DSLNodeType.WAIT:
                result = await self._execute_wait_node(node, context)
            else:
                raise ExecutionError(f"Unknown node type: {node.node_type}")

            # Update node context
            node_context.state = ExecutionState.COMPLETED
            node_context.result = result
            node_context.end_time = time.time()

            # Store result in global context
            context.results[node.node_id] = result

            self.logger.debug(f"Node execution completed: {node.node_id}")
            return result

        except Exception as e:
            node_context.state = ExecutionState.FAILED
            node_context.error = e
            node_context.end_time = time.time()

            self.logger.error(f"Node execution failed: {node.node_id}, error: {e}")

            # Check if we should retry
            max_retries = node.config.get("retry_count", 0)
            if node_context.retry_count < max_retries:
                node_context.retry_count += 1
                self.logger.info(f"Retrying node: {node.node_id} (attempt {node_context.retry_count})")
                await asyncio.sleep(1)  # Brief delay before retry
                return await self._execute_node(node, context)

            raise

    async def _execute_task_node(self, node: DSLNode, context: DSLExecutionContext) -> Any:
        """Execute a task node."""
        task_name = node.config["task_name"]
        tools = node.config.get("tools", [])
        parameters = node.config.get("parameters", {})

        # Resolve variables in parameters
        resolved_parameters = self._variable_resolver.resolve_variables(parameters, context)

        # Execute the task
        task_result = await self.task_executor.execute_task(
            task_name=task_name,
            tools=tools,
            parameters=resolved_parameters
        )

        return task_result

    async def _execute_sequence_node(self, node: DSLNode, context: DSLExecutionContext) -> List[Any]:
        """Execute a sequence node."""
        results = []

        for child in node.children:
            if context.cancelled:
                break

            result = await self._execute_node(child, context)
            results.append(result)

        return results

    async def _execute_parallel_node(self, node: DSLNode, context: DSLExecutionContext) -> List[Any]:
        """Execute a parallel node."""
        max_concurrency = node.config.get("max_concurrency", len(node.children))
        wait_for_all = node.config.get("wait_for_all", True)
        fail_fast = node.config.get("fail_fast", False)

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrency)

        async def execute_with_semaphore(child_node: DSLNode) -> Any:
            async with semaphore:
                return await self._execute_node(child_node, context)

        # Create tasks for all children
        tasks = [
            asyncio.create_task(execute_with_semaphore(child))
            for child in node.children
        ]

        results = []

        if wait_for_all:
            # Wait for all tasks to complete
            if fail_fast:
                # Fail fast: cancel remaining tasks on first failure
                try:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    # Check for exceptions
                    for i, result in enumerate(results):
                        if isinstance(result, Exception):
                            # Cancel remaining tasks
                            for j, task in enumerate(tasks):
                                if j != i and not task.done():
                                    task.cancel()
                            raise result
                except Exception as e:
                    # Cancel all remaining tasks
                    for task in tasks:
                        if not task.done():
                            task.cancel()
                    raise
            else:
                # Collect all results, including exceptions
                results = await asyncio.gather(*tasks, return_exceptions=True)
        else:
            # Return as soon as any task completes
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

            # Cancel pending tasks
            for task in pending:
                task.cancel()

            # Get result from completed task
            completed_task = next(iter(done))
            results = [await completed_task]

        return results

    async def _execute_condition_node(self, node: DSLNode, context: DSLExecutionContext) -> Any:
        """Execute a condition node."""
        condition = node.config["condition"]

        # Evaluate condition
        condition_result = self._condition_evaluator.evaluate(condition, context)

        # Find appropriate branch
        for child in node.children:
            branch_type = child.metadata.get("branch")
            if (condition_result and branch_type == "then") or \
               (not condition_result and branch_type == "else"):
                return await self._execute_node(child, context)

        # No matching branch found
        return None

    async def _execute_loop_node(self, node: DSLNode, context: DSLExecutionContext) -> List[Any]:
        """Execute a loop node."""
        condition = node.config["condition"]
        max_iterations = node.config.get("max_iterations", 100)
        break_on_error = node.config.get("break_on_error", True)

        results = []
        iteration = 0

        while iteration < max_iterations:
            if context.cancelled:
                break

            # Evaluate loop condition
            if not self._condition_evaluator.evaluate(condition, context):
                break

            try:
                # Execute loop body
                iteration_results = []
                for child in node.children:
                    result = await self._execute_node(child, context)
                    iteration_results.append(result)

                results.append(iteration_results)
                iteration += 1

            except Exception as e:
                if break_on_error:
                    self.logger.warning(f"Loop breaking on error: {e}")
                    break
                else:
                    self.logger.warning(f"Loop continuing despite error: {e}")
                    results.append(None)
                    iteration += 1

        return results

    async def _execute_wait_node(self, node: DSLNode, context: DSLExecutionContext) -> bool:
        """Execute a wait node."""
        condition = node.config["condition"]
        timeout = node.config.get("timeout", 30)
        poll_interval = node.config.get("poll_interval", 1)

        start_time = time.time()

        while time.time() - start_time < timeout:
            if context.cancelled:
                return False

            # Check condition
            if self._condition_evaluator.evaluate(condition, context):
                return True

            # Wait before next check
            await asyncio.sleep(poll_interval)

        # Timeout reached
        return False

    async def cancel_execution(self, context: DSLExecutionContext) -> None:
        """Cancel ongoing execution."""
        self.logger.info(f"Cancelling DSL workflow execution: {context.workflow_id}")
        context.cancelled = True

        # Mark running nodes as cancelled
        for node_context in context.node_contexts.values():
            if node_context.state == ExecutionState.RUNNING:
                node_context.state = ExecutionState.CANCELLED


# Classes moved to core.models.workflow_models:
# - DictWrapper
# - ConditionEvaluator
# - VariableResolver
