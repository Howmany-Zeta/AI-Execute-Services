# multi-task/base.py

from abc import ABC, abstractmethod
from typing import Dict, List, Any, AsyncGenerator
from enum import Enum
import asyncio
import json
from datetime import datetime
from asyncio import TimeoutError as AsyncioTimeoutError

from app.services.base_service import BaseAIService
from app.domain.execution.model import TaskStatus, ErrorCode, TaskStepResult
from app.services.service_executor import UserConfirmation
import logging

# List of domains for dynamic specialization
DOMAINS = [
    "Artificial Intelligence",
    "Computer",
    "Data Science",
    "Blockchain Technology",
    "Supply Chain",
    "Biotechnology",
    "Medicine",
    "Psychology",
    "Economics",
    "Finance",
    "Accounting",
    "Marketing",
    "User Research",
    "Product Manager",
    "Management",
    "Human Resources Management",
    "Education",
    "Linguistics",
    "History",
    "Literature",
    "Philosophy",
    "Arts",
    "Physics",
    "Chemistry",
    "Biology",
    "Astronomy",
    "Earth Science",
    "Mathematics",
    "Statistics",
    "Agricultural Science",
    "Journalism and Communication",
    "Law",
    "Automobile",
    "Real Estate",
    "Manufacturing",
    "Service Industry"
]

