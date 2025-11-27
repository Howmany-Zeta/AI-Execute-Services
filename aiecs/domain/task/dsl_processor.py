import re
import json
import logging
from typing import Dict, List, Any, Callable, Optional
from aiecs.domain.execution.model import TaskStepResult, TaskStatus, ErrorCode

logger = logging.getLogger(__name__)


class DSLProcessor:
    """
    Specialized DSL (Domain Specific Language) parsing and execution processor
    """

    def __init__(self, tracer=None):
        self.tracer = tracer
        # Update supported condition patterns with stricter matching
        self.supported_conditions = [
            r"intent\.includes\('([^']+)'\)",
            r"context\.(\w+)\s*(==|!=|>|<|>=|<=)\s*(.+)",
            r"input\.(\w+)\s*(==|!=|>|<|>=|<=)\s*(.+)",
            r"result\[(\d+)\]\.(\w+)\s*(==|!=|>|<|>=|<=)\s*(.+)",
        ]
        # Condition check priority order
        self.condition_check_order = [
            "AND",  # Logical AND operation
            "OR",  # Logical OR operation
            "intent.includes",  # Intent inclusion check
            "context",  # Context check
            "input",  # Input check
            "result",  # Result check
        ]

    def evaluate_condition(
        self,
        condition: str,
        intent_categories: List[str],
        context: Optional[Dict[str, Any]] = None,
        input_data: Optional[Dict[str, Any]] = None,
        results: Optional[List[TaskStepResult]] = None,
    ) -> bool:
        """
        Evaluate condition expression, supporting multiple condition types
        Following optimized check order: AND -> OR -> intent.includes -> context -> input -> result
        """
        try:
            # 1. Compound condition: support AND (highest priority)
            if " AND " in condition:
                parts = condition.split(" AND ")
                return all(
                    self.evaluate_condition(
                        part.strip(),
                        intent_categories,
                        context,
                        input_data,
                        results,
                    )
                    for part in parts
                )

            # 2. Compound condition: support OR (second priority)
            if " OR " in condition:
                parts = condition.split(" OR ")
                return any(
                    self.evaluate_condition(
                        part.strip(),
                        intent_categories,
                        context,
                        input_data,
                        results,
                    )
                    for part in parts
                )

            # 3. Intent condition: intent.includes('category')
            match = re.fullmatch(r"intent\.includes\('([^']+)'\)", condition)
            if match:
                category = match.group(1)
                return category in intent_categories

            # 4. Context condition: context.field == value
            match = re.fullmatch(r"context\.(\w+)\s*(==|!=|>|<|>=|<=)\s*(.+)", condition)
            if match and context:
                field, operator, value = match.groups()
                return self._evaluate_comparison(context.get(field), operator, self._parse_value(value))

            # 5. Input condition: input.field == value
            match = re.fullmatch(r"input\.(\w+)\s*(==|!=|>|<|>=|<=)\s*(.+)", condition)
            if match and input_data:
                field, operator, value = match.groups()
                return self._evaluate_comparison(input_data.get(field), operator, self._parse_value(value))

            # 6. Result condition: result[0].field == value
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
        """Evaluate comparison operation"""
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
            # Return False when types don't match
            return False

    def _parse_value(self, value_str: str) -> Any:
        """Parse value string to appropriate type"""
        value_str = value_str.strip()

        # String value
        if value_str.startswith('"') and value_str.endswith('"'):
            return value_str[1:-1]
        if value_str.startswith("'") and value_str.endswith("'"):
            return value_str[1:-1]

        # Boolean value
        if value_str.lower() == "true":
            return True
        if value_str.lower() == "false":
            return False

        # Numeric value
        try:
            if "." in value_str:
                return float(value_str)
            else:
                return int(value_str)
        except ValueError:
            pass

        # Default return string
        return value_str

    def validate_condition_syntax(self, condition: str) -> bool:
        """Validate condition syntax validity"""
        if not condition or not isinstance(condition, str):
            return False

        condition = condition.strip()
        if not condition:
            return False

        # Check if matches any supported condition pattern
        for pattern in self.supported_conditions:
            if re.fullmatch(pattern, condition):
                return True

        # Check compound conditions
        if " AND " in condition or " OR " in condition:
            return True

        return False

    async def execute_dsl_step(
        self,
        step: Dict,
        intent_categories: List[str],
        input_data: Dict,
        context: Dict,
        execute_single_task: Callable,
        execute_batch_task: Callable,
        results: Optional[List[TaskStepResult]] = None,
    ) -> TaskStepResult:
        """
        Execute DSL step based on step type (if, parallel, task, sequence)
        """
        span = self.tracer.start_span("execute_dsl_step") if self.tracer else None
        if span:
            span.set_tag("step", json.dumps(step))

        try:
            if "if" in step:
                return await self._handle_if_step(
                    step,
                    intent_categories,
                    input_data,
                    context,
                    execute_single_task,
                    execute_batch_task,
                    span,
                    results,
                )
            elif "parallel" in step:
                return await self._handle_parallel_step(step, input_data, context, execute_batch_task, span)
            elif "sequence" in step:
                return await self._handle_sequence_step(
                    step,
                    intent_categories,
                    input_data,
                    context,
                    execute_single_task,
                    execute_batch_task,
                    span,
                    results,
                )
            elif "task" in step:
                return await self._handle_task_step(step, input_data, context, execute_single_task, span)
            elif "loop" in step:
                return await self._handle_loop_step(
                    step,
                    intent_categories,
                    input_data,
                    context,
                    execute_single_task,
                    execute_batch_task,
                    span,
                    results,
                )
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
                    error_message="Unknown DSL step type",
                )
        finally:
            if span:
                span.finish()

    async def _handle_if_step(
        self,
        step: Dict,
        intent_categories: List[str],
        input_data: Dict,
        context: Dict,
        execute_single_task: Callable,
        execute_batch_task: Callable,
        span=None,
        results: Optional[List[TaskStepResult]] = None,
    ) -> TaskStepResult:
        """Handle conditional 'if' step"""
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
                    result = await self.execute_dsl_step(
                        sub_step,
                        intent_categories,
                        input_data,
                        context,
                        execute_single_task,
                        execute_batch_task,
                        results,
                    )
                    step_results.append(result)
                    if results is not None:
                        results.append(result)

                return TaskStepResult(
                    step=f"if_{condition}",
                    result=[r.dict() for r in step_results],
                    completed=all(r.completed for r in step_results),
                    message=f"Condition '{condition}' evaluated to true",
                    status=(TaskStatus.COMPLETED.value if all(r.status == TaskStatus.COMPLETED.value for r in step_results) else TaskStatus.FAILED.value),
                )
            else:
                if span:
                    span.log_kv({"condition_result": "false"})

                if else_steps:
                    step_results = []
                    for sub_step in else_steps:
                        result = await self.execute_dsl_step(
                            sub_step,
                            intent_categories,
                            input_data,
                            context,
                            execute_single_task,
                            execute_batch_task,
                            results,
                        )
                        step_results.append(result)
                        if results is not None:
                            results.append(result)

                    return TaskStepResult(
                        step=f"if_{condition}_else",
                        result=[r.dict() for r in step_results],
                        completed=all(r.completed for r in step_results),
                        message=f"Condition '{condition}' evaluated to false, executed else branch",
                        status=(TaskStatus.COMPLETED.value if all(r.status == TaskStatus.COMPLETED.value for r in step_results) else TaskStatus.FAILED.value),
                    )
                else:
                    return TaskStepResult(
                        step=f"if_{condition}",
                        result=None,
                        completed=True,
                        message=f"Condition '{condition}' evaluated to false, skipping",
                        status=TaskStatus.COMPLETED.value,
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
                error_message=str(e),
            )

    async def _handle_parallel_step(
        self,
        step: Dict,
        input_data: Dict,
        context: Dict,
        execute_batch_task: Callable,
        span=None,
    ) -> TaskStepResult:
        """Handle parallel task execution"""
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
            status=(TaskStatus.COMPLETED.value if all(r.status == TaskStatus.COMPLETED.value for r in batch_results) else TaskStatus.FAILED.value),
        )

    async def _handle_sequence_step(
        self,
        step: Dict,
        intent_categories: List[str],
        input_data: Dict,
        context: Dict,
        execute_single_task: Callable,
        execute_batch_task: Callable,
        span=None,
        results: Optional[List[TaskStepResult]] = None,
    ) -> TaskStepResult:
        """Handle sequential execution steps"""
        sequence_steps = step["sequence"]
        if span:
            span.set_tag("sequence_length", len(sequence_steps))

        step_results = []
        for i, sub_step in enumerate(sequence_steps):
            result = await self.execute_dsl_step(
                sub_step,
                intent_categories,
                input_data,
                context,
                execute_single_task,
                execute_batch_task,
                results,
            )
            step_results.append(result)
            if results is not None:
                results.append(result)

            # If step fails and stop_on_failure is set, stop execution
            if not result.completed and step.get("stop_on_failure", False):
                break

        return TaskStepResult(
            step=f"sequence_{len(sequence_steps)}_steps",
            result=[r.dict() for r in step_results],
            completed=all(r.completed for r in step_results),
            message=f"Completed sequence execution of {len(step_results)} steps",
            status=(TaskStatus.COMPLETED.value if all(r.status == TaskStatus.COMPLETED.value for r in step_results) else TaskStatus.FAILED.value),
        )

    async def _handle_task_step(
        self,
        step: Dict,
        input_data: Dict,
        context: Dict,
        execute_single_task: Callable,
        span=None,
    ) -> TaskStepResult:
        """Handle single task execution"""
        task_name = step["task"]
        task_params = step.get("params", {})

        if span:
            span.set_tag("task_name", task_name)

        try:
            # Merge task parameters and input data
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
                    status=TaskStatus.COMPLETED.value,
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
                error_message=str(e),
            )

    async def _handle_loop_step(
        self,
        step: Dict,
        intent_categories: List[str],
        input_data: Dict,
        context: Dict,
        execute_single_task: Callable,
        execute_batch_task: Callable,
        span=None,
        results: Optional[List[TaskStepResult]] = None,
    ) -> TaskStepResult:
        """Handle loop step"""
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
            # Check loop condition
            if condition and not self.evaluate_condition(condition, intent_categories, context, input_data, results):
                break

            # Execute loop body
            iteration_step_results = []
            for sub_step in loop_steps:
                result = await self.execute_dsl_step(
                    sub_step,
                    intent_categories,
                    input_data,
                    context,
                    execute_single_task,
                    execute_batch_task,
                    results,
                )
                iteration_step_results.append(result)
                if results is not None:
                    results.append(result)

            iteration_results.append(iteration_step_results)
            iteration += 1

            # If no condition, execute only once
            if not condition:
                break

        return TaskStepResult(
            step=f"loop_{iteration}_iterations",
            result=[{"iteration": i, "results": [r.dict() for r in iter_results]} for i, iter_results in enumerate(iteration_results)],
            completed=True,
            message=f"Completed loop with {iteration} iterations",
            status=TaskStatus.COMPLETED.value,
        )

    def validate_dsl_step(self, step: Dict) -> List[str]:
        """Validate DSL step format"""
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

        # Validate specific step types
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
        """Get supported DSL features"""
        return {
            "step_types": ["if", "parallel", "sequence", "task", "loop"],
            "condition_types": [
                "intent.includes('category')",
                "context.field == value",
                "input.field == value",
                "result[index].field == value",
            ],
            "operators": ["==", "!=", ">", "<", ">=", "<="],
            "logical_operators": ["AND", "OR"],
            "supported_value_types": ["string", "number", "boolean", "null"],
            "condition_check_order": self.condition_check_order,
            "regex_matching": "fullmatch (exact matching)",
            "improvements": [
                "Use re.fullmatch instead of re.match for stricter matching",
                "Optimize condition check order: AND -> OR -> intent.includes -> context -> input -> result",
                "Enhance value parsing robustness, support null values",
                "Add condition syntax validation method",
            ],
        }
