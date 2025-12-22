"""
Unit tests for graph storage cache module

Tests use real components (InMemoryCacheBackend) when possible.
Only use mocks if pytest-cov limitations cause issues.
"""

import pytest
import asyncio
import json

from aiecs.infrastructure.graph_storage.cache import (
    GraphStoreCacheConfig,
    CacheBackend,
    InMemoryCacheBackend,
    RedisCacheBackend,
    GraphStoreCache,
    cached_method
)


class TestGraphStoreCacheConfig:
    """Test GraphStoreCacheConfig"""
    
    def test_config_defaults(self):
        """Test cache config with defaults"""
        config = GraphStoreCacheConfig()
        
        assert config.enabled is True
        assert config.ttl == 300
        assert config.max_cache_size_mb == 100
        assert config.redis_url is None
        assert config.key_prefix == "graph:"
    
    def test_config_custom(self):
        """Test cache config with custom values"""
        config = GraphStoreCacheConfig(
            enabled=False,
            ttl=600,
            max_cache_size_mb=200,
            redis_url="redis://localhost:6379/0",
            key_prefix="test:"
        )
        
        assert config.enabled is False
        assert config.ttl == 600
        assert config.max_cache_size_mb == 200
        assert config.redis_url == "redis://localhost:6379/0"
        assert config.key_prefix == "test:"


class TestInMemoryCacheBackend:
    """Test InMemoryCacheBackend"""
    
    @pytest.fixture
    def backend(self):
        """Create InMemoryCacheBackend instance"""
        return InMemoryCacheBackend(max_size_mb=1)  # Small size for testing
    
    @pytest.mark.asyncio
    async def test_get_missing_key(self, backend):
        """Test getting non-existent key"""
        value = await backend.get("nonexistent")
        
        assert value is None
    
    @pytest.mark.asyncio
    async def test_set_and_get(self, backend):
        """Test setting and getting value"""
        await backend.set("key1", "value1", ttl=60)
        value = await backend.get("key1")
        
        assert value == "value1"
    
    @pytest.mark.asyncio
    async def test_set_overwrite(self, backend):
        """Test overwriting existing key"""
        await backend.set("key1", "value1", ttl=60)
        await backend.set("key1", "value2", ttl=60)
        value = await backend.get("key1")
        
        assert value == "value2"
    
    @pytest.mark.asyncio
    async def test_delete(self, backend):
        """Test deleting key"""
        await backend.set("key1", "value1", ttl=60)
        await backend.delete("key1")
        value = await backend.get("key1")
        
        assert value is None
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, backend):
        """Test deleting non-existent key"""
        # Should not raise error
        await backend.delete("nonexistent")
    
    @pytest.mark.asyncio
    async def test_ttl_expiration(self, backend):
        """Test TTL expiration"""
        await backend.set("key1", "value1", ttl=0.1)  # Very short TTL
        
        # Should be available immediately
        value = await backend.get("key1")
        assert value == "value1"
        
        # Wait for expiration
        await asyncio.sleep(0.15)
        value = await backend.get("key1")
        assert value is None
    
    @pytest.mark.asyncio
    async def test_delete_pattern(self, backend):
        """Test deleting keys by pattern"""
        await backend.set("prefix:key1", "value1", ttl=60)
        await backend.set("prefix:key2", "value2", ttl=60)
        await backend.set("other:key1", "value3", ttl=60)
        
        await backend.delete_pattern("prefix:")
        
        assert await backend.get("prefix:key1") is None
        assert await backend.get("prefix:key2") is None
        assert await backend.get("other:key1") == "value3"
    
    @pytest.mark.asyncio
    async def test_clear(self, backend):
        """Test clearing all cache"""
        await backend.set("key1", "value1", ttl=60)
        await backend.set("key2", "value2", ttl=60)
        
        await backend.clear()
        
        assert await backend.get("key1") is None
        assert await backend.get("key2") is None
    
    @pytest.mark.asyncio
    async def test_size_eviction(self, backend):
        """Test LRU eviction when cache is full"""
        # Fill cache beyond max size
        large_value = "x" * (512 * 1024)  # 512KB
        await backend.set("key1", large_value, ttl=60)
        await backend.set("key2", large_value, ttl=60)
        
        # Should evict oldest entries
        # Note: Exact behavior depends on implementation
        assert backend.current_size <= backend.max_size_bytes


