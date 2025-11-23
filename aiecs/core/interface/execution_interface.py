from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable
from aiecs.domain.execution.model import TaskStepResult


class IToolProvider(ABC):
    """Tool provider interface - Domain layer abstraction"""

    @abstractmethod
    def get_tool(self, tool_name: str) -> Any:
        """Get tool instance"""

    @abstractmethod
    def has_tool(self, tool_name: str) -> bool:
        """Check if tool exists"""


class IToolExecutor(ABC):
    """Tool executor interface - Domain layer abstraction"""

    @abstractmethod
    def execute(self, tool: Any, operation_name: str, **params) -> Any:
        """Execute tool operation synchronously"""

    @abstractmethod
    async def execute_async(self, tool: Any, operation_name: str, **params) -> Any:
        """Execute tool operation asynchronously"""


class ICacheProvider(ABC):
    """Cache provider interface - Domain layer abstraction"""

    @abstractmethod
    def generate_cache_key(
        self,
        operation_type: str,
        user_id: str,
        task_id: str,
        args: tuple,
        kwargs: Dict[str, Any],
    ) -> str:
        """Generate cache key"""

    @abstractmethod
    def get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Get data from cache"""

    @abstractmethod
    def add_to_cache(self, cache_key: str, value: Any) -> None:
        """Add data to cache"""


class IOperationExecutor(ABC):
    """Operation executor interface - Domain layer abstraction"""

    @abstractmethod
    async def execute_operation(self, operation_spec: str, params: Dict[str, Any]) -> Any:
        """Execute single operation"""

    @abstractmethod
    async def batch_execute_operations(self, operations: List[Dict[str, Any]]) -> List[Any]:
        """Batch execute operations"""

    @abstractmethod
    async def execute_operations_sequence(
        self,
        operations: List[Dict[str, Any]],
        user_id: str,
        task_id: str,
        stop_on_failure: bool = False,
        save_callback: Optional[Callable] = None,
    ) -> List[TaskStepResult]:
        """Execute operations sequence sequentially"""

    @abstractmethod
    async def execute_parallel_operations(self, operations: List[Dict[str, Any]]) -> List[TaskStepResult]:
        """Execute operations in parallel"""


class ExecutionInterface(ABC):
    """
    Unified execution interface that defines standard methods for service and tool execution.
    Supports plugin-based execution engines, allowing future introduction of new executors without modifying upper-level code.
    """

    @abstractmethod
    async def execute_operation(self, operation_spec: str, params: Dict[str, Any]) -> Any:
        """
        Execute a single operation (e.g., tool operation or service subtask).

        Args:
            operation_spec (str): Operation specification, format as 'tool_name.operation_name' or other identifier
            params (Dict[str, Any]): Operation parameters

        Returns:
            Any: Operation result
        """

    @abstractmethod
    async def execute_task(
        self,
        task_name: str,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        """
        Execute a single task (e.g., service task).

        Args:
            task_name (str): Task name
            input_data (Dict[str, Any]): Input data
            context (Dict[str, Any]): Context information

        Returns:
            Any: Task result
        """

    @abstractmethod
    async def batch_execute_operations(self, operations: List[Dict[str, Any]]) -> List[Any]:
        """
        Batch execute multiple operations.

        Args:
            operations (List[Dict[str, Any]]): List of operations, each containing 'operation' and 'params'

        Returns:
            List[Any]: List of operation results
        """

    @abstractmethod
    async def batch_execute_tasks(self, tasks: List[Dict[str, Any]]) -> List[Any]:
        """
        Batch execute multiple tasks.

        Args:
            tasks (List[Dict[str, Any]]): List of tasks, each containing 'task_name', 'input_data', 'context'

        Returns:
            List[Any]: List of task results
        """

    def register_executor(self, executor_type: str, executor_instance: Any) -> None:
        """
        Register new executor type, supporting plugin-based extension.

        Args:
            executor_type (str): Executor type identifier
            executor_instance (Any): Executor instance
        """
        raise NotImplementedError("Executor registration is not implemented in this interface")
