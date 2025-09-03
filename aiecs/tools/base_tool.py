import asyncio
import inspect
import logging
from typing import Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel, ValidationError
import re

from aiecs.tools.tool_executor import (
    ToolExecutor,
    ToolExecutionError,
    InputValidationError,
    OperationError,
    SecurityError,
    get_executor,
    validate_input,
    cache_result,
    run_in_executor,
    measure_execution_time,
    sanitize_input
)

logger = logging.getLogger(__name__)

class BaseTool:
    """
    Base class for all tools, providing common functionality:
    - Input validation with Pydantic schemas
    - Caching with TTL and content-based keys
    - Concurrency with async/sync execution
    - Error handling with retries and context
    - Performance optimization with metrics
    - Logging with structured output

    Tools inheriting from this class focus on business logic, leveraging
    the executor's cross-cutting concerns.

    Example:
        class MyTool(BaseTool):
            class ReadSchema(BaseModel):
                path: str

            @validate_input(ReadSchema)
            @cache_result(ttl=300)
            @run_in_executor
            @measure_execution_time
            @sanitize_input
            def read(self, path: str):
                # Implementation
                pass
    """
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the tool with optional configuration.

        Args:
            config (Dict[str, Any], optional): Tool-specific configuration.

        Raises:
            ValueError: If config is invalid.
        """
        self._executor = get_executor(config)
        self._config = config or {}
        self._schemas: Dict[str, Type[BaseModel]] = {}
        self._async_methods: List[str] = []
        self._register_schemas()
        self._register_async_methods()

    def _register_schemas(self) -> None:
        """
        Register Pydantic schemas for operations by inspecting inner Schema classes.

        Example:
            class MyTool(BaseTool):
                class ReadSchema(BaseModel):
                    path: str
                def read(self, path: str):
                    pass
            # Registers 'read' -> ReadSchema
        """
        for attr_name in dir(self.__class__):
            attr = getattr(self.__class__, attr_name)
            if isinstance(attr, type) and issubclass(attr, BaseModel) and attr.__name__.endswith('Schema'):
                op_name = attr.__name__.replace('Schema', '').lower()
                self._schemas[op_name] = attr

    def _register_async_methods(self) -> None:
        """
        Register async methods for proper execution handling.
        """
        for attr_name in dir(self.__class__):
            attr = getattr(self.__class__, attr_name)
            if inspect.iscoroutinefunction(attr) and not attr_name.startswith('_'):
                self._async_methods.append(attr_name)

    def _sanitize_kwargs(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize keyword arguments to prevent injection attacks.

        Args:
            kwargs (Dict[str, Any]): Input keyword arguments.

        Returns:
            Dict[str, Any]: Sanitized keyword arguments.

        Raises:
            SecurityError: If kwargs contain malicious content.
        """
        sanitized = {}
        for k, v in kwargs.items():
            if isinstance(v, str) and re.search(r'(\bSELECT\b|\bINSERT\b|--|;|/\*)', v, re.IGNORECASE):
                raise SecurityError(f"Input parameter '{k}' contains potentially malicious content")
            sanitized[k] = v
        return sanitized

    def run(self, op: str, **kwargs) -> Any:
        """
        Execute a synchronous operation with parameters.

        Args:
            op (str): The name of the operation to execute.
            **kwargs: The parameters to pass to the operation.

        Returns:
            Any: The result of the operation.

        Raises:
            ToolExecutionError: If the operation fails.
            InputValidationError: If input parameters are invalid.
            SecurityError: If inputs contain malicious content.
        """
        schema_class = self._schemas.get(op)
        if schema_class:
            try:
                schema = schema_class(**kwargs)
                kwargs = schema.model_dump(exclude_unset=True)
            except ValidationError as e:
                raise InputValidationError(f"Invalid input parameters: {e}")
        kwargs = self._sanitize_kwargs(kwargs)
        return self._executor.execute(self, op, **kwargs)

    async def run_async(self, op: str, **kwargs) -> Any:
        """
        Execute an asynchronous operation with parameters.

        Args:
            op (str): The name of the operation to execute.
            **kwargs: The parameters to pass to the operation.

        Returns:
            Any: The result of the operation.

        Raises:
            ToolExecutionError: If the operation fails.
            InputValidationError: If input parameters are invalid.
            SecurityError: If inputs contain malicious content.
        """
        schema_class = self._schemas.get(op)
        if schema_class:
            try:
                schema = schema_class(**kwargs)
                kwargs = schema.model_dump(exclude_unset=True)
            except ValidationError as e:
                raise InputValidationError(f"Invalid input parameters: {e}")
        kwargs = self._sanitize_kwargs(kwargs)
        return await self._executor.execute_async(self, op, **kwargs)

    async def run_batch(self, operations: List[Dict[str, Any]]) -> List[Any]:
        """
        Execute multiple operations in parallel.

        Args:
            operations (List[Dict[str, Any]]): List of operation dictionaries with 'op' and 'kwargs'.

        Returns:
            List[Any]: List of operation results.

        Raises:
            ToolExecutionError: If any operation fails.
            InputValidationError: If input parameters are invalid.
        """
        return await self._executor.execute_batch(self, operations)

    def _get_method_schema(self, method_name: str) -> Optional[Type[BaseModel]]:
        """
        Get the schema for a method if it exists.

        Args:
            method_name (str): The name of the method.

        Returns:
            Optional[Type[BaseModel]]: The schema class or None.
        """
        if method_name in self._schemas:
            return self._schemas[method_name]
        schema_name = method_name[0].upper() + method_name[1:] + 'Schema'
        for attr_name in dir(self.__class__):
            if attr_name == schema_name:
                attr = getattr(self.__class__, attr_name)
                if isinstance(attr, type) and issubclass(attr, BaseModel):
                    return attr
        return None
