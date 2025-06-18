import asyncio
import functools
import json
import logging
import uuid
import re
import time
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, Union, AsyncGenerator, Set

import tenacity
from celery import Celery
from celery.exceptions import TimeoutError as CeleryTimeoutError
from asyncio import TimeoutError as AsyncioTimeoutError
from pydantic import BaseModel, ValidationError

from app.tools import get_tool
from app.core.tool_executor import ToolExecutor
from app.core.execution_utils import ExecutionUtils
from app.core.execution_interface import ExecutionInterface

# 导入新的专门管理器
from app.core.executor_metrics import ExecutorMetrics
from app.core.database_manager import DatabaseManager, TaskStepResult, TaskStatus
from app.core.websocket_manager import WebSocketManager, UserConfirmation
from app.core.celery_task_manager import CeleryTaskManager
from app.core.operation_executor import OperationExecutor
from app.core.dsl_processor import DSLProcessor
from app.core.tracing_manager import TracingManager

logger = logging.getLogger(__name__)

# Error Code Enum
class ErrorCode(Enum):
    VALIDATION_ERROR = "E001"
    TIMEOUT_ERROR = "E002"
    EXECUTION_ERROR = "E003"
    CANCELLED_ERROR = "E004"
    RETRY_EXHAUSTED = "E005"
    DATABASE_ERROR = "E006"
    DSL_EVALUATION_ERROR = "E007"

# Configuration for the executor
class ExecutorConfig(BaseModel):
    """Configuration for the service executor"""
    broker_url: str = "redis://redis:6379/0"
    backend_url: str = "redis://redis:6379/0"
    task_serializer: str = "json"
    accept_content: List[str] = ["json"]
    result_serializer: str = "json"
    timezone: str = "UTC"
    enable_utc: bool = True
    task_queues: Dict[str, Dict[str, str]] = {
        'fast_tasks': {'exchange': 'fast_tasks', 'routing_key': 'fast_tasks'},
        'heavy_tasks': {'exchange': 'heavy_tasks', 'routing_key': 'heavy_tasks'}
    }
    worker_concurrency: Dict[str, int] = {
        'fast_worker': 10,
        'heavy_worker': 2
    }
    task_timeout_seconds: int = 300
    call_timeout_seconds: int = 600
    rate_limit_requests_per_second: int = 5
    batch_size: int = 10
    websocket_host: str = "python-middleware-api"
    websocket_port: int = 8765
    db_config: Dict[str, Any] = {
        "user": "your_postgres_user",
        "password": "your_postgres_password",
        "database": "your_database_name",
        "host": "your_gcp_host",
        "port": 5432
    }
    retry_max_attempts: int = 3
    retry_min_wait: int = 4
    retry_max_wait: int = 60
    metrics_port: int = 8001
    enable_metrics: bool = True
    tracing_service_name: str = "service_executor"
    tracing_host: str = "jaeger"
    tracing_port: int = 6831
    enable_tracing: bool = True
    enable_cache: bool = True
    cache_ttl: int = 3600


