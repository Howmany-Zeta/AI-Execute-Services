"""
Schema Cache

LRU cache with TTL support for schema lookups.
"""

import time
from typing import Optional, Dict, Any, Generic, TypeVar
from collections import OrderedDict
from dataclasses import dataclass, field
from threading import Lock

T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    """
    Cache entry with value and metadata

    Attributes:
        value: Cached value
        timestamp: When the entry was created/updated
        access_count: Number of times accessed
    """

    value: T
    timestamp: float = field(default_factory=time.time)
    access_count: int = 0


@dataclass
class CacheMetrics:
    """
    Cache performance metrics

    Attributes:
        hits: Number of cache hits
        misses: Number of cache misses
        evictions: Number of entries evicted
        expirations: Number of entries expired
        total_requests: Total number of cache requests
    """

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    expirations: int = 0

    @property
    def total_requests(self) -> int:
        """Total number of cache requests"""
        return self.hits + self.misses

    @property
    def hit_rate(self) -> float:
        """Cache hit rate (0.0-1.0)"""
        if self.total_requests == 0:
            return 0.0
        return self.hits / self.total_requests

    @property
    def miss_rate(self) -> float:
        """Cache miss rate (0.0-1.0)"""
        return 1.0 - self.hit_rate

    def reset(self) -> None:
        """Reset all metrics to zero"""
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.expirations = 0


class LRUCache(Generic[T]):
    """
    LRU (Least Recently Used) Cache with TTL support

    Thread-safe cache implementation with:
    - LRU eviction policy
    - TTL (time-to-live) expiration
    - Performance metrics tracking

    Example:
        ```python
        cache = LRUCache(max_size=100, ttl_seconds=3600)

        # Set value
        cache.set("key1", value)

        # Get value
        value = cache.get("key1")  # Returns value or None

        # Check metrics
        print(f"Hit rate: {cache.metrics.hit_rate:.2%}")
        ```
    """

    def __init__(self, max_size: int = 1000, ttl_seconds: Optional[int] = 3600):
        """
        Initialize LRU cache

        Args:
            max_size: Maximum number of entries (default: 1000)
            ttl_seconds: Time-to-live in seconds (default: 3600, None = no expiration)
        """
        if max_size <= 0:
            raise ValueError("max_size must be positive")

        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, CacheEntry[T]] = OrderedDict()
        self._lock = Lock()
        self.metrics = CacheMetrics()

    def get(self, key: str) -> Optional[T]:
        """
        Get value from cache

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self.metrics.misses += 1
                return None

            # Check TTL expiration
            if self._is_expired(entry):
                del self._cache[key]
                self.metrics.expirations += 1
                self.metrics.misses += 1
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            entry.access_count += 1
            self.metrics.hits += 1

            return entry.value

    def set(self, key: str, value: T) -> None:
        """
        Set value in cache

        Args:
            key: Cache key
            value: Value to cache
        """
        with self._lock:
            # Update existing entry
            if key in self._cache:
                self._cache[key] = CacheEntry(value=value)
                self._cache.move_to_end(key)
                return

            # Add new entry
            self._cache[key] = CacheEntry(value=value)

            # Evict oldest entry if cache is full
            if len(self._cache) > self.max_size:
                self._cache.popitem(last=False)  # Remove oldest (first) item
                self.metrics.evictions += 1

    def delete(self, key: str) -> bool:
        """
        Delete entry from cache

        Args:
            key: Cache key

        Returns:
            True if entry was deleted, False if not found
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """Clear all entries from cache"""
        with self._lock:
            self._cache.clear()

    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all keys matching a pattern

        Args:
            pattern: Pattern to match (simple prefix matching)

        Returns:
            Number of entries invalidated
        """
        with self._lock:
            keys_to_delete = [key for key in self._cache.keys() if key.startswith(pattern)]

            for key in keys_to_delete:
                del self._cache[key]

            return len(keys_to_delete)

    def _is_expired(self, entry: CacheEntry[T]) -> bool:
        """
        Check if cache entry is expired

        Args:
            entry: Cache entry to check

        Returns:
            True if expired, False otherwise
        """
        if self.ttl_seconds is None:
            return False

        age = time.time() - entry.timestamp
        return age > self.ttl_seconds

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries

        Returns:
            Number of entries removed
        """
        with self._lock:
            if self.ttl_seconds is None:
                return 0

            keys_to_delete = [key for key, entry in self._cache.items() if self._is_expired(entry)]

            for key in keys_to_delete:
                del self._cache[key]

            self.metrics.expirations += len(keys_to_delete)
            return len(keys_to_delete)

    @property
    def size(self) -> int:
        """Current number of entries in cache"""
        with self._lock:
            return len(self._cache)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics

        Returns:
            Dictionary with cache statistics
        """
        with self._lock:
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "ttl_seconds": self.ttl_seconds,
                "hits": self.metrics.hits,
                "misses": self.metrics.misses,
                "evictions": self.metrics.evictions,
                "expirations": self.metrics.expirations,
                "total_requests": self.metrics.total_requests,
                "hit_rate": self.metrics.hit_rate,
                "miss_rate": self.metrics.miss_rate,
            }

    def reset_metrics(self) -> None:
        """Reset cache metrics"""
        with self._lock:
            self.metrics.reset()

    def __len__(self) -> int:
        """Return number of entries in cache"""
        return self.size

    def __contains__(self, key: str) -> bool:
        """Check if key exists in cache (without affecting LRU order)"""
        with self._lock:
            if key not in self._cache:
                return False

            entry = self._cache[key]
            return not self._is_expired(entry)

    def __repr__(self) -> str:
        return f"LRUCache(size={self.size}/{self.max_size}, hit_rate={self.metrics.hit_rate:.2%})"
