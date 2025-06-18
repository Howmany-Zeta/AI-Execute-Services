from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

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