class ServiceExecutor(ExecutionInterface):
    """
    服务执行器主协调器 - 组合各个专门的管理器
    负责协调各个组件，不直接处理具体业务逻辑

    重构后的架构：
    - ExecutorMetrics: 监控指标管理
    - DatabaseManager: 数据库操作管理
    - WebSocketManager: WebSocket 通信管理
    - CeleryTaskManager: Celery 任务管理
    - OperationExecutor: 操作执行核心
    - DSLProcessor: DSL 处理器
    - TracingManager: 分布式追踪管理
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = ExecutorConfig(**(config or {}))

        # 初始化各个专门的管理器
        self._init_managers()

        # 基础组件
        self.semaphore = asyncio.Semaphore(self.config.rate_limit_requests_per_second)
        self.thread_pool = ThreadPoolExecutor(max_workers=self.config.worker_concurrency.get('fast_worker', 10))
        self._tool_instances = {}  # Cache for tool instances

        logger.info("ServiceExecutor initialized with modular architecture")

    def _init_managers(self):
        """初始化各个管理器"""
        # 监控指标管理器
        self.metrics_manager = ExecutorMetrics(
            enable_metrics=self.config.enable_metrics,
            metrics_port=self.config.metrics_port
        )

        # 数据库管理器
        self.database_manager = DatabaseManager(self.config.db_config)

        # WebSocket 管理器
        self.websocket_manager = WebSocketManager(
            host=self.config.websocket_host,
            port=self.config.websocket_port
        )

        # Celery 任务管理器
        celery_config = {
            'broker_url': self.config.broker_url,
            'backend_url': self.config.backend_url,
            'task_serializer': self.config.task_serializer,
            'accept_content': self.config.accept_content,
            'result_serializer': self.config.result_serializer,
            'timezone': self.config.timezone,
            'enable_utc': self.config.enable_utc,
            'task_queues': self.config.task_queues,
            'worker_concurrency': self.config.worker_concurrency,
            'task_timeout_seconds': self.config.task_timeout_seconds,
            'batch_size': self.config.batch_size,
            'rate_limit_requests_per_second': self.config.rate_limit_requests_per_second
        }
        self.celery_manager = CeleryTaskManager(celery_config)

        # 分布式追踪管理器
        self.tracing_manager = TracingManager(
            service_name=self.config.tracing_service_name,
            jaeger_host=self.config.tracing_host,
            jaeger_port=self.config.tracing_port,
            enable_tracing=self.config.enable_tracing
        )

        # 执行工具
        self.execution_utils = ExecutionUtils(
            cache_size=100,
            cache_ttl=self.config.cache_ttl,
            retry_attempts=self.config.retry_max_attempts,
            retry_backoff=1.0
        )

        # 工具执行器
        tool_executor_config = {
            "enable_cache": self.config.enable_cache,
            "cache_ttl": self.config.cache_ttl,
            "max_workers": self.config.worker_concurrency.get('fast_worker', 10),
            "log_level": "INFO",
            "log_execution_time": True,
            "enable_security_checks": True,
            "retry_attempts": self.config.retry_max_attempts,
            "retry_backoff": 1.0,
            "timeout": self.config.task_timeout_seconds
        }
        self.tool_executor = ToolExecutor(tool_executor_config)

        # 操作执行器
        operation_config = {
            'batch_size': self.config.batch_size,
            'rate_limit_requests_per_second': self.config.rate_limit_requests_per_second,
            'enable_cache': self.config.enable_cache
        }
        self.operation_executor = OperationExecutor(
            tool_executor=self.tool_executor,
            execution_utils=self.execution_utils,
            config=operation_config
        )

        # DSL 处理器
        self.dsl_processor = DSLProcessor(tracer=self.tracing_manager.tracer)

    async def initialize(self):
        """初始化所有组件"""
        try:
            # 初始化数据库
            await self.database_manager.init_connection_pool()
            await self.database_manager.init_database_schema()

            # 启动 WebSocket 服务器
            await self.websocket_manager.start_server()

            logger.info("ServiceExecutor initialization completed successfully")
            return True
        except Exception as e:
            logger.error(f"ServiceExecutor initialization failed: {e}")
            return False

    async def shutdown(self):
        """优雅关闭所有组件"""
        try:
            # 停止 WebSocket 服务器
            await self.websocket_manager.stop_server()

            # 关闭数据库连接
            await self.database_manager.close()

            # 关闭追踪器
            self.tracing_manager.close_tracer()

            # 关闭线程池
            self.thread_pool.shutdown(wait=True)

            logger.info("ServiceExecutor shutdown completed")
        except Exception as e:
            logger.error(f"Error during ServiceExecutor shutdown: {e}")

    # 实现 ExecutionInterface 的方法
    async def execute_operation(self, operation_spec: str, params: Dict[str, Any]) -> Any:
        """委托给操作执行器"""
        return await self.operation_executor.execute_operation(operation_spec, params)

    async def execute_task(self, task_name: str, input_data: Dict[str, Any], context: Dict[str, Any]) -> Any:
        """委托给 Celery 任务管理器"""
        return await self.celery_manager.execute_task(task_name, input_data, context)

    async def batch_execute_operations(self, operations: List[Dict[str, Any]]) -> List[Any]:
        """委托给操作执行器"""
        return await self.operation_executor.batch_execute_operations(operations)

    async def batch_execute_tasks(self, tasks: List[Dict[str, Any]]) -> List[Any]:
        """委托给 Celery 任务管理器"""
        return await self.celery_manager.batch_execute_tasks(tasks)

    # 数据库操作方法
    async def save_task_history(self, user_id: str, task_id: str, step: int, step_result: TaskStepResult):
        """保存任务历史"""
        return await self.database_manager.save_task_history(user_id, task_id, step, step_result)

    async def load_task_history(self, user_id: str, task_id: str) -> List[Dict]:
        """加载任务历史"""
        return await self.database_manager.load_task_history(user_id, task_id)

    async def check_task_status(self, user_id: str, task_id: str) -> TaskStatus:
        """检查任务状态"""
        return await self.database_manager.check_task_status(user_id, task_id)

    # WebSocket 通信方法
    async def notify_user(self, step_result: TaskStepResult, user_id: str, task_id: str, step: int) -> UserConfirmation:
        """通知用户"""
        return await self.websocket_manager.notify_user(step_result, user_id, task_id, step)

    async def send_heartbeat(self, user_id: str, task_id: str, interval: int = 30):
        """发送心跳"""
        return await self.websocket_manager.send_heartbeat(user_id, task_id, interval)

    # DSL 处理方法
    async def execute_dsl_step(self, step: Dict, intent_categories: List[str], input_data: Dict,
                              context: Dict, execute_single_task: Callable, execute_batch_task: Callable) -> TaskStepResult:
        """执行 DSL 步骤"""
        return await self.dsl_processor.execute_dsl_step(
            step, intent_categories, input_data, context, execute_single_task, execute_batch_task
        )

    def evaluate_condition(self, condition: str, intent_categories: List[str]) -> bool:
        """评估条件"""
        return self.dsl_processor.evaluate_condition(condition, intent_categories)

    # 高级执行方法
    async def execute_operations_sequence(self, operations: List[Dict[str, Any]], user_id: str, task_id: str,
                                        stop_on_failure: bool = False) -> List[TaskStepResult]:
        """执行操作序列"""
        return await self.operation_executor.execute_operations_sequence(
            operations, user_id, task_id, stop_on_failure,
            save_callback=self.save_task_history
        )

    async def execute_parallel_operations(self, operations: List[Dict[str, Any]]) -> List[TaskStepResult]:
        """并行执行操作"""
        return await self.operation_executor.execute_parallel_operations(operations)

    # 工具调用方法
    async def batch_tool_calls(self, tool_calls: List[Dict], tool_executor=None) -> List[Any]:
        """批量工具调用"""
        return await self.operation_executor.batch_tool_calls(tool_calls, tool_executor)

    def extract_tool_calls(self, description: str, input_data: Dict, context: Dict) -> List[Dict]:
        """提取工具调用"""
        return self.operation_executor.extract_tool_calls(description, input_data, context)

    # 重试和超时方法
    def create_retry_strategy(self, metric_name: Optional[str] = None):
        """创建重试策略"""
        def after_retry(retry_state):
            if metric_name and retry_state.attempt_number > 1:
                self.metrics_manager.record_retry(metric_name, retry_state.attempt_number)

        return tenacity.retry(
            retry=tenacity.retry_if_exception_type(Exception),
            wait=tenacity.wait_exponential(
                multiplier=1,
                min=self.config.retry_min_wait,
                max=self.config.retry_max_wait
            ),
            stop=tenacity.stop_after_attempt(self.config.retry_max_attempts),
            after=after_retry,
            reraise=True
        )

    async def execute_with_timeout(self, func, *args, timeout=None, **kwargs):
        """带超时的执行"""
        timeout = timeout or self.config.task_timeout_seconds
        try:
            return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
        except AsyncioTimeoutError as e:
            logger.error(f"Timeout executing {func.__name__}: {e}")
            return {
                "step": func.__name__,
                "result": None,
                "completed": False,
                "message": f"Timed out executing {func.__name__}",
                "status": TaskStatus.TIMED_OUT.value,
                "error_code": ErrorCode.TIMEOUT_ERROR.value,
                "error_message": "Execution timed out"
            }

    # 装饰器方法
    def with_metrics(self, metric_name: str, labels: Optional[Dict[str, str]] = None):
        """监控装饰器"""
        return self.metrics_manager.with_metrics(metric_name, labels)

    def with_tracing(self, operation_name: str):
        """追踪装饰器"""
        return self.tracing_manager.with_tracing(operation_name)

    # 状态和信息方法
    def get_status(self) -> Dict[str, Any]:
        """获取执行器状态"""
        return {
            "service_executor": {
                "initialized": True,
                "config": {
                    "enable_metrics": self.config.enable_metrics,
                    "enable_tracing": self.config.enable_tracing,
                    "enable_cache": self.config.enable_cache
                }
            },
            "metrics": self.metrics_manager.get_metrics_summary(),
            "websocket": self.websocket_manager.get_status(),
            "tracing": self.tracing_manager.get_tracer_info(),
            "operation_executor": self.operation_executor.get_stats(),
            "celery": self.celery_manager.get_queue_info()
        }

    def get_health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "components": {
                    "database": "healthy",  # 可以添加实际的数据库健康检查
                    "websocket": "healthy" if self.websocket_manager.get_connection_count() >= 0 else "unhealthy",
                    "metrics": "healthy" if self.config.enable_metrics else "disabled",
                    "tracing": "healthy" if self.config.enable_tracing else "disabled"
                }
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }


# Singleton executor instance
_default_executor = None

def get_executor(config: Optional[Dict[str, Any]] = None) -> ServiceExecutor:
    """
    Get a singleton instance of the ServiceExecutor.
    """
    global _default_executor
    if _default_executor is None:
        _default_executor = ServiceExecutor(config)
    return _default_executor

async def initialize_executor(config: Optional[Dict[str, Any]] = None) -> ServiceExecutor:
    """
    Initialize and return the ServiceExecutor singleton.
    """
    executor = get_executor(config)
    await executor.initialize()
    return executor