class TestGraphStoreCache:
    """Test GraphStoreCache"""
    
    @pytest.fixture
    def config(self):
        """Create cache config"""
        return GraphStoreCacheConfig(enabled=True, redis_url=None)  # Use in-memory
    
    @pytest.fixture
    async def cache(self, config):
        """Create and initialize cache"""
        cache = GraphStoreCache(config)
        await cache.initialize()
        yield cache
        await cache.close()
    
    @pytest.mark.asyncio
    async def test_initialize_in_memory(self, config):
        """Test initializing with in-memory backend"""
        cache = GraphStoreCache(config)
        await cache.initialize()
        
        assert cache._initialized is True
        assert isinstance(cache.backend, InMemoryCacheBackend)
        await cache.close()
    
    @pytest.mark.asyncio
    async def test_initialize_disabled(self):
        """Test initializing with cache disabled"""
        config = GraphStoreCacheConfig(enabled=False)
        cache = GraphStoreCache(config)
        await cache.initialize()
        
        assert cache._initialized is False
        assert cache.backend is None
    
    @pytest.mark.asyncio
    async def test_get_or_set_miss(self, cache):
        """Test get_or_set on cache miss"""
        call_count = 0
        
        async def fetch_func():
            nonlocal call_count
            call_count += 1
            return {"data": "value"}
        
        result = await cache.get_or_set("test_key", fetch_func)
        
        assert result == {"data": "value"}
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_get_or_set_hit(self, cache):
        """Test get_or_set on cache hit"""
        call_count = 0
        
        async def fetch_func():
            nonlocal call_count
            call_count += 1
            return {"data": "value"}
        
        # First call - miss
        result1 = await cache.get_or_set("test_key", fetch_func)
        assert call_count == 1
        
        # Second call - hit
        result2 = await cache.get_or_set("test_key", fetch_func)
        assert call_count == 1  # Should not call again
        assert result1 == result2
    
    @pytest.mark.asyncio
    async def test_get_or_set_custom_ttl(self, cache):
        """Test get_or_set with custom TTL"""
        async def fetch_func():
            return {"data": "value"}
        
        await cache.get_or_set("test_key", fetch_func, ttl=600)
        
        # Should be cached
        result = await cache.get_or_set("test_key", fetch_func)
        assert result == {"data": "value"}
    
    @pytest.mark.asyncio
    async def test_get_or_set_none_value(self, cache):
        """Test get_or_set with None value"""
        async def fetch_func():
            return None
        
        result = await cache.get_or_set("test_key", fetch_func)
        
        assert result is None
        # None values should not be cached
    
    @pytest.mark.asyncio
    async def test_invalidate_entity(self, cache):
        """Test invalidating entity cache"""
        async def fetch_func():
            return {"entity": "data"}
        
        # Cache entity
        await cache.get_or_set("graph:entity:e1", fetch_func)
        
        # Invalidate
        await cache.invalidate_entity("e1")
        
        # Should be removed
        call_count = 0
        async def fetch_func2():
            nonlocal call_count
            call_count += 1
            return {"entity": "data"}
        
        result = await cache.get_or_set("graph:entity:e1", fetch_func2)
        assert call_count == 1  # Should fetch again
    
    @pytest.mark.asyncio
    async def test_invalidate_relation(self, cache):
        """Test invalidating relation cache"""
        async def fetch_func():
            return {"relation": "data"}
        
        # Cache relation
        await cache.get_or_set("graph:relation:r1", fetch_func)
        
        # Invalidate
        await cache.invalidate_relation("r1")
        
        # Should be removed
        call_count = 0
        async def fetch_func2():
            nonlocal call_count
            call_count += 1
            return {"relation": "data"}
        
        result = await cache.get_or_set("graph:relation:r1", fetch_func2)
        assert call_count == 1  # Should fetch again
    
    @pytest.mark.asyncio
    async def test_clear(self, cache):
        """Test clearing all cache"""
        async def fetch_func():
            return {"data": "value"}
        
        # Cache multiple keys
        await cache.get_or_set("key1", fetch_func)
        await cache.get_or_set("key2", fetch_func)
        
        # Clear
        await cache.clear()
        
        # Both should be gone
        call_count = 0
        async def fetch_func2():
            nonlocal call_count
            call_count += 1
            return {"data": "value"}
        
        await cache.get_or_set("key1", fetch_func2)
        await cache.get_or_set("key2", fetch_func2)
        
        assert call_count == 2  # Both should fetch again
    
    @pytest.mark.asyncio
    async def test_make_key(self, cache):
        """Test cache key generation"""
        key = cache._make_key("entity", "e1")
        
        assert key.startswith("graph:")
        assert "entity" in key
    
    @pytest.mark.asyncio
    async def test_make_key_with_args(self, cache):
        """Test cache key generation with multiple args"""
        key1 = cache._make_key("neighbors", "e1", "outgoing")
        key2 = cache._make_key("neighbors", "e1", "outgoing")
        key3 = cache._make_key("neighbors", "e1", "incoming")
        
        assert key1 == key2  # Same args should produce same key
        assert key1 != key3  # Different args should produce different key


class TestCachedMethodDecorator:
    """Test cached_method decorator"""
    
    @pytest.mark.asyncio
    async def test_cached_method_without_cache(self):
        """Test cached_method when cache is not available"""
        call_count = 0
        
        class TestStore:
            @cached_method(lambda self, entity_id: f"entity:{entity_id}")
            async def get_entity(self, entity_id: str):
                nonlocal call_count
                call_count += 1
                return {"id": entity_id}
        
        store = TestStore()
        result = await store.get_entity("e1")
        
        assert result == {"id": "e1"}
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_cached_method_with_cache(self):
        """Test cached_method with cache available"""
        from aiecs.infrastructure.graph_storage.cache import GraphStoreCache, GraphStoreCacheConfig
        
        call_count = 0
        
        class TestStore:
            def __init__(self):
                cache_config = GraphStoreCacheConfig(enabled=True, redis_url=None)
                self.cache = GraphStoreCache(cache_config)
            
            @cached_method(lambda self, entity_id: f"entity:{entity_id}")
            async def get_entity(self, entity_id: str):
                nonlocal call_count
                call_count += 1
                return {"id": entity_id}
        
        store = TestStore()
        await store.cache.initialize()
        
        # First call
        result1 = await store.get_entity("e1")
        assert call_count == 1
        
        # Second call - should use cache
        result2 = await store.get_entity("e1")
        assert call_count == 1  # Should not call again
        assert result1 == result2
        
        await store.cache.close()

