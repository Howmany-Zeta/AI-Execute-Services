import os
import asyncio
import functools
import hashlib
import inspect
import json
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional, Type, Union, get_type_hints
from contextlib import contextmanager

from cachetools import LRUCache
from aiecs.utils.execution_utils import ExecutionUtils
import re
from pydantic import BaseModel, ValidationError, ConfigDict

logger = logging.getLogger(__name__)

# Base exception hierarchy
class ToolExecutionError(Exception):
    """Base exception for all tool execution errors."""
    pass

class InputValidationError(ToolExecutionError):
    """Error in validating input parameters."""
    pass

class SecurityError(ToolExecutionError):
    """Security-related error."""
    pass

class OperationError(ToolExecutionError):
    """Error during operation execution."""
    pass

class TimeoutError(ToolExecutionError):
    """Operation timed out."""
    pass

# Configuration for the executor
class ExecutorConfig(BaseModel):
    """
    Configuration for the ToolExecutor.

    Attributes:
        enable_cache (bool): Enable caching of operation results.
        cache_size (int): Maximum number of cache entries.
        cache_ttl (int): Cache time-to-live in seconds.
        max_workers (int): Maximum number of thread pool workers.
        io_concurrency (int): Maximum concurrent I/O operations.
        chunk_size (int): Chunk size for processing large data.
        max_file_size (int): Maximum file size in bytes.
        log_level (str): Logging level (e.g., 'INFO', 'DEBUG').
        log_execution_time (bool): Log execution time for operations.
        enable_security_checks (bool): Enable security checks for inputs.
        retry_attempts (int): Number of retry attempts for transient errors.
        retry_backoff (float): Backoff factor for retries.
        timeout (int): Timeout for operations in seconds.
    """
    enable_cache: bool = True
    cache_size: int = 100
    cache_ttl: int = 3600
    max_workers: int = 4
    io_concurrency: int = 8
    chunk_size: int = 10000
    max_file_size: int = 1000000
    log_level: str = "INFO"
    log_execution_time: bool = True
    enable_security_checks: bool = True
    retry_attempts: int = 3
    retry_backoff: float = 1.0
    timeout: int = 30

    model_config = ConfigDict(env_prefix="TOOL_EXECUTOR_")

# Metrics counter
class ExecutorMetrics:
    """
    Tracks executor performance metrics.
    """
    def __init__(self):
        self.requests: int = 0
        self.failures: int = 0
        self.cache_hits: int = 0
        self.processing_times: List[float] = []

    def record_request(self, processing_time: float):
        self.requests += 1
        self.processing_times.append(processing_time)

    def record_failure(self):
        self.failures += 1

    def record_cache_hit(self):
        self.cache_hits += 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            'requests': self.requests,
            'failures': self.failures,
            'cache_hits': self.cache_hits,
            'avg_processing_time': sum(self.processing_times) / len(self.processing_times) if self.processing_times else 0.0
        }

# Decorators for tool methods
def validate_input(schema_class: Type[BaseModel]) -> Callable:
    """
    Decorator to validate input using a Pydantic schema.

    Args:
        schema_class (Type[BaseModel]): Pydantic schema class for validation.

    Returns:
        Callable: Decorated function with validated inputs.

    Raises:
        InputValidationError: If input validation fails.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                schema = schema_class(**kwargs)
                validated_kwargs = schema.model_dump(exclude_unset=True)
                return func(self, **validated_kwargs)
            except ValidationError as e:
                raise InputValidationError(f"Invalid input parameters: {e}")
        return wrapper
    return decorator

def cache_result(ttl: Optional[int] = None) -> Callable:
    """
    Decorator to cache function results with optional TTL.

    Args:
        ttl (Optional[int]): Time-to-live for cache entry in seconds.

    Returns:
        Callable: Decorated function with caching.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            if not hasattr(self, '_executor') or not self._executor.config.enable_cache:
                return func(self, *args, **kwargs)
            cache_key = self._executor._get_cache_key(func.__name__, args, kwargs)
            result = self._executor._get_from_cache(cache_key)
            if result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                self._executor._metrics.record_cache_hit()
                return result
            result = func(self, *args, **kwargs)
            self._executor._add_to_cache(cache_key, result, ttl)
            return result
        return wrapper
    return decorator

