import functools
import logging
import os
from typing import Dict, Any, Optional
import jaeger_client
import jaeger_client.config
from opentracing import Span

logger = logging.getLogger(__name__)


class TracingManager:
    """
    Specialized handler for distributed tracing and link tracking
    """

    def __init__(
        self,
        service_name: str = "service_executor",
        jaeger_host: Optional[str] = None,
        jaeger_port: Optional[int] = None,
        enable_tracing: Optional[bool] = None,
    ):
        self.service_name = service_name
        # Get configuration from environment variables, use defaults if not
        # available
        self.jaeger_host = jaeger_host or os.getenv("JAEGER_AGENT_HOST", "jaeger")
        self.jaeger_port = jaeger_port or int(os.getenv("JAEGER_AGENT_PORT", "6831"))
        self.enable_tracing = enable_tracing if enable_tracing is not None else os.getenv("JAEGER_ENABLE_TRACING", "true").lower() == "true"
        self.tracer = None

        if self.enable_tracing:
            self._init_tracer()

    def _init_tracer(self):
        """Initialize Jaeger tracer"""
        try:
            config = jaeger_client.config.Config(
                config={
                    "sampler": {
                        "type": "const",
                        "param": 1,
                    },
                    "local_agent": {
                        "reporting_host": self.jaeger_host,
                        "reporting_port": self.jaeger_port,
                    },
                    "logging": True,
                },
                service_name=self.service_name,
                validate=True,
            )
            self.tracer = config.initialize_tracer()
            logger.info(f"Jaeger tracer initialized for service '{self.service_name}' at {self.jaeger_host}:{self.jaeger_port}")
        except Exception as e:
            logger.warning(f"Failed to initialize Jaeger tracer: {e}")
            self.tracer = None
            self.enable_tracing = False

    def start_span(
        self,
        operation_name: str,
        parent_span: Optional[Span] = None,
        tags: Optional[Dict[str, Any]] = None,
    ) -> Optional[Span]:
        """
        Start a tracing span

        Args:
            operation_name: Operation name
            parent_span: Parent span
            tags: Initial tags

        Returns:
            Span object or None (if tracing is not enabled)
        """
        if not self.enable_tracing or not self.tracer:
            return None

        try:
            span = self.tracer.start_span(operation_name=operation_name, child_of=parent_span)

            # Set initial tags
            if tags:
                for key, value in tags.items():
                    span.set_tag(key, value)

            # Set service information
            span.set_tag("service.name", self.service_name)
            span.set_tag("span.kind", "server")

            return span
        except Exception as e:
            logger.error(f"Error starting span '{operation_name}': {e}")
            return None

    def finish_span(
        self,
        span: Optional[Span],
        tags: Optional[Dict[str, Any]] = None,
        logs: Optional[Dict[str, Any]] = None,
        error: Optional[Exception] = None,
    ):
        """
        Finish tracing span

        Args:
            span: Span to finish
            tags: Additional tags
            logs: Log information
            error: Error information
        """
        if not span or not self.enable_tracing:
            return

        try:
            # Add additional tags
            if tags:
                for key, value in tags.items():
                    span.set_tag(key, value)

            # Record error
            if error:
                span.set_tag("error", True)
                span.set_tag("error.kind", type(error).__name__)
                span.set_tag("error.message", str(error))
                span.log_kv({"event": "error", "error.object": error})

            # Add logs
            if logs:
                span.log_kv(logs)

            span.finish()
        except Exception as e:
            logger.error(f"Error finishing span: {e}")

    def with_tracing(self, operation_name: str, tags: Optional[Dict[str, Any]] = None):
        """
        Tracing decorator

        Args:
            operation_name: Operation name
            tags: Initial tags
        """

        def decorator(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                if not self.enable_tracing or not self.tracer:
                    return await func(*args, **kwargs)

                span = self.start_span(operation_name, tags=tags)

                try:
                    # Add function arguments as tags
                    self._add_function_args_to_span(span, args, kwargs)

                    result = await func(*args, **kwargs)

                    # Record success
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
                    # Add function arguments as tags
                    self._add_function_args_to_span(span, args, kwargs)

                    result = func(*args, **kwargs)

                    # Record success
                    if span:
                        span.set_tag("success", True)

                    return result
                except Exception as e:
                    self.finish_span(span, error=e)
                    raise
                finally:
                    if span and not span.finished:
                        self.finish_span(span)

            # Return appropriate wrapper based on function type
            import asyncio

            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper

        return decorator

    def _add_function_args_to_span(self, span: Optional[Span], args: tuple, kwargs: Dict[str, Any]):
        """Add function arguments to span tags"""
        if not span:
            return

        try:
            # Add positional arguments
            for i, arg in enumerate(args):
                if isinstance(arg, (str, int, float, bool)):
                    span.set_tag(f"arg_{i}", arg)
                elif hasattr(arg, "__class__"):
                    span.set_tag(f"arg_{i}_type", arg.__class__.__name__)

            # Add keyword arguments
            for key, value in kwargs.items():
                if isinstance(value, (str, int, float, bool)):
                    span.set_tag(key, value)
                # Avoid overly large dictionaries
                elif isinstance(value, dict) and len(str(value)) < 1000:
                    span.set_tag(f"{key}_json", str(value))
                elif hasattr(value, "__class__"):
                    span.set_tag(f"{key}_type", value.__class__.__name__)
        except Exception as e:
            logger.debug(f"Error adding function args to span: {e}")

    def trace_database_operation(self, operation: str, table: Optional[str] = None, query: Optional[str] = None):
        """Database operation tracing decorator"""

        def decorator(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                tags = {
                    "component": "database",
                    "db.type": "postgresql",
                    "db.statement.type": operation,
                }

                if table:
                    tags["db.table"] = table
                if query:
                    tags["db.statement"] = query[:500]  # Limit query length

                span = self.start_span(f"db.{operation}", tags=tags)

                try:
                    result = await func(*args, **kwargs)
                    if span:
                        span.set_tag(
                            "db.rows_affected",
                            len(result) if isinstance(result, list) else 1,
                        )
                    return result
                except Exception as e:
                    self.finish_span(span, error=e)
                    raise
                finally:
                    if span and not span.finished:
                        self.finish_span(span)

            return wrapper

        return decorator

    def trace_external_call(self, service_name: str, endpoint: Optional[str] = None):
        """External service call tracing decorator"""

        def decorator(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                tags = {
                    "component": "http",
                    "span.kind": "client",
                    "peer.service": service_name,
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
        """Tool execution tracing decorator"""

        def decorator(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                tags = {
                    "component": "tool",
                    "tool.name": tool_name,
                    "tool.operation": operation,
                }

                span = self.start_span(f"tool.{tool_name}.{operation}", tags=tags)

                try:
                    result = await func(*args, **kwargs)
                    if span:
                        span.set_tag("tool.success", True)
                        if hasattr(result, "__len__"):
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

    def create_child_span(
        self,
        parent_span: Optional[Span],
        operation_name: str,
        tags: Optional[Dict[str, Any]] = None,
    ) -> Optional[Span]:
        """Create child span"""
        if not self.enable_tracing or not parent_span:
            return None

        return self.start_span(operation_name, parent_span=parent_span, tags=tags)

    def inject_span_context(self, span: Optional[Span], carrier: Dict[str, str]):
        """Inject span context into carrier (for cross-service propagation)"""
        if not self.enable_tracing or not span or not self.tracer:
            return

        try:
            from opentracing.propagation import Format

            self.tracer.inject(span.context, Format.TEXT_MAP, carrier)
        except Exception as e:
            logger.error(f"Error injecting span context: {e}")

    def extract_span_context(self, carrier: Dict[str, str]) -> Optional[Any]:
        """Extract span context from carrier"""
        if not self.enable_tracing or not self.tracer:
            return None

        try:
            from opentracing.propagation import Format

            return self.tracer.extract(Format.TEXT_MAP, carrier)
        except Exception as e:
            logger.error(f"Error extracting span context: {e}")
            return None

    def get_active_span(self) -> Optional[Span]:
        """Get current active span"""
        if not self.enable_tracing or not self.tracer:
            return None

        try:
            return self.tracer.active_span
        except Exception as e:
            logger.error(f"Error getting active span: {e}")
            return None

    def close_tracer(self):
        """Close tracer"""
        if self.tracer:
            try:
                self.tracer.close()
                logger.info("Tracer closed successfully")
            except Exception as e:
                logger.error(f"Error closing tracer: {e}")

    def get_tracer_info(self) -> Dict[str, Any]:
        """Get tracer information"""
        return {
            "enabled": self.enable_tracing,
            "service_name": self.service_name,
            "jaeger_host": self.jaeger_host,
            "jaeger_port": self.jaeger_port,
            "tracer_initialized": self.tracer is not None,
        }
