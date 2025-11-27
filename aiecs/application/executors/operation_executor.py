import asyncio
import logging
from typing import Dict, List, Any
from aiecs.tools import get_tool
from aiecs.tools.tool_executor import ToolExecutor
from aiecs.utils.execution_utils import ExecutionUtils
from aiecs.domain.execution.model import TaskStepResult, TaskStatus, ErrorCode

logger = logging.getLogger(__name__)


class OperationExecutor:
    """
    Core logic for handling operation execution
    """

    def __init__(
        self,
        tool_executor: ToolExecutor,
        execution_utils: ExecutionUtils,
        config: Dict[str, Any],
    ):
        self.tool_executor = tool_executor
        self.execution_utils = execution_utils
        self.config = config
        self._tool_instances: Dict[str, Any] = {}
        self.semaphore = asyncio.Semaphore(config.get("rate_limit_requests_per_second", 5))

    def _filter_tool_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filter out system-related parameters, keeping only parameters needed by tool methods
        """
        # System-related parameters that should not be passed to tool methods
        system_params = {"user_id", "task_id", "op"}
        return {k: v for k, v in params.items() if k not in system_params}

    def _filter_tool_call_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filter out system-related parameters in tool calls, but keep 'op' parameter (needed by BaseTool.run())
        """
        # Only filter user and task IDs, keep 'op' parameter for BaseTool.run()
        # to use
        system_params = {"user_id", "task_id"}
        return {k: v for k, v in params.items() if k not in system_params}

    async def execute_operation(self, operation_spec: str, params: Dict[str, Any]) -> Any:
        """
        Execute a single operation (tool_name.operation_name)
        """
        if "." not in operation_spec:
            raise ValueError(f"Invalid operation spec: {operation_spec}, expected 'tool_name.operation_name'")

        parts = operation_spec.split(".", 1)
        tool_name: str = parts[0]
        operation_name: str = parts[1]

        # Get or create tool instance
        if tool_name not in self._tool_instances:
            self._tool_instances[tool_name] = get_tool(tool_name)

        tool = self._tool_instances[tool_name]
        if not hasattr(tool, operation_name):
            raise ValueError(f"Operation '{operation_name}' not found in tool '{tool_name}'")

        # Filter parameters, remove system-related parameters
        tool_params = self._filter_tool_params(params)

        # Use ToolExecutor to execute operation
        operation = getattr(tool, operation_name)
        if asyncio.iscoroutinefunction(operation):
            return await self.tool_executor.execute_async(tool, operation_name, **tool_params)
        else:
            return self.tool_executor.execute(tool, operation_name, **tool_params)

    async def batch_execute_operations(self, operations: List[Dict[str, Any]]) -> List[Any]:
        """
        Batch execute operations with rate limiting
        """
        results = []
        batch_size = self.config.get("batch_size", 10)
        rate_limit = self.config.get("rate_limit_requests_per_second", 5)

        for i in range(0, len(operations), batch_size):
            batch = operations[i : i + batch_size]
            batch_results = await asyncio.gather(
                *[self.execute_operation(op["operation"], op.get("params", {})) for op in batch],
                return_exceptions=True,
            )
            results.extend(batch_results)
            await asyncio.sleep(1.0 / rate_limit)

        return results

    async def execute_operations_sequence(
        self,
        operations: List[Dict[str, Any]],
        user_id: str,
        task_id: str,
        stop_on_failure: bool = False,
        save_callback=None,
    ) -> List[TaskStepResult]:
        """
        Execute operations sequence sequentially, with option to stop on failure
        """
        results: List[TaskStepResult] = []

        for step, op_info in enumerate(operations):
            operation_spec = op_info.get("operation")
            if not isinstance(operation_spec, str):
                raise ValueError(f"Invalid operation spec: {operation_spec}, expected string")
            params = op_info.get("params", {})

            # Process parameter references
            processed_params = self._process_param_references(params, results)

            try:
                result = await self.execute_operation(operation_spec, processed_params)
                step_result = TaskStepResult(
                    step=operation_spec,
                    result=result,
                    completed=True,
                    message=f"Completed operation {operation_spec}",
                    status=TaskStatus.COMPLETED.value,
                )
            except Exception as e:
                step_result = TaskStepResult(
                    step=operation_spec,
                    result=None,
                    completed=False,
                    message=f"Failed to execute {operation_spec}",
                    status=TaskStatus.FAILED.value,
                    error_code=ErrorCode.EXECUTION_ERROR.value,
                    error_message=str(e),
                )

                if stop_on_failure:
                    if save_callback:
                        await save_callback(user_id, task_id, step, step_result)
                    results.append(step_result)
                    break

            # Save step result
            if save_callback:
                await save_callback(user_id, task_id, step, step_result)

            results.append(step_result)

        return results

    def _process_param_references(self, params: Dict[str, Any], results: List[TaskStepResult]) -> Dict[str, Any]:
        """
        Process parameter references, such as $result[0] in operation parameters
        """
        processed = {}

        for name, value in params.items():
            if isinstance(value, str) and value.startswith("$result["):
                try:
                    ref_parts = value[8:].split("]", 1)
                    idx = int(ref_parts[0])

                    if idx >= len(results):
                        raise ValueError(f"Referenced result index {idx} out of range")

                    ref_value = results[idx].result

                    # Handle nested attribute access, such as
                    # $result[0].data.field
                    if len(ref_parts) > 1 and ref_parts[1].startswith("."):
                        for attr in ref_parts[1][1:].split("."):
                            if attr:
                                if isinstance(ref_value, dict):
                                    ref_value = ref_value.get(attr)
                                else:
                                    ref_value = getattr(ref_value, attr)

                    processed[name] = ref_value
                except Exception as e:
                    logger.error(f"Error processing parameter reference {value}: {e}")
                    processed[name] = value
            else:
                processed[name] = value

        return processed

    async def batch_tool_calls(self, tool_calls: List[Dict], tool_executor_func=None) -> List[Any]:
        """
        Execute batch tool calls with rate limiting
        """
        results = []
        batch_size = self.config.get("batch_size", 10)
        rate_limit = self.config.get("rate_limit_requests_per_second", 5)

        for i in range(0, len(tool_calls), batch_size):
            batch = tool_calls[i : i + batch_size]
            batch_results = await asyncio.gather(
                *[self._execute_tool_call(call, tool_executor_func) for call in batch],
                return_exceptions=True,
            )
            results.extend(batch_results)
            await asyncio.sleep(1.0 / rate_limit)

        return results

    async def _execute_tool_call(self, call: Dict, tool_executor_func=None) -> Any:
        """
        Execute a single tool call with rate limiting
        """
        async with self.semaphore:
            tool_name_raw = call.get("tool")
            if not isinstance(tool_name_raw, str):
                raise ValueError(f"Invalid tool name: {tool_name_raw}, expected string")
            tool_name: str = tool_name_raw
            params = call.get("params", {})

            # Use context-aware caching
            if self.config.get("enable_cache", True):
                user_id = params.get("user_id", "anonymous")
                task_id = params.get("task_id", "none")
                cache_key = self.execution_utils.generate_cache_key("tool_call", user_id, task_id, (), params)
                cached_result = self.execution_utils.get_from_cache(cache_key)
                if cached_result is not None:
                    return cached_result

            # Execute tool call
            if tool_executor_func:
                # Use provided tool executor function
                result = await tool_executor_func(tool_name, params)
            else:
                # Use internal ToolExecutor
                if tool_name not in self._tool_instances:
                    self._tool_instances[tool_name] = get_tool(tool_name)
                tool = self._tool_instances[tool_name]

                # Filter parameters, remove system-related parameters (but keep
                # 'op' parameter)
                tool_params = self._filter_tool_call_params(params)
                # Execute through BaseTool.run method, passing filtered
                # parameters
                result = await self.tool_executor.execute_async(tool, "run", **tool_params)

            # Cache result
            if self.config.get("enable_cache", True):
                self.execution_utils.add_to_cache(cache_key, result)

            return result

    def extract_tool_calls(self, description: str, input_data: Dict, context: Dict) -> List[Dict]:
        """
        Extract tool calls from description
        """
        import re

        tool_calls = []
        tool_pattern = r"\{\{(\w+)\((.*?)\)\}\}"
        matches = re.finditer(tool_pattern, description)

        for match in matches:
            tool_name = match.group(1)
            params_str = match.group(2)
            params = {}

            # Parse parameters
            param_pattern = r'(\w+)=["\'](.*?)["\']'
            param_matches = re.finditer(param_pattern, params_str)

            for param_match in param_matches:
                param_name = param_match.group(1)
                param_value = param_match.group(2)

                # Handle input data references
                if param_value.startswith("input."):
                    key = param_value.split(".", 1)[1]
                    param_value = input_data.get(key, "")
                elif param_value.startswith("context."):
                    key = param_value.split(".", 1)[1]
                    param_value = context.get(key, "")

                params[param_name] = param_value

            tool_calls.append({"tool": tool_name, "params": params})

        return tool_calls

    async def execute_parallel_operations(self, operations: List[Dict[str, Any]]) -> List[TaskStepResult]:
        """
        Execute multiple operations in parallel
        """
        tasks = []

        for i, op_info in enumerate(operations):
            operation_spec = op_info.get("operation")
            if not isinstance(operation_spec, str):
                raise ValueError(f"Invalid operation spec: {operation_spec}, expected string")
            params = op_info.get("params", {})

            async def execute_single_op(spec: str, p: Dict[str, Any], index: int) -> TaskStepResult:
                try:
                    result = await self.execute_operation(spec, p)
                    return TaskStepResult(
                        step=f"parallel_{index}_{spec}",
                        result=result,
                        completed=True,
                        message=f"Completed parallel operation {spec}",
                        status=TaskStatus.COMPLETED.value,
                    )
                except Exception as e:
                    return TaskStepResult(
                        step=f"parallel_{index}_{spec}",
                        result=None,
                        completed=False,
                        message=f"Failed parallel operation {spec}",
                        status=TaskStatus.FAILED.value,
                        error_code=ErrorCode.EXECUTION_ERROR.value,
                        error_message=str(e),
                    )

            tasks.append(execute_single_op(operation_spec, params, i))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exception results
        processed_results: List[TaskStepResult] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    TaskStepResult(
                        step=f"parallel_{i}_error",
                        result=None,
                        completed=False,
                        message="Parallel operation failed with exception",
                        status=TaskStatus.FAILED.value,
                        error_code=ErrorCode.EXECUTION_ERROR.value,
                        error_message=str(result),
                    )
                )
            else:
                # result is TaskStepResult here because execute_single_op always returns TaskStepResult
                assert isinstance(result, TaskStepResult), f"Expected TaskStepResult, got {type(result)}"
                processed_results.append(result)

        return processed_results

    def get_tool_instance(self, tool_name: str):
        """Get tool instance"""
        if tool_name not in self._tool_instances:
            self._tool_instances[tool_name] = get_tool(tool_name)
        return self._tool_instances[tool_name]

    def clear_tool_cache(self):
        """Clear tool instance cache"""
        self._tool_instances.clear()
        logger.info("Tool instance cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        """Get operation executor statistics"""
        return {
            "cached_tools": len(self._tool_instances),
            "tool_names": list(self._tool_instances.keys()),
            "semaphore_value": self.semaphore._value,
            "config": {
                "batch_size": self.config.get("batch_size", 10),
                "rate_limit": self.config.get("rate_limit_requests_per_second", 5),
                "enable_cache": self.config.get("enable_cache", True),
            },
        }