class BaseTaskService(BaseAIService, ABC):
    """
    Base class for task services using the Template Method Pattern.
    Defines a skeleton for task execution workflows, with abstract methods
    for specific steps that subclasses must implement.
    """

    def __init__(self):
        super().__init__()
        # Business state
        self.task_id: str = None
        self.user_id: str = None
        self.task_history: List[Dict] = []
        self.current_step: int = 0
        self.task_sequence: List[Dict] = []
        self.user_input: Dict = {}
        self.results: List[TaskStepResult] = []
        self.failure_counts: Dict[str, int] = {}  # Track failures for quality control
        self._executor = None  # Will be set by subclasses

    async def initialize(self):
        """Initialize the service by setting up the database and WebSocket server."""
        await self._executor.initialize()

    async def execute_workflow(self, input_data: Dict, context: Dict) -> AsyncGenerator[Dict, None]:
        """
        Template method defining the workflow for task execution.
        Subclasses can override specific steps or hooks to customize behavior.
        """
        SESSION_TIMEOUT_SECONDS = 30 * 60  # 30 minutes

        try:
            async with asyncio.timeout(SESSION_TIMEOUT_SECONDS):
                # Initialize user ID and task ID
                self.user_id = input_data.get("user_id")
                if not self.user_id:
                    yield {
                        "status": TaskStatus.FAILED.value,
                        "message": "User ID is required.",
                        "error_code": ErrorCode.VALIDATION_ERROR.value,
                        "error_message": "Missing user_id in input data"
                    }
                    return

                self.task_id = input_data.get("task_id", self._generate_task_id())
                self.user_input = input_data

                # Restore task state
                await self._restore_task_state()

                # Check if task was cancelled
                status = await self._executor.check_task_status(self.user_id, self.task_id)
                if status == TaskStatus.CANCELLED:
                    yield {
                        "status": TaskStatus.CANCELLED.value,
                        "message": "Task was previously cancelled.",
                        "error_code": ErrorCode.CANCELLED_ERROR.value,
                        "error_message": "Task was cancelled by user"
                    }
                    return

                # Step 1: Parse intent
                if not any(result.step == "parse_intent" for result in self.results):
                    yield {"status": "info", "message": "Parsing user intent..."}
                    step_result = await self._parse_intent_with_retry(input_data)
                    self.results.append(step_result)
                    await self._executor.save_task_history(self.user_id, self.task_id, self.current_step, step_result)

                    user_confirmation = await self._notify_user(step_result)
                    if not user_confirmation.proceed:
                        yield self._cancel_task(user_confirmation)
                        return

                # Step 2: Break down sub-tasks
                self.current_step += 1
                if not any(result.step == "breakdown_subTask" for result in self.results):
                    yield {"status": "info", "message": "Breaking down sub-tasks..."}
                    categories = [self._category_enum(cat) for cat in self.results[0].result]
                    step_result = await self._breakdown_subtasks_with_retry(categories)
                    self.results.append(step_result)
                    await self._executor.save_task_history(self.user_id, self.task_id, self.current_step, step_result)

                    user_confirmation = await self._notify_user(step_result)
                    if not user_confirmation.proceed:
                        yield self._cancel_task(user_confirmation)
                        return

                # Step 3: Plan task sequence
                self.current_step += 1
                if not any(result.step == "plan_sequence" for result in self.results):
                    yield {"status": "info", "message": "Planning task sequence..."}
                    subtask_breakdown = next(result.result for result in self.results if result.step == "breakdown_subTask")
                    step_result = await self._plan_task_sequence_with_retry(subtask_breakdown)
                    self.results.append(step_result)
                    await self._executor.save_task_history(self.user_id, self.task_id, self.current_step, step_result)

                    user_confirmation = await self._notify_user(step_result)
                    if not user_confirmation.proceed:
                        yield self._cancel_task(user_confirmation)
                        return

                # Step 4: Execute task sequence with quality control
                intent_categories = self.results[0].result if self.results and self.results[0].result else []
                subtask_breakdown = next(result.result for result in self.results if result.step == "breakdown_subTask")
                async for result in self._execute_task_sequence(intent_categories, subtask_breakdown, input_data, context):
                    yield result

                # Final result
                final_result = {
                    "task_id": self.task_id,
                    "results": [result.dict() for result in self.results],
                    "completed": True
                }
                yield {
                    "status": TaskStatus.COMPLETED.value,
                    "message": "Task completed successfully.",
                    "result": final_result
                }
        except AsyncioTimeoutError:
            yield {
                "status": TaskStatus.TIMED_OUT.value,
                "message": "Session timed out due to inactivity (30 minutes).",
                "error_code": ErrorCode.TIMEOUT_ERROR.value,
                "error_message": "Session exceeded maximum duration of 30 minutes."
            }

    @abstractmethod
    async def _parse_intent(self, input_data: Dict) -> List[Any]:
        """
        Parse user input to identify intent categories for task processing.

        Args:
            input_data (Dict): The input data containing user query or instructions.

        Returns:
            List[Any]: A list of intent categories derived from the user input.
        """
        pass

    @abstractmethod
    async def _breakdown_subtasks(self, categories: List[Any]) -> Dict[str, List[str]]:
        """
        Break down identified intent categories into specific sub-tasks.

        Args:
            categories (List[Any]): The list of intent categories to break down.

        Returns:
            Dict[str, List[str]]: A mapping of category names to lists of sub-task identifiers.
        """
        pass

    @abstractmethod
    async def _examine_outcome(self, task_name: str, category: str, task_result: Dict) -> Dict:
        """
        Examine the outcome of 'collect' and 'process' category tasks for quality control.

        Args:
            task_name (str): The name of the task being examined.
            category (str): The category of the task (e.g., 'collect', 'process').
            task_result (Dict): The result of the task execution to evaluate.

        Returns:
            Dict: A dictionary indicating if the outcome passed examination with any feedback or issues.
        """
        pass

    @abstractmethod
    async def _accept_outcome(self, task_name: str, category: str, task_result: Dict) -> Dict:
        """
        Accept the outcome of 'analyze' and 'generate' category tasks for quality control.

        Args:
            task_name (str): The name of the task being accepted.
            category (str): The category of the task (e.g., 'analyze', 'generate').
            task_result (Dict): The result of the task execution to evaluate.

        Returns:
            Dict: A dictionary indicating if the outcome was accepted with any feedback or issues.
        """
        pass

    @abstractmethod
    async def _plan_task_sequence(self, subtask_breakdown: Dict[str, List[str]]) -> List[Dict]:
        """
        Plan a sequence of tasks based on the sub-task breakdown for execution.

        Args:
            subtask_breakdown (Dict[str, List[str]]): A mapping of categories to lists of sub-tasks.

        Returns:
            List[Dict]: A list of task definitions representing the execution sequence.
        """
        pass

    @abstractmethod
    async def _execute_dsl_step(self, step: Dict, intent_categories: List[str], input_data: Dict, context: Dict) -> TaskStepResult:
        """
        Execute a single step defined in a domain-specific language (DSL) format.

        Args:
            step (Dict): The DSL step definition to execute.
            intent_categories (List[str]): The list of intent categories for context.
            input_data (Dict): The input data for the step execution.
            context (Dict): Additional context for the step execution.

        Returns:
            TaskStepResult: The result of the step execution, including status and output.
        """
        pass

    @abstractmethod
    def _category_enum(self, category: str) -> Any:
        """
        Convert a category string to its corresponding enumeration or typed value.

        Args:
            category (str): The category string to convert.

        Returns:
            Any: The converted category value, typically an enum.
        """
        pass

    async def _execute_with_retry_metrics_tracing(self, func, metric_name: str, tracing_name: str, *args, step_name: str, success_message: str, **kwargs) -> TaskStepResult:
        """Helper to execute a function with retry, metrics, and tracing, returning a TaskStepResult."""
        wrapped_func = self._executor.with_tracing(tracing_name)(
            self._executor.with_metrics(metric_name)(
                self._executor.execute_with_retry(func, metric_name)
            )
        )
        try:
            result = await wrapped_func(*args, **kwargs)
            if step_name == "plan_sequence":
                self.task_sequence = result
            return TaskStepResult(
                step=step_name,
                result=result if step_name != "parse_intent" else [cat.value for cat in result],
                completed=True,
                message=success_message,
                status=TaskStatus.COMPLETED.value
            )
        except AsyncioTimeoutError as e:
            return TaskStepResult(
                step=step_name,
                result=None,
                completed=False,
                message=f"{step_name.replace('_', ' ').title()} timed out.",
                status=TaskStatus.TIMED_OUT.value,
                error_code=ErrorCode.TIMEOUT_ERROR.value,
                error_message=str(e)
            )
        except Exception as e:
            return TaskStepResult(
                step=step_name,
                result=None,
                completed=False,
                message=f"Failed to {step_name.replace('_', ' ').lower()}.",
                status=TaskStatus.FAILED.value,
                error_code=ErrorCode.EXECUTION_ERROR.value,
                error_message=str(e)
            )

    async def _parse_intent_with_retry(self, input_data: Dict) -> TaskStepResult:
        """Execute intent parsing with retry, metrics, and tracing."""
        return await self._execute_with_retry_metrics_tracing(
            self._parse_intent, "intent", "parse_intent", input_data,
            step_name="parse_intent", success_message="User intent parsed successfully."
        )

    async def _breakdown_subtasks_with_retry(self, categories: List[Any]) -> TaskStepResult:
        """Execute sub-task breakdown with retry, metrics, and tracing."""
        return await self._execute_with_retry_metrics_tracing(
            self._breakdown_subtasks, "breakdown", "breakdown_subTask", categories,
            step_name="breakdown_subTask", success_message="Sub-tasks broken down successfully."
        )

    async def _examine_outcome_with_retry(self, task_name: str, category: str, task_result: Dict) -> Dict:
        """Execute outcome examination with retry, metrics, and tracing."""
        wrapped_func = self._executor.with_tracing("examine_outcome")(
            self._executor.with_metrics("examine")(
                self._executor.execute_with_retry(self._examine_outcome, "examine")
            )
        )
        return await wrapped_func(task_name, category, task_result)

    async def _accept_outcome_with_retry(self, task_name: str, category: str, task_result: Dict) -> Dict:
        """Execute outcome acceptance with retry, metrics, and tracing."""
        wrapped_func = self._executor.with_tracing("accept_outcome")(
            self._executor.with_metrics("accept")(
                self._executor.execute_with_retry(self._accept_outcome, "accept")
            )
        )
        return await wrapped_func(task_name, category, task_result)

    async def _plan_task_sequence_with_retry(self, subtask_breakdown: Dict[str, List[str]]) -> TaskStepResult:
        """Execute task sequence planning with retry, metrics, and tracing."""
        return await self._execute_with_retry_metrics_tracing(
            self._plan_task_sequence, "plan", "plan_task_sequence", subtask_breakdown,
            step_name="plan_sequence", success_message="Task sequence planned successfully."
        )

    async def _notify_user(self, step_result: TaskStepResult) -> UserConfirmation:
        """Notify the user of a step result and get confirmation."""
        return await self._executor.notify_user(
            step_result,
            self.user_id,
            self.task_id,
            self.current_step
        )

    async def _cancel_task(self, user_confirmation: UserConfirmation) -> Dict:
        """Cancel the task with the given user confirmation."""
        return {
            "status": TaskStatus.CANCELLED.value,
            "message": "Task cancelled by user.",
            "feedback": user_confirmation.feedback,
            "error_code": ErrorCode.CANCELLED_ERROR.value,
            "error_message": "User declined to proceed"
        }

    def _generate_task_id(self) -> str:
        """Generate a unique task ID."""
        return str(int(datetime.now().timestamp() * 1000))

    async def _restore_task_state(self):
        """Restore task state from the database."""
        try:
            if self.user_id and self.task_id:
                self.task_history = await self._executor.load_task_history(self.user_id, self.task_id)
                if self.task_history:
                    self.current_step = max(entry['step'] for entry in self.task_history)
                    self.results = [TaskStepResult(**entry['result']) for entry in self.task_history]
                    for result in self.results:
                        if result.step == "plan_sequence":
                            self.task_sequence = result.result
                            break
        except Exception as e:
            raise Exception(f"Failed to restore task state: {e}")

    async def _pre_execution_hook(self, step: Dict, intent_categories: List[str], input_data: Dict, context: Dict):
        """
        Hook for custom actions before executing a task step. Subclasses can override for specific pre-execution logic.

        Args:
            step (Dict): The task step to be executed.
            intent_categories (List[str]): The list of intent categories for context.
            input_data (Dict): The input data for the step.
            context (Dict): Additional context for the step.
        """
        pass

    async def _post_execution_hook(self, step: Dict, step_result: TaskStepResult, intent_categories: List[str], input_data: Dict, context: Dict):
        """
        Hook for custom actions after executing a task step. Subclasses can override for specific post-execution logic.

        Args:
            step (Dict): The task step that was executed.
            step_result (TaskStepResult): The result of the step execution.
            intent_categories (List[str]): The list of intent categories for context.
            input_data (Dict): The input data for the step.
            context (Dict): Additional context for the step.
        """
        pass

    async def _execute_task_sequence(self, intent_categories: List[str], subtask_breakdown: Dict[str, List[str]], input_data: Dict, context: Dict) -> AsyncGenerator[Dict, None]:
        """
        Execute the planned task sequence with quality control checks and user feedback.

        Args:
            intent_categories (List[str]): The list of intent categories derived from user input.
            subtask_breakdown (Dict[str, List[str]]): The breakdown of sub-tasks by category.
            input_data (Dict): The original user input data.
            context (Dict): Additional context for task execution.

        Yields:
            Dict: Status updates, step results, or error messages during task sequence execution.
        """
        for step_idx, step in enumerate(self.task_sequence):
            self.current_step += 1

            status = await self._executor.check_task_status(self.user_id, self.task_id)
            if status == TaskStatus.CANCELLED:
                yield self._cancel_task(UserConfirmation(proceed=False, feedback="User cancelled"))
                return

            step_key = step.get("step", json.dumps(step))
            if any(result.step == step_key for result in self.results):
                continue

            yield {"status": "info", "message": f"Executing step {step_idx + 1}..."}
            await self._pre_execution_hook(step, intent_categories, input_data, context)

            step_input_data = {**input_data, 'current_step': step}
            step_result = await self._execute_dsl_step(step, intent_categories, step_input_data, context)

            # Quality control with examination and acceptance
            task_name = step.get('task', step_key)
            category = next((cat for cat in intent_categories if task_name in subtask_breakdown.get(cat, [])), None)

            if category in ['collect', 'process']:
                examination_result = await self._examine_outcome_with_retry(task_name, category, step_result)
                if not examination_result.get('passed', False):
                    self.failure_counts[task_name] = self.failure_counts.get(task_name, 0) + 1
                    if self.failure_counts[task_name] >= 2:
                        yield {
                            "status": TaskStatus.FAILED.value,
                            "message": f"Task {task_name} failed examination twice. Current conditions cannot support the task.",
                            "error_code": ErrorCode.QUALITY_CONTROL_ERROR.value,
                            "error_message": "Returning to user to re-clarify intent and breakdown sub-tasks."
                        }
                        self.results = []
                        self.current_step = 0
                        self.task_sequence = []
                        self.failure_counts = {}
                        continue
                    else:
                        self.failure_counts[task_name] = 0

            if category in ['analyze', 'generate']:
                acceptance_result = await self._accept_outcome_with_retry(task_name, category, step_result)
                if not acceptance_result.get('passed', False):
                    self.failure_counts[task_name] = self.failure_counts.get(task_name, 0) + 1
                    if self.failure_counts[task_name] >= 2:
                        yield {
                            "status": TaskStatus.FAILED.value,
                            "message": f"Task {task_name} failed acceptance twice. Current conditions cannot support the task.",
                            "error_code": ErrorCode.QUALITY_CONTROL_ERROR.value,
                            "error_message": "Returning to user to re-clarify intent and breakdown sub-tasks."
                        }
                        self.results = []
                        self.current_step = 0
                        self.task_sequence = []
                        self.failure_counts = {}
                        continue
                    else:
                        self.failure_counts[task_name] = 0

            self.results.append(step_result)
            await self._executor.save_task_history(self.user_id, self.task_id, self.current_step, step_result)

            user_confirmation = await self._notify_user(step_result)
            if not user_confirmation.proceed:
                yield self._cancel_task(user_confirmation)
                return

            await self._post_execution_hook(step, step_result, intent_categories, input_data, context)
            yield {"status": "step_completed", "result": step_result.dict()}

        # Final result
        final_result = {
            "task_id": self.task_id,
            "results": [result.dict() for result in self.results],
            "completed": True
        }
        yield {
            "status": TaskStatus.COMPLETED.value,
            "message": "Task completed successfully.",
            "result": final_result
        }
