"""
Workflow Interfaces

Core interfaces for workflow implementations in the multi-task service.
Extracted from workflow files for unified maintenance.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, AsyncGenerator, Callable

from ..models.execution_models import ExecutionContext
from ..models.task_models import TaskRequest, TaskResponse


class IWorkflow(ABC):
    """
    Abstract interface for workflow implementations.

    This interface defines the core contract for executing workflows
    in the multi-task system, following the Interface Segregation Principle.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the workflow."""
        pass

    @abstractmethod
    async def execute(
        self,
        request: TaskRequest,
        context: ExecutionContext
    ) -> AsyncGenerator[TaskResponse, None]:
        """Execute the workflow."""
        pass

    @abstractmethod
    async def validate_workflow(self, workflow_definition: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a workflow definition."""
        pass

    @abstractmethod
    async def pause(self, execution_id: str) -> bool:
        """Pause workflow execution."""
        pass

    @abstractmethod
    async def resume(self, execution_id: str) -> bool:
        """Resume workflow execution."""
        pass

    @abstractmethod
    async def cancel(self, execution_id: str, reason: Optional[str] = None) -> bool:
        """Cancel workflow execution."""
        pass

    @abstractmethod
    async def get_status(self, execution_id: str) -> str:
        """Get workflow execution status."""
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up workflow resources."""
        pass
