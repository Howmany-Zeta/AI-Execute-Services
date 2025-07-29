import re
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional, Callable
from app.domain.execution.model import TaskStepResult, TaskStatus, ErrorCode

logger = logging.getLogger(__name__)


class DSLProcessor:
    """
    Specialized DSL (Domain Specific Language) parsing and execution processor
    """

    def __init__(self, tracer=None):
        self.tracer = tracer
        # 更新支持的条件模式，使用更严格的匹配
        self.supported_conditions = [
            r"intent\.includes\('([^']+)'\)",
            r"context\.(\w+)\s*(==|!=|>|<|>=|<=)\s*(.+)",
            r"input\.(\w+)\s*(==|!=|>|<|>=|<=)\s*(.+)",
            r"result\[(\d+)\]\.(\w+)\s*(==|!=|>|<|>=|<=)\s*(.+)"
        ]
        # 条件检查优先级顺序
        self.condition_check_order = [
            "AND",  # 逻辑AND操作
            "OR",   # 逻辑OR操作
            "intent.includes",  # 意图包含检查
            "context",  # 上下文检查
            "input",    # 输入检查
            "result"    # 结果检查
        ]

    def evaluate_condition(self, condition: str, intent_categories: List[str],
                          context: Dict[str, Any] = None, input_data: Dict[str, Any] = None,
                          results: List[TaskStepResult] = None) -> bool:
        """
        评估条件表达式，支持多种条件类型
        按照优化后的检查顺序：AND -> OR -> intent.includes -> context -> input -> result
        """
        try:
            # 1. 复合条件: 支持 AND (优先级最高)
            if " AND " in condition:
                parts = condition.split(" AND ")
                return all(self.evaluate_condition(part.strip(), intent_categories, context, input_data, results) for part in parts)

            # 2. 复合条件: 支持 OR (第二优先级)
            if " OR " in condition:
                parts = condition.split(" OR ")
                return any(self.evaluate_condition(part.strip(), intent_categories, context, input_data, results) for part in parts)

            # 3. Intent 条件: intent.includes('category')
            match = re.fullmatch(r"intent\.includes\('([^']+)'\)", condition)
            if match:
                category = match.group(1)
                return category in intent_categories

            # 4. Context 条件: context.field == value
            match = re.fullmatch(r"context\.(\w+)\s*(==|!=|>|<|>=|<=)\s*(.+)", condition)
            if match and context:
                field, operator, value = match.groups()
                return self._evaluate_comparison(context.get(field), operator, self._parse_value(value))

            # 5. Input 条件: input.field == value
            match = re.fullmatch(r"input\.(\w+)\s*(==|!=|>|<|>=|<=)\s*(.+)", condition)
            if match and input_data:
                field, operator, value = match.groups()
                return self._evaluate_comparison(input_data.get(field), operator, self._parse_value(value))

            # 6. Result 条件: result[0].field == value
            match = re.fullmatch(r"result\[(\d+)\]\.(\w+)\s*(==|!=|>|<|>=|<=)\s*(.+)", condition)
            if match and results:
                index, field, operator, value = match.groups()
                index = int(index)
                if index < len(results) and results[index].result:
                    result_value = results[index].result.get(field) if isinstance(results[index].result, dict) else None
                    return self._evaluate_comparison(result_value, operator, self._parse_value(value))

            raise ValueError(f"Unsupported condition format: {condition}")

        except Exception as e:
            logger.error(f"Failed to evaluate condition '{condition}': {e}")
            raise ValueError(f"Failed to evaluate condition '{condition}': {e}")

    def _evaluate_comparison(self, left_value: Any, operator: str, right_value: Any) -> bool:
        """评估比较操作"""
        try:
            if operator == "==":
                return left_value == right_value
            elif operator == "!=":
                return left_value != right_value
            elif operator == ">":
                return left_value > right_value
            elif operator == "<":
                return left_value < right_value
            elif operator == ">=":
                return left_value >= right_value
            elif operator == "<=":
                return left_value <= right_value
            else:
                raise ValueError(f"Unsupported operator: {operator}")
        except TypeError:
            # 类型不匹配时返回 False
            return False

    def _parse_value(self, value_str: str) -> Any:
        """解析值字符串为适当的类型"""
        value_str = value_str.strip()

        # 字符串值
        if value_str.startswith('"') and value_str.endswith('"'):
            return value_str[1:-1]
        if value_str.startswith("'") and value_str.endswith("'"):
            return value_str[1:-1]

        # 布尔值
        if value_str.lower() == "true":
            return True
        if value_str.lower() == "false":
            return False

        # 数字值
        try:
            if "." in value_str:
                return float(value_str)
            else:
                return int(value_str)
        except ValueError:
            pass

        # 默认返回字符串
        return value_str

    def validate_condition_syntax(self, condition: str) -> bool:
        """验证条件语法的有效性"""
        if not condition or not isinstance(condition, str):
            return False

        condition = condition.strip()
        if not condition:
            return False

        # 检查是否匹配任何支持的条件模式
        for pattern in self.supported_conditions:
            if re.fullmatch(pattern, condition):
                return True

        # 检查复合条件
        if " AND " in condition or " OR " in condition:
            return True

        return False

    async def execute_dsl_step(self, step: Dict, intent_categories: List[str], input_data: Dict,
                              context: Dict, execute_single_task: Callable, execute_batch_task: Callable,
                              results: List[TaskStepResult] = None) -> TaskStepResult:
        """
        执行 DSL 步骤，基于步骤类型 (if, parallel, task, sequence)
        """
        span = self.tracer.start_span("execute_dsl_step") if self.tracer else None
        if span:
            span.set_tag("step", json.dumps(step))

        try:
            if "if" in step:
                return await self._handle_if_step(step, intent_categories, input_data, context,
                                                execute_single_task, execute_batch_task, span, results)
            elif "parallel" in step:
                return await self._handle_parallel_step(step, input_data, context, execute_batch_task, span)
            elif "sequence" in step:
                return await self._handle_sequence_step(step, intent_categories, input_data, context,
                                                      execute_single_task, execute_batch_task, span, results)
            elif "task" in step:
                return await self._handle_task_step(step, input_data, context, execute_single_task, span)
            elif "loop" in step:
                return await self._handle_loop_step(step, intent_categories, input_data, context,
                                                  execute_single_task, execute_batch_task, span, results)
            else:
                if span:
                    span.set_tag("error", True)
                    span.log_kv({"error_message": "Invalid DSL step"})
                return TaskStepResult(
                    step="unknown",
                    result=None,
                    completed=False,
                    message="Invalid DSL step",
                    status=TaskStatus.FAILED.value,
                    error_code=ErrorCode.EXECUTION_ERROR.value,
                    error_message="Unknown DSL step type"
                )
        finally:
            if span:
                span.finish()

    async def _handle_if_step(self, step: Dict, intent_categories: List[str], input_data: Dict,
                             context: Dict, execute_single_task: Callable, execute_batch_task: Callable,
                             span=None, results: List[TaskStepResult] = None) -> TaskStepResult:
        """处理条件 'if' 步骤"""
        condition = step["if"]
        then_steps = step["then"]
        else_steps = step.get("else", [])

        if span:
            span.set_tag("condition", condition)

        try:
            condition_result = self.evaluate_condition(condition, intent_categories, context, input_data, results)

            if condition_result:
                if span:
                    span.log_kv({"condition_result": "true"})

                step_results = []
                for sub_step in then_steps:
                    result = await self.execute_dsl_step(sub_step, intent_categories, input_data, context,
                                                       execute_single_task, execute_batch_task, results)
                    step_results.append(result)
                    if results is not None:
                        results.append(result)

                return TaskStepResult(
                    step=f"if_{condition}",
                    result=[r.dict() for r in step_results],
                    completed=all(r.completed for r in step_results),
                    message=f"Condition '{condition}' evaluated to true",
                    status=TaskStatus.COMPLETED.value if all(r.status == TaskStatus.COMPLETED.value for r in step_results) else TaskStatus.FAILED.value
                )
            else:
                if span:
                    span.log_kv({"condition_result": "false"})

                if else_steps:
                    step_results = []
                    for sub_step in else_steps:
                        result = await self.execute_dsl_step(sub_step, intent_categories, input_data, context,
                                                           execute_single_task, execute_batch_task, results)
                        step_results.append(result)
                        if results is not None:
                            results.append(result)

                    return TaskStepResult(
                        step=f"if_{condition}_else",
                        result=[r.dict() for r in step_results],
                        completed=all(r.completed for r in step_results),
                        message=f"Condition '{condition}' evaluated to false, executed else branch",
                        status=TaskStatus.COMPLETED.value if all(r.status == TaskStatus.COMPLETED.value for r in step_results) else TaskStatus.FAILED.value
                    )
                else:
                    return TaskStepResult(
                        step=f"if_{condition}",
                        result=None,
                        completed=True,
                        message=f"Condition '{condition}' evaluated to false, skipping",
                        status=TaskStatus.COMPLETED.value
                    )
        except Exception as e:
            if span:
                span.set_tag("error", True)
                span.log_kv({"error_message": str(e)})
            return TaskStepResult(
                step=f"if_{condition}",
                result=None,
                completed=False,
                message="Failed to evaluate condition",
                status=TaskStatus.FAILED.value,
                error_code=ErrorCode.DSL_EVALUATION_ERROR.value,
                error_message=str(e)
            )

    async def _handle_parallel_step(self, step: Dict, input_data: Dict, context: Dict,
                                   execute_batch_task: Callable, span=None) -> TaskStepResult:
        """处理并行任务执行"""
        task_names = step["parallel"]
        if span:
            span.set_tag("parallel_tasks", task_names)

        batch_tasks = [{"category": "process", "task": task_name} for task_name in task_names]
        batch_results = await execute_batch_task(batch_tasks, input_data, context)

        return TaskStepResult(
            step=f"parallel_{'_'.join(task_names)}",
            result=[r.dict() for r in batch_results],
            completed=all(r.completed for r in batch_results),
            message=f"Completed parallel execution of {len(task_names)} tasks",
            status=TaskStatus.COMPLETED.value if all(r.status == TaskStatus.COMPLETED.value for r in batch_results) else TaskStatus.FAILED.value
        )

    async def _handle_sequence_step(self, step: Dict, intent_categories: List[str], input_data: Dict,
                                   context: Dict, execute_single_task: Callable, execute_batch_task: Callable,
                                   span=None, results: List[TaskStepResult] = None) -> TaskStepResult:
        """处理顺序执行步骤"""
        sequence_steps = step["sequence"]
        if span:
            span.set_tag("sequence_length", len(sequence_steps))

        step_results = []
        for i, sub_step in enumerate(sequence_steps):
            result = await self.execute_dsl_step(sub_step, intent_categories, input_data, context,
                                               execute_single_task, execute_batch_task, results)
            step_results.append(result)
            if results is not None:
                results.append(result)

            # 如果步骤失败且设置了 stop_on_failure，则停止执行
            if not result.completed and step.get("stop_on_failure", False):
                break

        return TaskStepResult(
            step=f"sequence_{len(sequence_steps)}_steps",
            result=[r.dict() for r in step_results],
            completed=all(r.completed for r in step_results),
            message=f"Completed sequence execution of {len(step_results)} steps",
            status=TaskStatus.COMPLETED.value if all(r.status == TaskStatus.COMPLETED.value for r in step_results) else TaskStatus.FAILED.value
        )

    async def _handle_task_step(self, step: Dict, input_data: Dict, context: Dict,
                               execute_single_task: Callable, span=None) -> TaskStepResult:
        """处理单个任务执行"""
        task_name = step["task"]
        task_params = step.get("params", {})

        if span:
            span.set_tag("task_name", task_name)

        try:
            # 合并任务参数和输入数据
            merged_input = {**input_data, **task_params}
            result = await execute_single_task(task_name, merged_input, context)

            if isinstance(result, dict) and "step" in result:
                return TaskStepResult(**result)
            else:
                return TaskStepResult(
                    step=f"task_{task_name}",
                    result=result,
                    completed=True,
                    message=f"Completed task {task_name}",
                    status=TaskStatus.COMPLETED.value
                )
        except Exception as e:
            if span:
                span.set_tag("error", True)
                span.log_kv({"error_message": str(e)})
            return TaskStepResult(
                step=f"task_{task_name}",
                result=None,
                completed=False,
                message=f"Failed to execute task {task_name}",
                status=TaskStatus.FAILED.value,
                error_code=ErrorCode.EXECUTION_ERROR.value,
                error_message=str(e)
            )

    async def _handle_loop_step(self, step: Dict, intent_categories: List[str], input_data: Dict,
                               context: Dict, execute_single_task: Callable, execute_batch_task: Callable,
                               span=None, results: List[TaskStepResult] = None) -> TaskStepResult:
        """处理循环步骤"""
        loop_config = step["loop"]
        loop_steps = loop_config["steps"]
        condition = loop_config.get("while")
        max_iterations = loop_config.get("max_iterations", 10)

        if span:
            span.set_tag("loop_condition", condition)
            span.set_tag("max_iterations", max_iterations)

        iteration_results = []
        iteration = 0

        while iteration < max_iterations:
            # 检查循环条件
            if condition and not self.evaluate_condition(condition, intent_categories, context, input_data, results):
                break

            # 执行循环体
            iteration_step_results = []
            for sub_step in loop_steps:
                result = await self.execute_dsl_step(sub_step, intent_categories, input_data, context,
                                                   execute_single_task, execute_batch_task, results)
                iteration_step_results.append(result)
                if results is not None:
                    results.append(result)

            iteration_results.append(iteration_step_results)
            iteration += 1

            # 如果没有条件，只执行一次
            if not condition:
                break

        return TaskStepResult(
            step=f"loop_{iteration}_iterations",
            result=[{"iteration": i, "results": [r.dict() for r in iter_results]}
                   for i, iter_results in enumerate(iteration_results)],
            completed=True,
            message=f"Completed loop with {iteration} iterations",
            status=TaskStatus.COMPLETED.value
        )

    def validate_dsl_step(self, step: Dict) -> List[str]:
        """验证 DSL 步骤的格式"""
        errors = []

        if not isinstance(step, dict):
            errors.append("Step must be a dictionary")
            return errors

        step_types = ["if", "parallel", "sequence", "task", "loop"]
        found_types = [t for t in step_types if t in step]

        if len(found_types) == 0:
            errors.append(f"Step must contain one of: {step_types}")
        elif len(found_types) > 1:
            errors.append(f"Step can only contain one type, found: {found_types}")

        # 验证具体步骤类型
        if "if" in step:
            if "then" not in step:
                errors.append("'if' step must have 'then' clause")

        if "parallel" in step:
            if not isinstance(step["parallel"], list):
                errors.append("'parallel' must be a list of task names")

        if "sequence" in step:
            if not isinstance(step["sequence"], list):
                errors.append("'sequence' must be a list of steps")

        if "loop" in step:
            loop_config = step["loop"]
            if not isinstance(loop_config, dict):
                errors.append("'loop' must be a dictionary")
            elif "steps" not in loop_config:
                errors.append("'loop' must have 'steps' field")

        return errors

    def get_supported_features(self) -> Dict[str, Any]:
        """获取支持的 DSL 功能"""
        return {
            "step_types": ["if", "parallel", "sequence", "task", "loop"],
            "condition_types": [
                "intent.includes('category')",
                "context.field == value",
                "input.field == value",
                "result[index].field == value"
            ],
            "operators": ["==", "!=", ">", "<", ">=", "<="],
            "logical_operators": ["AND", "OR"],
            "supported_value_types": ["string", "number", "boolean", "null"],
            "condition_check_order": self.condition_check_order,
            "regex_matching": "fullmatch (exact matching)",
            "improvements": [
                "使用 re.fullmatch 替代 re.match 提供更严格的匹配",
                "优化条件检查顺序：AND -> OR -> intent.includes -> context -> input -> result",
                "增强值解析的健壮性，支持 null 值",
                "添加条件语法验证方法"
            ]
        }