def run_in_executor(func: Callable) -> Callable:
    """
    Decorator to run a synchronous function in the thread pool executor.

    Args:
        func (Callable): Function to execute.

    Returns:
        Callable: Async wrapper for the function.
    """
    @functools.wraps(func)
    async def wrapper(self, *args, **kwargs):
        if not hasattr(self, '_executor'):
            return await func(self, *args, **kwargs)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor._thread_pool,
            functools.partial(func, self, *args, **kwargs)
        )
    return wrapper

def measure_execution_time(func: Callable) -> Callable:
    """
    Decorator to measure and log execution time.

    Args:
        func (Callable): Function to measure.

    Returns:
        Callable: Decorated function with timing.
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if not hasattr(self, '_executor') or not self._executor.config.log_execution_time:
            return func(self, *args, **kwargs)
        start_time = time.time()
        try:
            result = func(self, *args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(f"{func.__name__} executed in {execution_time:.4f} seconds")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{func.__name__} failed after {execution_time:.4f} seconds: {e}")
            raise
    return wrapper

def sanitize_input(func: Callable) -> Callable:
    """
    Decorator to sanitize input parameters for security.

    Args:
        func (Callable): Function to sanitize inputs for.

    Returns:
        Callable: Decorated function with sanitized inputs.
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if not hasattr(self, '_executor') or not self._executor.config.enable_security_checks:
            return func(self, *args, **kwargs)
        sanitized_kwargs = {}
        for k, v in kwargs.items():
            if isinstance(v, str) and re.search(r'(\bSELECT\b|\bINSERT\b|--|;|/\*)', v, re.IGNORECASE):
                raise SecurityError(f"Input parameter '{k}' contains potentially malicious content")
            sanitized_kwargs[k] = v
        return func(self, *args, **sanitized_kwargs)
    return wrapper

