"""
Task Service Interface

Defines the contract for task service implementations in the multi-task architecture.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, AsyncGenerator, Optional
from ..models.task_models import TaskRequest, TaskResponse, ExecutionContext


class ITaskService(ABC):
    """
    Abstract interface for task service implementations.

    This interface defines the core contract that all task services must implement,
    providing a standardized way to handle task execution workflows.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the task service.

        This method should set up any required resources, connections,
        or configurations needed for the service to operate.

        Raises:
            Exception: If initialization fails
        """
        pass

    @abstractmethod
    async def execute_workflow(
        self,
        request: TaskRequest,
        context: ExecutionContext
    ) -> AsyncGenerator[TaskResponse, None]:
        """
        Execute a complete task workflow.

        This is the main entry point for task execution, implementing the
        template method pattern to define the workflow skeleton.

        Args:
            request: The task request containing input data and configuration
            context: The execution context with additional metadata

        Yields:
            TaskResponse: Status updates and results during workflow execution

        Raises:
            TaskException: If workflow execution fails
        """
        pass

    @abstractmethod
    async def parse_intent(self, input_data: Dict[str, Any]) -> List[str]:
        """
        Parse user input to identify intent categories.

        Args:
            input_data: Raw input data from the user

        Returns:
            List of identified intent categories

        Raises:
            TaskValidationError: If input data is invalid
            TaskExecutionError: If intent parsing fails
        """
        pass

    @abstractmethod
    async def breakdown_subtasks(self, categories: List[str]) -> Dict[str, List[str]]:
        """
        Break down intent categories into executable sub-tasks.

        Args:
            categories: List of intent categories to decompose

        Returns:
            Mapping of categories to their corresponding sub-tasks

        Raises:
            TaskExecutionError: If subtask breakdown fails
        """
        pass

    @abstractmethod
    async def plan_task_sequence(self, subtask_breakdown: Dict[str, List[str]]) -> List[Dict[str, Any]]:
        """
        Plan the execution sequence for sub-tasks.

        Args:
            subtask_breakdown: Mapping of categories to sub-tasks

        Returns:
            Ordered list of task execution steps

        Raises:
            TaskExecutionError: If task planning fails
        """
        pass

    @abstractmethod
    async def execute_task_step(
        self,
        step: Dict[str, Any],
        context: ExecutionContext
    ) -> TaskResponse:
        """
        Execute a single task step.

        Args:
            step: The task step definition to execute
            context: Execution context with metadata and state

        Returns:
            Result of the task step execution

        Raises:
            TaskExecutionError: If step execution fails
        """
        pass

    @abstractmethod
    async def validate_task_result(
        self,
        task_name: str,
        category: str,
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate the result of a completed task.

        Args:
            task_name: Name of the executed task
            category: Category of the task (collect, process, analyze, generate)
            result: The task execution result to validate

        Returns:
            Validation result with pass/fail status and feedback

        Raises:
            TaskExecutionError: If validation process fails
        """
        pass

    @abstractmethod
    async def get_task_status(self, task_id: str) -> str:
        """
        Get the current status of a task.

        Args:
            task_id: Unique identifier of the task

        Returns:
            Current task status (pending, running, completed, failed, cancelled)

        Raises:
            TaskException: If task status cannot be retrieved
        """
        pass

    @abstractmethod
    async def cancel_task(self, task_id: str, reason: Optional[str] = None) -> bool:
        """
        Cancel a running task.

        Args:
            task_id: Unique identifier of the task to cancel
            reason: Optional reason for cancellation

        Returns:
            True if task was successfully cancelled, False otherwise

        Raises:
            TaskException: If task cancellation fails
        """
        pass

    @abstractmethod
    async def get_task_history(self, task_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve the execution history of a task.

        Args:
            task_id: Unique identifier of the task

        Returns:
            List of execution steps and their results

        Raises:
            TaskException: If history retrieval fails
        """
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """
        Clean up resources used by the task service.

        This method should be called when the service is being shut down
        to properly release any held resources.
        """
        pass
