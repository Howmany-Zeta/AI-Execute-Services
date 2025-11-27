"""
Graph Store Caching Layer

Provides caching capabilities for graph storage backends using Redis.
Supports TTL-based expiration, invalidation, and cache warming.
"""

import json
import hashlib
import logging
from typing import Any, Dict, Optional, Callable
from functools import wraps
import asyncio

logger = logging.getLogger(__name__)


class GraphStoreCacheConfig:
    """Configuration for graph store caching"""

    def __init__(
        self,
        enabled: bool = True,
        ttl: int = 300,  # 5 minutes default
        max_cache_size_mb: int = 100,
        redis_url: Optional[str] = None,
        key_prefix: str = "graph:",
    ):
        """
        Initialize cache configuration

        Args:
            enabled: Enable/disable caching
            ttl: Time-to-live for cache entries in seconds
            max_cache_size_mb: Maximum cache size in MB (for in-memory fallback)
            redis_url: Redis connection URL (e.g., "redis://localhost:6379/0")
            key_prefix: Prefix for all cache keys
        """
        self.enabled = enabled
        self.ttl = ttl
        self.max_cache_size_mb = max_cache_size_mb
        self.redis_url = redis_url
        self.key_prefix = key_prefix


class CacheBackend:
    """Abstract cache backend interface"""

    async def get(self, key: str) -> Optional[str]:
        """Get value from cache"""
        raise NotImplementedError

    async def set(self, key: str, value: str, ttl: int) -> None:
        """Set value in cache with TTL"""
        raise NotImplementedError

    async def delete(self, key: str) -> None:
        """Delete key from cache"""
        raise NotImplementedError

    async def delete_pattern(self, pattern: str) -> None:
        """Delete all keys matching pattern"""
        raise NotImplementedError

    async def clear(self) -> None:
        """Clear all cache entries"""
        raise NotImplementedError

    async def close(self) -> None:
        """Close cache connection"""


class InMemoryCacheBackend(CacheBackend):
    """In-memory LRU cache backend (fallback when Redis unavailable)"""

    def __init__(self, max_size_mb: int = 100):
        """
        Initialize in-memory cache

        Args:
            max_size_mb: Maximum cache size in MB
        """
        self.cache: Dict[str, tuple[str, float]] = {}  # key -> (value, expiry_time)
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.current_size = 0
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[str]:
        """Get value from cache if not expired"""
        async with self._lock:
            if key in self.cache:
                value, expiry = self.cache[key]
                if expiry > asyncio.get_event_loop().time():
                    return value
                else:
                    # Expired, remove
                    del self.cache[key]
                    self.current_size -= len(value)
            return None

    async def set(self, key: str, value: str, ttl: int) -> None:
        """Set value in cache with TTL"""
        async with self._lock:
            # Check if we need to evict
            value_size = len(value)
            while self.current_size + value_size > self.max_size_bytes and self.cache:
                # Evict oldest entry (simplified LRU)
                oldest_key = next(iter(self.cache))
                oldest_value, _ = self.cache[oldest_key]
                del self.cache[oldest_key]
                self.current_size -= len(oldest_value)

            # Add/update entry
            expiry_time = asyncio.get_event_loop().time() + ttl
            if key in self.cache:
                old_value, _ = self.cache[key]
                self.current_size -= len(old_value)

            self.cache[key] = (value, expiry_time)
            self.current_size += value_size

    async def delete(self, key: str) -> None:
        """Delete key from cache"""
        async with self._lock:
            if key in self.cache:
                value, _ = self.cache[key]
                del self.cache[key]
                self.current_size -= len(value)

    async def delete_pattern(self, pattern: str) -> None:
        """Delete all keys matching pattern (simple prefix match)"""
        async with self._lock:
            keys_to_delete = [k for k in self.cache.keys() if k.startswith(pattern.replace("*", ""))]
            for key in keys_to_delete:
                value, _ = self.cache[key]
                del self.cache[key]
                self.current_size -= len(value)

    async def clear(self) -> None:
        """Clear all cache entries"""
        async with self._lock:
            self.cache.clear()
            self.current_size = 0