class ToolExecutor:
    """
    Centralized executor for tool operations, handling:
    - Input validation
    - Caching with TTL and content-based keys
    - Concurrency with dynamic thread pool
    - Error handling with retries
    - Performance optimization with metrics
    - Structured logging

    Example:
        executor = ToolExecutor(config={'max_workers': 8})
        result = executor.execute(tool_instance, 'operation_name', param1='value')
    """
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the executor with optional configuration.

        Args:
            config (Dict[str, Any], optional): Configuration overrides for ExecutorConfig.

        Raises:
            ValueError: If config is invalid.
        """
        self.config = ExecutorConfig(**(config or {}))
        logging.basicConfig(
            level=getattr(logging, self.config.log_level),
            format='%(asctime)s %(levelname)s %(name)s: %(message)s'
        )
        self._thread_pool = ThreadPoolExecutor(max_workers=max(os.cpu_count() or 4, self.config.max_workers))
        self._locks: Dict[str, threading.Lock] = {}
        self._metrics = ExecutorMetrics()
        self.execution_utils = ExecutionUtils(
            cache_size=self.config.cache_size,
            cache_ttl=self.config.cache_ttl,
            retry_attempts=self.config.retry_attempts,
            retry_backoff=self.config.retry_backoff
        )

    def _get_cache_key(self, func_name: str, args: tuple, kwargs: Dict[str, Any]) -> str:
        """
        Generate a context-aware cache key from function name, user ID, task ID, and arguments.

        Args:
            func_name (str): Name of the function.
            args (tuple): Positional arguments.
            kwargs (Dict[str, Any]): Keyword arguments.

        Returns:
            str: Cache key.
        """
        user_id = kwargs.get("user_id", "anonymous")
        task_id = kwargs.get("task_id", "none")
        return self.execution_utils.generate_cache_key(func_name, user_id, task_id, args, kwargs)

    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """
        Get a result from cache if it exists and is not expired.

        Args:
            cache_key (str): Cache key.

        Returns:
            Optional[Any]: Cached result or None.
        """
        if not self.config.enable_cache:
            return None
        return self.execution_utils.get_from_cache(cache_key)

    def _add_to_cache(self, cache_key: str, result: Any, ttl: Optional[int] = None) -> None:
        """
        Add a result to the cache with optional TTL.

        Args:
            cache_key (str): Cache key.
            result (Any): Result to cache.
            ttl (Optional[int]): Time-to-live in seconds.
        """
        if not self.config.enable_cache:
            return
        self.execution_utils.add_to_cache(cache_key, result, ttl)

    def get_lock(self, resource_id: str) -> threading.Lock:
        """
        Get or create a lock for a specific resource.

        Args:
            resource_id (str): Resource identifier.

        Returns:
            threading.Lock: Lock for the resource.
        """
        if resource_id not in self._locks:
            self._locks[resource_id] = threading.Lock()
        return self._locks[resource_id]

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get current executor metrics.

        Returns:
            Dict[str, Any]: Metrics including request count, failures, cache hits, and average processing time.
        """
        return self._metrics.to_dict()

    @contextmanager
    def timeout_context(self, seconds: int):
        """
        Context manager for enforcing operation timeouts.

        Args:
            seconds (int): Timeout duration in seconds.

        Raises:
            TimeoutError: If operation exceeds timeout.
        """
        return self.execution_utils.timeout_context(seconds)

    async def _retry_operation(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute an operation with retries for transient errors.

        Args:
            func (Callable): Function to execute.
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
            Any: Result of the operation.

        Raises:
            OperationError: If all retries fail.
        """
        return await self.execution_utils.execute_with_retry_and_timeout(func, self.config.timeout, *args, **kwargs)

    def execute(self, tool_instance: Any, operation: str, **kwargs) -> Any:
        """
        Execute a synchronous tool operation with parameters.

        Args:
            tool_instance (Any): The tool instance to execute the operation on.
            operation (str): The name of the operation to execute.
            **kwargs: The parameters to pass to the operation.

        Returns:
            Any: The result of the operation.

        Raises:
            ToolExecutionError: If the operation fails.
            InputValidationError: If input parameters are invalid.
            SecurityError: If inputs contain malicious content.
        """
        method = getattr(tool_instance, operation, None)
        if not method or not callable(method) or operation.startswith('_'):
            available_ops = [m for m in dir(tool_instance) if not m.startswith('_') and callable(getattr(tool_instance, m))]
            raise ToolExecutionError(f"Unsupported operation: {operation}. Available operations: {', '.join(available_ops)}")
        logger.info(f"Executing {tool_instance.__class__.__name__}.{operation} with params: {kwargs}")
        start_time = time.time()
        try:
            # Sanitize inputs
            if self.config.enable_security_checks:
                for k, v in kwargs.items():
                    if isinstance(v, str) and re.search(r'(\bSELECT\b|\bINSERT\b|--|;|/\*)', v, re.IGNORECASE):
                        raise SecurityError(f"Input parameter '{k}' contains potentially malicious content")
            # Use cache if enabled
            if self.config.enable_cache:
                cache_key = self._get_cache_key(operation, (), kwargs)
                cached_result = self._get_from_cache(cache_key)
                if cached_result is not None:
                    self._metrics.record_cache_hit()
                    logger.debug(f"Cache hit for {operation}")
                    return cached_result

            result = method(**kwargs)
            self._metrics.record_request(time.time() - start_time)
            if self.config.log_execution_time:
                logger.info(f"{tool_instance.__class__.__name__}.{operation} executed in {time.time() - start_time:.4f} seconds")

            # Cache result if enabled
            if self.config.enable_cache:
                self._add_to_cache(cache_key, result)
            return result
        except Exception as e:
            self._metrics.record_failure()
            logger.error(f"Error executing {tool_instance.__class__.__name__}.{operation}: {str(e)}", exc_info=True)
            raise OperationError(f"Error executing {operation}: {str(e)}") from e

    async def execute_async(self, tool_instance: Any, operation: str, **kwargs) -> Any:
        """
        Execute an asynchronous tool operation with parameters.

        Args:
            tool_instance (Any): The tool instance to execute the operation on.
            operation (str): The name of the operation to execute.
            **kwargs: The parameters to pass to the operation.

        Returns:
            Any: The result of the operation.

        Raises:
            ToolExecutionError: If the operation fails.
            InputValidationError: If input parameters are invalid.
            SecurityError: If inputs contain malicious content.
        """
        method = getattr(tool_instance, operation, None)
        if not method or not callable(method) or operation.startswith('_'):
            available_ops = [m for m in dir(tool_instance) if not m.startswith('_') and callable(getattr(tool_instance, m))]
            raise ToolExecutionError(f"Unsupported operation: {operation}. Available operations: {', '.join(available_ops)}")
        is_async = inspect.iscoroutinefunction(method)
        logger.info(f"Executing async {tool_instance.__class__.__name__}.{operation} with params: {kwargs}")
        start_time = time.time()
        try:
            # Sanitize inputs
            if self.config.enable_security_checks:
                for k, v in kwargs.items():
                    if isinstance(v, str) and re.search(r'(\bSELECT\b|\bINSERT\b|--|;|/\*)', v, re.IGNORECASE):
                        raise SecurityError(f"Input parameter '{k}' contains potentially malicious content")
            # Use cache if enabled
            if self.config.enable_cache:
                cache_key = self._get_cache_key(operation, (), kwargs)
                cached_result = self._get_from_cache(cache_key)
                if cached_result is not None:
                    self._metrics.record_cache_hit()
                    logger.debug(f"Cache hit for {operation}")
                    return cached_result

            async def _execute():
                if is_async:
                    return await method(**kwargs)
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(self._thread_pool, functools.partial(method, **kwargs))
            result = await self._retry_operation(_execute)
            self._metrics.record_request(time.time() - start_time)
            if self.config.log_execution_time:
                logger.info(f"{tool_instance.__class__.__name__}.{operation} executed in {time.time() - start_time:.4f} seconds")

            # Cache result if enabled
            if self.config.enable_cache:
                self._add_to_cache(cache_key, result)
            return result
        except Exception as e:
            self._metrics.record_failure()
            logger.error(f"Error executing {tool_instance.__class__.__name__}.{operation}: {str(e)}", exc_info=True)
            raise OperationError(f"Error executing {operation}: {str(e)}") from e

    async def execute_batch(self, tool_instance: Any, operations: List[Dict[str, Any]]) -> List[Any]:
        """
        Execute multiple tool operations in parallel.

        Args:
            tool_instance (Any): The tool instance to execute operations on.
            operations (List[Dict[str, Any]]): List of operation dictionaries with 'op' and 'kwargs'.

        Returns:
            List[Any]: List of operation results.

        Raises:
            ToolExecutionError: If any operation fails.
            InputValidationError: If input parameters are invalid.
        """
        tasks = []
        for op_data in operations:
            op = op_data.get('op')
            kwargs = op_data.get('kwargs', {})
            if not op:
                raise InputValidationError("Operation name missing in batch request")
            tasks.append(self.execute_async(tool_instance, op, **kwargs))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Batch operation {operations[i]['op']} failed: {result}")
        return results

# Singleton executor instance
_default_executor = None

def get_executor(config: Optional[Dict[str, Any]] = None) -> ToolExecutor:
    """
    Get or create the default executor instance.

    Args:
        config (Dict[str, Any], optional): Configuration overrides.

    Returns:
        ToolExecutor: Singleton executor instance.
    """
    global _default_executor
    if _default_executor is None:
        _default_executor = ToolExecutor(config)
    return _default_executor
