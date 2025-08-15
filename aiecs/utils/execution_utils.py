import json
import asyncio
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple
from cachetools import LRUCache
from contextlib import contextmanager
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, after_log

logger = logging.getLogger(__name__)

class ExecutionUtils:
    """
    提供执行层的公共工具集，包括缓存和重试逻辑。
    """
    def __init__(self, cache_size: int = 100, cache_ttl: int = 3600, retry_attempts: int = 3, retry_backoff: float = 1.0):
        """
        初始化执行工具类。
        
        Args:
            cache_size (int): 缓存的最大条目数
            cache_ttl (int): 缓存的生存时间（秒）
            retry_attempts (int): 重试尝试次数
            retry_backoff (float): 重试的退避因子
        """
        self.cache_size = cache_size
        self.cache_ttl = cache_ttl
        self.retry_attempts = retry_attempts
        self.retry_backoff = retry_backoff
        self._cache = LRUCache(maxsize=self.cache_size) if cache_size > 0 else None
        self._cache_lock = threading.Lock()
        self._cache_ttl_dict: Dict[str, float] = {}
        
    def generate_cache_key(self, func_name: str, user_id: str, task_id: str, args: tuple, kwargs: Dict[str, Any]) -> str:
        """
        生成基于上下文的缓存键，包括用户ID、任务ID、函数名和参数。
        
        Args:
            func_name (str): 函数名称
            user_id (str): 用户ID
            task_id (str): 任务ID
            args (tuple): 位置参数
            kwargs (Dict[str, Any]): 关键字参数
            
        Returns:
            str: 缓存键
        """
        key_dict = {
            'func': func_name,
            'user_id': user_id,
            'task_id': task_id,
            'args': args,
            'kwargs': {k: v for k, v in kwargs.items() if k != 'self'}
        }
        try:
            key_str = json.dumps(key_dict, sort_keys=True)
        except (TypeError, ValueError):
            key_str = str(key_dict)
        return hash(key_str).__str__()

    def get_from_cache(self, cache_key: str) -> Optional[Any]:
        """
        从缓存中获取结果，如果存在且未过期。
        
        Args:
            cache_key (str): 缓存键
            
        Returns:
            Optional[Any]: 缓存结果或None
        """
        if not self._cache:
            return None
        with self._cache_lock:
            if cache_key in self._cache:
                if cache_key in self._cache_ttl_dict and time.time() > self._cache_ttl_dict[cache_key]:
                    del self._cache[cache_key]
                    del self._cache_ttl_dict[cache_key]
                    return None
                return self._cache[cache_key]
        return None

    def add_to_cache(self, cache_key: str, result: Any, ttl: Optional[int] = None) -> None:
        """
        将结果添加到缓存中，可选设置生存时间。
        
        Args:
            cache_key (str): 缓存键
            result (Any): 缓存结果
            ttl (Optional[int]): 生存时间（秒）
        """
        if not self._cache:
            return
        with self._cache_lock:
            self._cache[cache_key] = result
            ttl = ttl if ttl is not None else self.cache_ttl
            if ttl > 0:
                self._cache_ttl_dict[cache_key] = time.time() + ttl

    def create_retry_strategy(self, metric_name: Optional[str] = None) -> Callable:
        """
        创建重试策略，适用于执行操作。
        
        Args:
            metric_name (Optional[str]): 指标名称，用于日志记录
            
        Returns:
            Callable: 重试装饰器
        """
        def after_retry(retry_state):
            logger.warning(f"Retry {retry_state.attempt_number}/{self.retry_attempts} for {metric_name or 'operation'} after {retry_state.idle_for}s: {retry_state.outcome.exception()}")
        
        return retry(
            stop=stop_after_attempt(self.retry_attempts),
            wait=wait_exponential(multiplier=self.retry_backoff, min=1, max=10),
            after=after_retry
        )

    @contextmanager
    def timeout_context(self, seconds: int):
        """
        上下文管理器，用于强制执行操作超时。
        
        Args:
            seconds (int): 超时时间（秒）
            
        Raises:
            TimeoutError: 如果操作超过超时时间
        """
        loop = asyncio.get_event_loop()
        future = asyncio.Future()
        handle = loop.call_later(seconds, lambda: future.set_exception(TimeoutError(f"Operation timed out after {seconds}s")))
        try:
            yield future
        finally:
            handle.cancel()

    async def execute_with_retry_and_timeout(self, func: Callable, timeout: int, *args, **kwargs) -> Any:
        """
        使用重试和超时机制执行操作。
        
        Args:
            func (Callable): 要执行的函数
            timeout (int): 超时时间（秒）
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            Any: 操作结果
            
        Raises:
            OperationError: 如果所有重试尝试失败
        """
        retry_strategy = self.create_retry_strategy(func.__name__)
        try:
            return await asyncio.wait_for(retry_strategy(func)(*args, **kwargs), timeout=timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Operation timed out after {timeout}s")