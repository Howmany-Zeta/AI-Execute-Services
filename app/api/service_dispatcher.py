from typing import Dict, Any
from app.domain.task.task_context import build_context
from app.config.registry import get_ai_service

class ServiceDispatcher:
    """
    中间层，负责服务实例化和上下文构建，作为API层和业务逻辑层之间的桥梁。
    """

    @staticmethod
    async def dispatch_service(mode: str, service: str, request_data: Dict[str, Any]):
        """
        构建上下文并获取服务实例，准备执行服务逻辑。

        Args:
            mode (str): 服务模式
            service (str): 服务名称
            request_data (Dict[str, Any]): 请求数据

        Returns:
            tuple: 包含服务实例和上下文的元组
        """
        context = build_context(request_data)
        service_cls = get_ai_service(mode, service)
        service_instance = service_cls()
        return service_instance, context
