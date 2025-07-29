import functools
import logging
import os
from typing import Dict, Any, Optional
import jaeger_client
import jaeger_client.config
from opentracing import tracer, Span

logger = logging.getLogger(__name__)


class TracingManager:
    """
    专门处理分布式追踪和链路跟踪
    """

    def __init__(self, service_name: str = "service_executor",
                 jaeger_host: Optional[str] = None,
                 jaeger_port: Optional[int] = None,
                 enable_tracing: Optional[bool] = None):
        self.service_name = service_name
        # 从环境变量获取配置，如果没有则使用默认值
        self.jaeger_host = jaeger_host or os.getenv("JAEGER_AGENT_HOST", "jaeger")
        self.jaeger_port = jaeger_port or int(os.getenv("JAEGER_AGENT_PORT", "6831"))
        self.enable_tracing = enable_tracing if enable_tracing is not None else os.getenv("JAEGER_ENABLE_TRACING", "true").lower() == "true"
        self.tracer = None

        if self.enable_tracing:
            self._init_tracer()

    def _init_tracer(self):
        """初始化 Jaeger 追踪器"""
        try:
            config = jaeger_client.config.Config(
                config={
                    'sampler': {
                        'type': 'const',
                        'param': 1,
                    },
                    'local_agent': {
                        'reporting_host': self.jaeger_host,
                        'reporting_port': self.jaeger_port,
                    },
                    'logging': True,
                },
                service_name=self.service_name,
                validate=True
            )
            self.tracer = config.initialize_tracer()
            logger.info(f"Jaeger tracer initialized for service '{self.service_name}' at {self.jaeger_host}:{self.jaeger_port}")
        except Exception as e:
            logger.warning(f"Failed to initialize Jaeger tracer: {e}")
            self.tracer = None
            self.enable_tracing = False

    def start_span(self, operation_name: str, parent_span: Optional[Span] = None,
                   tags: Optional[Dict[str, Any]] = None) -> Optional[Span]:
        """
        开始一个追踪 span

        Args:
            operation_name: 操作名称
            parent_span: 父 span
            tags: 初始标签

        Returns:
            Span 对象或 None（如果追踪未启用）
        """
        if not self.enable_tracing or not self.tracer:
            return None

        try:
            span = self.tracer.start_span(
                operation_name=operation_name,
                child_of=parent_span
            )

            # 设置初始标签
            if tags:
                for key, value in tags.items():
                    span.set_tag(key, value)

            # 设置服务信息
            span.set_tag("service.name", self.service_name)
            span.set_tag("span.kind", "server")

            return span
        except Exception as e:
            logger.error(f"Error starting span '{operation_name}': {e}")
            return None

    def finish_span(self, span: Optional[Span], tags: Optional[Dict[str, Any]] = None,
                    logs: Optional[Dict[str, Any]] = None, error: Optional[Exception] = None):
        """
        结束追踪 span

        Args:
            span: 要结束的 span
            tags: 额外的标签
            logs: 日志信息
            error: 错误信息
        """
        if not span or not self.enable_tracing:
            return

        try:
            # 添加额外标签
            if tags:
                for key, value in tags.items():
                    span.set_tag(key, value)

            # 记录错误
            if error:
                span.set_tag("error", True)
                span.set_tag("error.kind", type(error).__name__)
                span.set_tag("error.message", str(error))
                span.log_kv({"event": "error", "error.object": error})

            # 添加日志
            if logs:
                span.log_kv(logs)

            span.finish()
        except Exception as e:
            logger.error(f"Error finishing span: {e}")

    def with_tracing(self, operation_name: str, tags: Optional[Dict[str, Any]] = None):
        """
        追踪装饰器

        Args:
            operation_name: 操作名称
            tags: 初始标签
        """
        def decorator(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                if not self.enable_tracing or not self.tracer:
                    return await func(*args, **kwargs)

                span = self.start_span(operation_name, tags=tags)

                try:
                    # 添加函数参数作为标签
                    self._add_function_args_to_span(span, args, kwargs)

                    result = await func(*args, **kwargs)

                    # 记录成功
                    if span:
                        span.set_tag("success", True)

                    return result
                except Exception as e:
                    self.finish_span(span, error=e)
                    raise
                finally:
                    if span and not span.finished:
                        self.finish_span(span)

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                if not self.enable_tracing or not self.tracer:
                    return func(*args, **kwargs)

                span = self.start_span(operation_name, tags=tags)

                try:
                    # 添加函数参数作为标签
                    self._add_function_args_to_span(span, args, kwargs)

                    result = func(*args, **kwargs)

                    # 记录成功
                    if span:
                        span.set_tag("success", True)

                    return result
                except Exception as e:
                    self.finish_span(span, error=e)
                    raise
                finally:
                    if span and not span.finished:
                        self.finish_span(span)

            # 根据函数类型返回相应的包装器
            import asyncio
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper

        return decorator

    def _add_function_args_to_span(self, span: Optional[Span], args: tuple, kwargs: Dict[str, Any]):
        """将函数参数添加到 span 标签中"""
        if not span:
            return

        try:
            # 添加位置参数
            for i, arg in enumerate(args):
                if isinstance(arg, (str, int, float, bool)):
                    span.set_tag(f"arg_{i}", arg)
                elif hasattr(arg, '__class__'):
                    span.set_tag(f"arg_{i}_type", arg.__class__.__name__)

            # 添加关键字参数
            for key, value in kwargs.items():
                if isinstance(value, (str, int, float, bool)):
                    span.set_tag(key, value)
                elif isinstance(value, dict) and len(str(value)) < 1000:  # 避免过大的字典
                    span.set_tag(f"{key}_json", str(value))
                elif hasattr(value, '__class__'):
                    span.set_tag(f"{key}_type", value.__class__.__name__)
        except Exception as e:
            logger.debug(f"Error adding function args to span: {e}")

    def trace_database_operation(self, operation: str, table: str = None, query: str = None):
        """数据库操作追踪装饰器"""
        def decorator(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                tags = {
                    "component": "database",
                    "db.type": "postgresql",
                    "db.statement.type": operation
                }

                if table:
                    tags["db.table"] = table
                if query:
                    tags["db.statement"] = query[:500]  # 限制查询长度

                span = self.start_span(f"db.{operation}", tags=tags)

                try:
                    result = await func(*args, **kwargs)
                    if span:
                        span.set_tag("db.rows_affected", len(result) if isinstance(result, list) else 1)
                    return result
                except Exception as e:
                    self.finish_span(span, error=e)
                    raise
                finally:
                    if span and not span.finished:
                        self.finish_span(span)

            return wrapper
        return decorator

    def trace_external_call(self, service_name: str, endpoint: str = None):
        """外部服务调用追踪装饰器"""
        def decorator(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                tags = {
                    "component": "http",
                    "span.kind": "client",
                    "peer.service": service_name
                }

                if endpoint:
                    tags["http.url"] = endpoint

                span = self.start_span(f"http.{service_name}", tags=tags)

                try:
                    result = await func(*args, **kwargs)
                    if span:
                        span.set_tag("http.status_code", 200)
                    return result
                except Exception as e:
                    if span:
                        span.set_tag("http.status_code", 500)
                    self.finish_span(span, error=e)
                    raise
                finally:
                    if span and not span.finished:
                        self.finish_span(span)

            return wrapper
        return decorator

    def trace_tool_execution(self, tool_name: str, operation: str):
        """工具执行追踪装饰器"""
        def decorator(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                tags = {
                    "component": "tool",
                    "tool.name": tool_name,
                    "tool.operation": operation
                }

                span = self.start_span(f"tool.{tool_name}.{operation}", tags=tags)

                try:
                    result = await func(*args, **kwargs)
                    if span:
                        span.set_tag("tool.success", True)
                        if hasattr(result, '__len__'):
                            span.set_tag("tool.result_size", len(result))
                    return result
                except Exception as e:
                    if span:
                        span.set_tag("tool.success", False)
                    self.finish_span(span, error=e)
                    raise
                finally:
                    if span and not span.finished:
                        self.finish_span(span)

            return wrapper
        return decorator

    def create_child_span(self, parent_span: Optional[Span], operation_name: str,
                         tags: Optional[Dict[str, Any]] = None) -> Optional[Span]:
        """创建子 span"""
        if not self.enable_tracing or not parent_span:
            return None

        return self.start_span(operation_name, parent_span=parent_span, tags=tags)

    def inject_span_context(self, span: Optional[Span], carrier: Dict[str, str]):
        """将 span 上下文注入到载体中（用于跨服务传播）"""
        if not self.enable_tracing or not span or not self.tracer:
            return

        try:
            from opentracing.propagation import Format
            self.tracer.inject(span.context, Format.TEXT_MAP, carrier)
        except Exception as e:
            logger.error(f"Error injecting span context: {e}")

    def extract_span_context(self, carrier: Dict[str, str]) -> Optional[Any]:
        """从载体中提取 span 上下文"""
        if not self.enable_tracing or not self.tracer:
            return None

        try:
            from opentracing.propagation import Format
            return self.tracer.extract(Format.TEXT_MAP, carrier)
        except Exception as e:
            logger.error(f"Error extracting span context: {e}")
            return None

    def get_active_span(self) -> Optional[Span]:
        """获取当前活跃的 span"""
        if not self.enable_tracing or not self.tracer:
            return None

        try:
            return self.tracer.active_span
        except Exception as e:
            logger.error(f"Error getting active span: {e}")
            return None

    def close_tracer(self):
        """关闭追踪器"""
        if self.tracer:
            try:
                self.tracer.close()
                logger.info("Tracer closed successfully")
            except Exception as e:
                logger.error(f"Error closing tracer: {e}")

    def get_tracer_info(self) -> Dict[str, Any]:
        """获取追踪器信息"""
        return {
            "enabled": self.enable_tracing,
            "service_name": self.service_name,
            "jaeger_host": self.jaeger_host,
            "jaeger_port": self.jaeger_port,
            "tracer_initialized": self.tracer is not None
        }
