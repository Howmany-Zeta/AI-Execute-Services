import asyncio
import logging
from typing import Dict, List, Any, Optional
from app.tools import get_tool
from app.tools.tool_executor import ToolExecutor
from app.utils.execution_utils import ExecutionUtils
from app.domain.execution.model import TaskStepResult, TaskStatus, ErrorCode

logger = logging.getLogger(__name__)


class OperationExecutor:
    """
    专门处理操作执行的核心逻辑
    """

    def __init__(self, tool_executor: ToolExecutor, execution_utils: ExecutionUtils, config: Dict[str, Any]):
        self.tool_executor = tool_executor
        self.execution_utils = execution_utils
        self.config = config
        self._tool_instances = {}
        self.semaphore = asyncio.Semaphore(config.get('rate_limit_requests_per_second', 5))

    async def execute_operation(self, operation_spec: str, params: Dict[str, Any]) -> Any:
        """
        执行单个操作 (tool_name.operation_name)
        """
        if "." not in operation_spec:
            raise ValueError(f"Invalid operation spec: {operation_spec}, expected 'tool_name.operation_name'")

        tool_name, operation_name = operation_spec.split(".", 1)

        # 获取或创建工具实例
        if tool_name not in self._tool_instances:
            self._tool_instances[tool_name] = get_tool(tool_name)

        tool = self._tool_instances[tool_name]
        if not hasattr(tool, operation_name):
            raise ValueError(f"Operation '{operation_name}' not found in tool '{tool_name}'")

        # 使用 ToolExecutor 执行操作
        operation = getattr(tool, operation_name)
        if asyncio.iscoroutinefunction(operation):
            return await self.tool_executor.execute_async(tool, operation_name, **params)
        else:
            return self.tool_executor.execute(tool, operation_name, **params)

    async def batch_execute_operations(self, operations: List[Dict[str, Any]]) -> List[Any]:
        """
        批量执行操作，带有速率限制
        """
        results = []
        batch_size = self.config.get('batch_size', 10)
        rate_limit = self.config.get('rate_limit_requests_per_second', 5)

        for i in range(0, len(operations), batch_size):
            batch = operations[i:i + batch_size]
            batch_results = await asyncio.gather(
                *[self.execute_operation(op["operation"], op.get("params", {})) for op in batch],
                return_exceptions=True
            )
            results.extend(batch_results)
            await asyncio.sleep(1.0 / rate_limit)

        return results

    async def execute_operations_sequence(self, operations: List[Dict[str, Any]], user_id: str, task_id: str,
                                        stop_on_failure: bool = False, save_callback=None) -> List[TaskStepResult]:
        """
        顺序执行操作序列，可选择在失败时停止
        """
        results = []

        for step, op_info in enumerate(operations):
            operation_spec = op_info.get("operation")
            params = op_info.get("params", {})

            # 处理参数引用
            processed_params = self._process_param_references(params, results)

            try:
                result = await self.execute_operation(operation_spec, processed_params)
                step_result = TaskStepResult(
                    step=operation_spec,
                    result=result,
                    completed=True,
                    message=f"Completed operation {operation_spec}",
                    status=TaskStatus.COMPLETED.value
                )
            except Exception as e:
                step_result = TaskStepResult(
                    step=operation_spec,
                    result=None,
                    completed=False,
                    message=f"Failed to execute {operation_spec}",
                    status=TaskStatus.FAILED.value,
                    error_code=ErrorCode.EXECUTION_ERROR.value,
                    error_message=str(e)
                )

                if stop_on_failure:
                    if save_callback:
                        await save_callback(user_id, task_id, step, step_result)
                    results.append(step_result)
                    break

            # 保存步骤结果
            if save_callback:
                await save_callback(user_id, task_id, step, step_result)

            results.append(step_result)

        return results

    def _process_param_references(self, params: Dict[str, Any], results: List[TaskStepResult]) -> Dict[str, Any]:
        """
        处理参数引用，如 $result[0] 在操作参数中
        """
        processed = {}

        for name, value in params.items():
            if isinstance(value, str) and value.startswith('$result['):
                try:
                    ref_parts = value[8:].split(']', 1)
                    idx = int(ref_parts[0])

                    if idx >= len(results):
                        raise ValueError(f"Referenced result index {idx} out of range")

                    ref_value = results[idx].result

                    # 处理嵌套属性访问，如 $result[0].data.field
                    if len(ref_parts) > 1 and ref_parts[1].startswith('.'):
                        for attr in ref_parts[1][1:].split('.'):
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
        执行批量工具调用，带有速率限制
        """
        results = []
        batch_size = self.config.get('batch_size', 10)
        rate_limit = self.config.get('rate_limit_requests_per_second', 5)

        for i in range(0, len(tool_calls), batch_size):
            batch = tool_calls[i:i + batch_size]
            batch_results = await asyncio.gather(
                *[self._execute_tool_call(call, tool_executor_func) for call in batch],
                return_exceptions=True
            )
            results.extend(batch_results)
            await asyncio.sleep(1.0 / rate_limit)

        return results

    async def _execute_tool_call(self, call: Dict, tool_executor_func=None) -> Any:
        """
        执行单个工具调用，带有速率限制
        """
        async with self.semaphore:
            tool_name = call.get("tool")
            params = call.get("params", {})

            # 使用上下文感知缓存
            if self.config.get('enable_cache', True):
                user_id = params.get("user_id", "anonymous")
                task_id = params.get("task_id", "none")
                cache_key = self.execution_utils.generate_cache_key("tool_call", user_id, task_id, (), params)
                cached_result = self.execution_utils.get_from_cache(cache_key)
                if cached_result is not None:
                    return cached_result

            # 执行工具调用
            if tool_executor_func:
                # 使用提供的工具执行器函数
                result = await tool_executor_func(tool_name, params)
            else:
                # 使用内部 ToolExecutor
                if tool_name not in self._tool_instances:
                    self._tool_instances[tool_name] = get_tool(tool_name)
                tool = self._tool_instances[tool_name]
                result = await self.tool_executor.execute_async(tool, "run", **params)

            # 缓存结果
            if self.config.get('enable_cache', True):
                self.execution_utils.add_to_cache(cache_key, result)

            return result

    def extract_tool_calls(self, description: str, input_data: Dict, context: Dict) -> List[Dict]:
        """
        从描述中提取工具调用
        """
        import re

        tool_calls = []
        tool_pattern = r'\{\{(\w+)\((.*?)\)\}\}'
        matches = re.finditer(tool_pattern, description)

        for match in matches:
            tool_name = match.group(1)
            params_str = match.group(2)
            params = {}

            # 解析参数
            param_pattern = r'(\w+)=["\'](.*?)["\']'
            param_matches = re.finditer(param_pattern, params_str)

            for param_match in param_matches:
                param_name = param_match.group(1)
                param_value = param_match.group(2)

                # 处理输入数据引用
                if param_value.startswith("input."):
                    key = param_value.split(".", 1)[1]
                    param_value = input_data.get(key, "")
                elif param_value.startswith("context."):
                    key = param_value.split(".", 1)[1]
                    param_value = context.get(key, "")

                params[param_name] = param_value

            tool_calls.append({
                "tool": tool_name,
                "params": params
            })

        return tool_calls

    async def execute_parallel_operations(self, operations: List[Dict[str, Any]]) -> List[TaskStepResult]:
        """
        并行执行多个操作
        """
        tasks = []

        for i, op_info in enumerate(operations):
            operation_spec = op_info.get("operation")
            params = op_info.get("params", {})

            async def execute_single_op(spec, p, index):
                try:
                    result = await self.execute_operation(spec, p)
                    return TaskStepResult(
                        step=f"parallel_{index}_{spec}",
                        result=result,
                        completed=True,
                        message=f"Completed parallel operation {spec}",
                        status=TaskStatus.COMPLETED.value
                    )
                except Exception as e:
                    return TaskStepResult(
                        step=f"parallel_{index}_{spec}",
                        result=None,
                        completed=False,
                        message=f"Failed parallel operation {spec}",
                        status=TaskStatus.FAILED.value,
                        error_code=ErrorCode.EXECUTION_ERROR.value,
                        error_message=str(e)
                    )

            tasks.append(execute_single_op(operation_spec, params, i))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理异常结果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(TaskStepResult(
                    step=f"parallel_{i}_error",
                    result=None,
                    completed=False,
                    message=f"Parallel operation failed with exception",
                    status=TaskStatus.FAILED.value,
                    error_code=ErrorCode.EXECUTION_ERROR.value,
                    error_message=str(result)
                ))
            else:
                processed_results.append(result)

        return processed_results

    def get_tool_instance(self, tool_name: str):
        """获取工具实例"""
        if tool_name not in self._tool_instances:
            self._tool_instances[tool_name] = get_tool(tool_name)
        return self._tool_instances[tool_name]

    def clear_tool_cache(self):
        """清理工具实例缓存"""
        self._tool_instances.clear()
        logger.info("Tool instance cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        """获取操作执行器统计信息"""
        return {
            "cached_tools": len(self._tool_instances),
            "tool_names": list(self._tool_instances.keys()),
            "semaphore_value": self.semaphore._value,
            "config": {
                "batch_size": self.config.get('batch_size', 10),
                "rate_limit": self.config.get('rate_limit_requests_per_second', 5),
                "enable_cache": self.config.get('enable_cache', True)
            }
        }
