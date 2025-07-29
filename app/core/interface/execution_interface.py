from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable
from app.domain.execution.model import TaskStepResult


class IToolProvider(ABC):
    """工具提供者接口 - Domain层抽象"""

    @abstractmethod
    def get_tool(self, tool_name: str) -> Any:
        """获取工具实例"""
        pass

    @abstractmethod
    def has_tool(self, tool_name: str) -> bool:
        """检查工具是否存在"""
        pass


class IToolExecutor(ABC):
    """工具执行器接口 - Domain层抽象"""

    @abstractmethod
    def execute(self, tool: Any, operation_name: str, **params) -> Any:
        """同步执行工具操作"""
        pass

    @abstractmethod
    async def execute_async(self, tool: Any, operation_name: str, **params) -> Any:
        """异步执行工具操作"""
        pass


class ICacheProvider(ABC):
    """缓存提供者接口 - Domain层抽象"""

    @abstractmethod
    def generate_cache_key(self, operation_type: str, user_id: str, task_id: str,
                          args: tuple, kwargs: Dict[str, Any]) -> str:
        """生成缓存键"""
        pass

    @abstractmethod
    def get_from_cache(self, cache_key: str) -> Optional[Any]:
        """从缓存获取数据"""
        pass

    @abstractmethod
    def add_to_cache(self, cache_key: str, value: Any) -> None:
        """添加数据到缓存"""
        pass


class IOperationExecutor(ABC):
    """操作执行器接口 - Domain层抽象"""

    @abstractmethod
    async def execute_operation(self, operation_spec: str, params: Dict[str, Any]) -> Any:
        """执行单个操作"""
        pass

    @abstractmethod
    async def batch_execute_operations(self, operations: List[Dict[str, Any]]) -> List[Any]:
        """批量执行操作"""
        pass

    @abstractmethod
    async def execute_operations_sequence(self, operations: List[Dict[str, Any]],
                                        user_id: str, task_id: str,
                                        stop_on_failure: bool = False,
                                        save_callback: Optional[Callable] = None) -> List[TaskStepResult]:
        """顺序执行操作序列"""
        pass

    @abstractmethod
    async def execute_parallel_operations(self, operations: List[Dict[str, Any]]) -> List[TaskStepResult]:
        """并行执行操作"""
        pass


class ExecutionInterface(ABC):
    """
    统一的执行接口，定义了服务和工具执行的标准方法。
    支持插件式执行引擎，允许未来引入新的执行器而无需修改上层代码。
    """

    @abstractmethod
    async def execute_operation(self, operation_spec: str, params: Dict[str, Any]) -> Any:
        """
        执行单个操作（例如工具操作或服务子任务）。

        Args:
            operation_spec (str): 操作规格，格式为 'tool_name.operation_name' 或其他标识符
            params (Dict[str, Any]): 操作参数

        Returns:
            Any: 操作结果
        """
        pass

    @abstractmethod
    async def execute_task(self, task_name: str, input_data: Dict[str, Any], context: Dict[str, Any]) -> Any:
        """
        执行单个任务（例如服务任务）。

        Args:
            task_name (str): 任务名称
            input_data (Dict[str, Any]): 输入数据
            context (Dict[str, Any]): 上下文信息

        Returns:
            Any: 任务结果
        """
        pass

    @abstractmethod
    async def batch_execute_operations(self, operations: List[Dict[str, Any]]) -> List[Any]:
        """
        批量执行多个操作。

        Args:
            operations (List[Dict[str, Any]]): 操作列表，每个操作包含 'operation' 和 'params'

        Returns:
            List[Any]: 操作结果列表
        """
        pass

    @abstractmethod
    async def batch_execute_tasks(self, tasks: List[Dict[str, Any]]) -> List[Any]:
        """
        批量执行多个任务。

        Args:
            tasks (List[Dict[str, Any]]): 任务列表，每个任务包含 'task_name', 'input_data', 'context'

        Returns:
            List[Any]: 任务结果列表
        """
        pass

    def register_executor(self, executor_type: str, executor_instance: Any) -> None:
        """
        注册新的执行器类型，支持插件式扩展。

        Args:
            executor_type (str): 执行器类型标识符
            executor_instance (Any): 执行器实例
        """
        raise NotImplementedError("Executor registration is not implemented in this interface")
