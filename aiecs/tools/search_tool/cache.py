"""
Intelligent Caching with Redis

This module implements intelligent caching with intent-aware TTL strategies
using Redis as the backend.
"""

import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .constants import QueryIntentType

logger = logging.getLogger(__name__)


class IntelligentCache:
    """Redis-based intelligent cache with intent-aware TTL"""

    # TTL strategies by intent type (in seconds)
    TTL_STRATEGIES = {
        # 30 days (rarely changes)
        QueryIntentType.DEFINITION.value: 86400 * 30,
        QueryIntentType.HOW_TO.value: 86400 * 7,  # 7 days
        QueryIntentType.FACTUAL.value: 86400 * 7,  # 7 days
        # 30 days (papers don't change)
        QueryIntentType.ACADEMIC.value: 86400 * 30,
        # 1 hour (fast-changing)
        QueryIntentType.RECENT_NEWS.value: 3600,
        QueryIntentType.PRODUCT.value: 86400,  # 1 day
        QueryIntentType.COMPARISON.value: 86400 * 3,  # 3 days
        QueryIntentType.GENERAL.value: 3600,  # 1 hour default
    }

    def __init__(self, redis_client: Optional[Any] = None, enabled: bool = True):
        """
        Initialize intelligent cache.

        Args:
            redis_client: Redis client instance (optional)
            enabled: Whether caching is enabled
        """
        self.redis_client = redis_client
        self.enabled = enabled and redis_client is not None
        self.cache_prefix = "search_tool:"

        if not self.enabled:
            logger.info("Intelligent cache is disabled (no Redis client)")

    async def get(self, query: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Get cached search results.

        Args:
            query: Search query
            params: Search parameters

        Returns:
            Cached results dictionary or None if not found
        """
        if not self.enabled:
            return None

        try:
            if self.redis_client is None:
                return None
            cache_key = self._generate_cache_key(query, params)
            redis = await self.redis_client.get_client()
            cached_data = await redis.get(cache_key)

            if cached_data:
                logger.debug(f"Cache hit for query: {query}")
                return json.loads(cached_data)

            logger.debug(f"Cache miss for query: {query}")
            return None

        except Exception as e:
            logger.warning(f"Cache get error: {e}")
            return None

    async def set(
        self,
        query: str,
        params: Dict[str, Any],
        results: List[Dict[str, Any]],
        intent_type: str = QueryIntentType.GENERAL.value,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Cache search results with intelligent TTL.

        Args:
            query: Search query
            params: Search parameters
            results: Search results to cache
            intent_type: Query intent type for TTL calculation
            metadata: Optional metadata about the search
        """
        if not self.enabled:
            return

        try:
            cache_key = self._generate_cache_key(query, params)

            # Calculate intelligent TTL
            ttl = self.calculate_ttl(query, intent_type, results)

            # Prepare cache data
            cache_data = {
                "query": query,
                "params": params,
                "results": results,
                "intent_type": intent_type,
                "metadata": metadata or {},
                "cached_at": datetime.utcnow().isoformat(),
                "ttl": ttl,
            }

            # Store in Redis
            if self.redis_client is None:
                return
            redis = await self.redis_client.get_client()
            await redis.set(cache_key, json.dumps(cache_data), ex=ttl)

            logger.debug(f"Cached results for query: {query} (TTL: {ttl}s)")

        except Exception as e:
            logger.warning(f"Cache set error: {e}")

    def calculate_ttl(self, query: str, intent_type: str, results: List[Dict[str, Any]]) -> int:
        """
        Calculate intelligent TTL based on intent and result quality.

        Args:
            query: Search query
            intent_type: Query intent type
            results: Search results

        Returns:
            TTL in seconds
        """
        # Base TTL from intent type
        base_ttl = self.TTL_STRATEGIES.get(intent_type, self.TTL_STRATEGIES[QueryIntentType.GENERAL.value])

        if not results:
            # No results: shorter cache time
            return base_ttl // 2

        # Adjust based on result freshness
        try:
            avg_freshness = sum(r.get("_quality", {}).get("freshness_score", 0.5) for r in results) / len(results)

            # Very fresh results can be cached longer
            if avg_freshness > 0.9:
                base_ttl = int(base_ttl * 2)
            # Old results should have shorter cache
            elif avg_freshness < 0.3:
                base_ttl = base_ttl // 2
        except Exception:
            pass

        # Adjust based on result quality
        try:
            avg_quality = sum(r.get("_quality", {}).get("quality_score", 0.5) for r in results) / len(results)

            # High quality results can be cached longer
            if avg_quality > 0.8:
                base_ttl = int(base_ttl * 1.5)
        except Exception:
            pass

        return base_ttl

    async def invalidate(self, query: str, params: Dict[str, Any]):
        """
        Invalidate cached results.

        Args:
            query: Search query
            params: Search parameters
        """
        if not self.enabled:
            return

        try:
            if self.redis_client is None:
                return
            cache_key = self._generate_cache_key(query, params)
            redis = await self.redis_client.get_client()
            await redis.delete(cache_key)
            logger.debug(f"Invalidated cache for query: {query}")
        except Exception as e:
            logger.warning(f"Cache invalidate error: {e}")

    async def clear_all(self):
        """Clear all cached search results"""
        if not self.enabled:
            return

        try:
            if self.redis_client is None:
                return
            redis = await self.redis_client.get_client()
            # Find all search_tool cache keys
            pattern = f"{self.cache_prefix}*"
            keys = []
            async for key in redis.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                await redis.delete(*keys)
                logger.info(f"Cleared {len(keys)} cached entries")
        except Exception as e:
            logger.warning(f"Cache clear error: {e}")

    def _generate_cache_key(self, query: str, params: Dict[str, Any]) -> str:
        """
        Generate unique cache key from query and parameters.

        Args:
            query: Search query
            params: Search parameters

        Returns:
            Cache key string
        """
        # Create deterministic string from query and params
        param_str = json.dumps(params, sort_keys=True)
        key_data = f"{query}:{param_str}"
        key_hash = hashlib.sha256(key_data.encode()).hexdigest()[:16]

        return f"{self.cache_prefix}{key_hash}"

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Cache statistics dictionary
        """
        if not self.enabled:
            return {"enabled": False, "total_keys": 0}

        try:
            if self.redis_client is None:
                return {"enabled": False, "total_keys": 0}
            redis = await self.redis_client.get_client()
            # Count cache keys
            pattern = f"{self.cache_prefix}*"
            key_count = 0
            async for _ in redis.scan_iter(match=pattern):
                key_count += 1

            return {
                "enabled": True,
                "total_keys": key_count,
                "prefix": self.cache_prefix,
            }
        except Exception as e:
            logger.warning(f"Cache stats error: {e}")
            return {"enabled": True, "error": str(e)}