class RedisCacheBackend(CacheBackend):
    """Redis cache backend"""

    def __init__(self, redis_url: str):
        """
        Initialize Redis cache

        Args:
            redis_url: Redis connection URL
        """
        self.redis_url = redis_url
        self.redis = None
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize Redis connection"""
        try:
            import redis.asyncio as aioredis

            redis_client = await aioredis.from_url(self.redis_url, encoding="utf-8", decode_responses=True)
            # Test connection
            await redis_client.ping()
            self.redis = redis_client
            self._initialized = True
            logger.info(f"Redis cache initialized: {self.redis_url}")
            return True
        except Exception as e:
            logger.warning(f"Failed to initialize Redis cache: {e}")
            self.redis = None
            self._initialized = False
            return False

    async def get(self, key: str) -> Optional[str]:
        """Get value from Redis"""
        if not self._initialized or not self.redis:
            return None

        try:
            return await self.redis.get(key)
        except Exception as e:
            logger.warning(f"Redis get error: {e}")
            return None

    async def set(self, key: str, value: str, ttl: int) -> None:
        """Set value in Redis with TTL"""
        if not self._initialized or not self.redis:
            return

        try:
            await self.redis.setex(key, ttl, value)
        except Exception as e:
            logger.warning(f"Redis set error: {e}")

    async def delete(self, key: str) -> None:
        """Delete key from Redis"""
        if not self._initialized or not self.redis:
            return

        try:
            await self.redis.delete(key)
        except Exception as e:
            logger.warning(f"Redis delete error: {e}")

    async def delete_pattern(self, pattern: str) -> None:
        """Delete all keys matching pattern"""
        if not self._initialized or not self.redis:
            return

        try:
            cursor = 0
            while True:
                cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)
                if keys:
                    await self.redis.delete(*keys)
                if cursor == 0:
                    break
        except Exception as e:
            logger.warning(f"Redis delete_pattern error: {e}")

    async def clear(self) -> None:
        """Clear all cache entries (dangerous in production!)"""
        if not self._initialized or not self.redis:
            return

        try:
            await self.redis.flushdb()
        except Exception as e:
            logger.warning(f"Redis clear error: {e}")

    async def close(self) -> None:
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()
            self._initialized = False


class GraphStoreCache:
    """
    Cache layer for graph store operations

    Provides transparent caching with automatic invalidation.
    Falls back to in-memory cache if Redis is unavailable.

    Example:
        ```python
        cache = GraphStoreCache(GraphStoreCacheConfig(
            redis_url="redis://localhost:6379/0"
        ))
        await cache.initialize()

        # Cache a query result
        result = await cache.get_or_set(
            "entity:person_1",
            lambda: store.get_entity("person_1"),
            ttl=300
        )

        # Invalidate cache
        await cache.invalidate_entity("person_1")
        ```
    """

    def __init__(self, config: GraphStoreCacheConfig):
        """
        Initialize cache

        Args:
            config: Cache configuration
        """
        self.config = config
        self.backend: Optional[CacheBackend] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize cache backend (Redis or in-memory fallback)"""
        if not self.config.enabled:
            logger.info("Graph store cache disabled")
            return

        # Try Redis first
        if self.config.redis_url:
            redis_backend = RedisCacheBackend(self.config.redis_url)
            if await redis_backend.initialize():
                self.backend = redis_backend
                self._initialized = True
                logger.info("Using Redis cache backend")
                return

        # Fallback to in-memory
        self.backend = InMemoryCacheBackend(self.config.max_cache_size_mb)
        self._initialized = True
        logger.info("Using in-memory cache backend (fallback)")

    async def close(self) -> None:
        """Close cache backend"""
        if self.backend:
            await self.backend.close()
        self._initialized = False

    def _make_key(self, operation: str, *args) -> str:
        """
        Create cache key from operation and arguments

        Args:
            operation: Operation name (e.g., "entity", "relation", "neighbors")
            *args: Operation arguments

        Returns:
            Cache key string
        """
        # Create deterministic key from args
        args_str = json.dumps(args, sort_keys=True)
        args_hash = hashlib.md5(args_str.encode()).hexdigest()[:8]
        return f"{self.config.key_prefix}{operation}:{args_hash}"

    async def get_or_set(self, key: str, fetch_func: Callable, ttl: Optional[int] = None) -> Any:
        """
        Get value from cache or fetch and cache it

        Args:
            key: Cache key
            fetch_func: Async function to fetch value if not cached
            ttl: TTL override (uses config.ttl if None)

        Returns:
            Cached or fetched value
        """
        if not self._initialized or not self.backend:
            return await fetch_func()

        # Try to get from cache
        cached = await self.backend.get(key)
        if cached is not None:
            try:
                return json.loads(cached)
            except json.JSONDecodeError:
                logger.warning(f"Failed to decode cached value for key: {key}")

        # Fetch and cache
        value = await fetch_func()
        if value is not None:
            try:
                cached_value = json.dumps(value)
                await self.backend.set(key, cached_value, ttl or self.config.ttl)
            except (TypeError, ValueError) as e:
                logger.warning(f"Failed to cache value for key {key}: {e}")

        return value

    async def invalidate_entity(self, entity_id: str) -> None:
        """
        Invalidate all cache entries related to an entity

        Args:
            entity_id: Entity ID to invalidate
        """
        if not self._initialized or not self.backend:
            return

        # Invalidate entity and related queries
        await self.backend.delete(f"{self.config.key_prefix}entity:{entity_id}")
        await self.backend.delete_pattern(f"{self.config.key_prefix}neighbors:{entity_id}:*")
        await self.backend.delete_pattern(f"{self.config.key_prefix}paths:*:{entity_id}:*")
        await self.backend.delete_pattern(f"{self.config.key_prefix}traverse:{entity_id}:*")

    async def invalidate_relation(self, relation_id: str) -> None:
        """
        Invalidate all cache entries related to a relation

        Args:
            relation_id: Relation ID to invalidate
        """
        if not self._initialized or not self.backend:
            return

        await self.backend.delete(f"{self.config.key_prefix}relation:{relation_id}")
        # Relations affect neighbors and paths, so invalidate broadly
        await self.backend.delete_pattern(f"{self.config.key_prefix}neighbors:*")
        await self.backend.delete_pattern(f"{self.config.key_prefix}paths:*")

    async def clear(self) -> None:
        """Clear all cache entries"""
        if self._initialized and self.backend:
            await self.backend.clear()


def cached_method(cache_key_func: Callable[..., str], ttl: Optional[int] = None):
    """
    Decorator for caching graph store methods

    Args:
        cache_key_func: Function to generate cache key from method args
        ttl: Cache TTL (uses cache config if None)

    Example:
        ```python
        @cached_method(lambda self, entity_id: f"entity:{entity_id}")
        async def get_entity(self, entity_id: str) -> Optional[Entity]:
            # Implementation
            pass
        ```
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Check if caching is available
            if not hasattr(self, "cache") or not self.cache or not self.cache._initialized:
                return await func(self, *args, **kwargs)

            # Generate cache key
            cache_key = cache_key_func(self, *args, **kwargs)

            # Try to get from cache or fetch
            return await self.cache.get_or_set(cache_key, lambda: func(self, *args, **kwargs), ttl=ttl)

        return wrapper

    return decorator
