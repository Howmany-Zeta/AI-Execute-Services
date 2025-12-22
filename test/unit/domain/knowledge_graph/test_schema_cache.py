"""
Unit tests for schema caching functionality
"""

import pytest
import time
from aiecs.infrastructure.graph_storage.schema_cache import LRUCache, CacheMetrics, CacheEntry


class TestCacheMetrics:
    """Test CacheMetrics"""
    
    def test_initial_metrics(self):
        """Test initial metrics are zero"""
        metrics = CacheMetrics()
        assert metrics.hits == 0
        assert metrics.misses == 0
        assert metrics.evictions == 0
        assert metrics.expirations == 0
        assert metrics.total_requests == 0
        assert metrics.hit_rate == 0.0
        assert metrics.miss_rate == 1.0
    
    def test_hit_rate_calculation(self):
        """Test hit rate calculation"""
        metrics = CacheMetrics()
        metrics.hits = 7
        metrics.misses = 3
        
        assert metrics.total_requests == 10
        assert metrics.hit_rate == 0.7
        assert metrics.miss_rate == 0.3
    
    def test_reset(self):
        """Test metrics reset"""
        metrics = CacheMetrics()
        metrics.hits = 10
        metrics.misses = 5
        metrics.evictions = 2
        metrics.expirations = 1
        
        metrics.reset()
        
        assert metrics.hits == 0
        assert metrics.misses == 0
        assert metrics.evictions == 0
        assert metrics.expirations == 0


class TestLRUCache:
    """Test LRUCache"""
    
    def test_initialization(self):
        """Test cache initialization"""
        cache = LRUCache(max_size=100, ttl_seconds=3600)
        
        assert cache.max_size == 100
        assert cache.ttl_seconds == 3600
        assert cache.size == 0
        assert cache.metrics.total_requests == 0
    
    def test_initialization_invalid_size(self):
        """Test initialization with invalid size"""
        with pytest.raises(ValueError, match="max_size must be positive"):
            LRUCache(max_size=0)
    
    def test_set_and_get(self):
        """Test basic set and get operations"""
        cache = LRUCache(max_size=10)
        
        cache.set("key1", "value1")
        assert cache.size == 1
        
        value = cache.get("key1")
        assert value == "value1"
        assert cache.metrics.hits == 1
        assert cache.metrics.misses == 0
    
    def test_get_nonexistent(self):
        """Test getting nonexistent key"""
        cache = LRUCache(max_size=10)
        
        value = cache.get("nonexistent")
        assert value is None
        assert cache.metrics.misses == 1
        assert cache.metrics.hits == 0
    
    def test_update_existing(self):
        """Test updating existing key"""
        cache = LRUCache(max_size=10)
        
        cache.set("key1", "value1")
        cache.set("key1", "value2")
        
        assert cache.size == 1
        assert cache.get("key1") == "value2"
    
    def test_lru_eviction(self):
        """Test LRU eviction when cache is full"""
        cache = LRUCache(max_size=3)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        assert cache.size == 3
        assert cache.metrics.evictions == 0
        
        # Add fourth item - should evict key1
        cache.set("key4", "value4")
        
        assert cache.size == 3
        assert cache.metrics.evictions == 1
        assert cache.get("key1") is None  # Evicted
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"
    
    def test_lru_order_on_access(self):
        """Test that accessing an item moves it to end (most recent)"""
        cache = LRUCache(max_size=3)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        # Access key1 to make it most recent
        cache.get("key1")
        
        # Add key4 - should evict key2 (oldest)
        cache.set("key4", "value4")
        
        assert cache.get("key1") == "value1"  # Still there
        assert cache.get("key2") is None  # Evicted
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"
    
    def test_delete(self):
        """Test deleting entries"""
        cache = LRUCache(max_size=10)
        
        cache.set("key1", "value1")
        assert cache.size == 1
        
        deleted = cache.delete("key1")
        assert deleted is True
        assert cache.size == 0
        assert cache.get("key1") is None
        
        # Delete nonexistent
        deleted = cache.delete("nonexistent")
        assert deleted is False
    
    def test_clear(self):
        """Test clearing cache"""
        cache = LRUCache(max_size=10)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        assert cache.size == 3
        
        cache.clear()

        assert cache.size == 0
        assert cache.get("key1") is None

    def test_ttl_expiration(self):
        """Test TTL-based expiration"""
        cache = LRUCache(max_size=10, ttl_seconds=1)  # 1 second TTL

        cache.set("key1", "value1")

        # Should be available immediately
        assert cache.get("key1") == "value1"
        assert cache.metrics.hits == 1

        # Wait for expiration
        time.sleep(1.1)

        # Should be expired
        value = cache.get("key1")
        assert value is None
        assert cache.metrics.expirations == 1
        assert cache.metrics.misses == 1

    def test_no_ttl(self):
        """Test cache with no TTL (never expires)"""
        cache = LRUCache(max_size=10, ttl_seconds=None)

        cache.set("key1", "value1")

        # Wait a bit
        time.sleep(0.5)

        # Should still be available
        assert cache.get("key1") == "value1"
        assert cache.metrics.expirations == 0

    def test_cleanup_expired(self):
        """Test manual cleanup of expired entries"""
        cache = LRUCache(max_size=10, ttl_seconds=1)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        assert cache.size == 3

        # Wait for expiration
        time.sleep(1.1)

        # Cleanup expired
        removed = cache.cleanup_expired()

        assert removed == 3
        assert cache.size == 0
        assert cache.metrics.expirations == 3

    def test_invalidate_pattern(self):
        """Test pattern-based invalidation"""
        cache = LRUCache(max_size=10)

        cache.set("user:1", "Alice")
        cache.set("user:2", "Bob")
        cache.set("product:1", "Widget")
        cache.set("product:2", "Gadget")

        assert cache.size == 4

        # Invalidate all user entries
        removed = cache.invalidate_pattern("user:")

        assert removed == 2
        assert cache.size == 2
        assert cache.get("user:1") is None
        assert cache.get("user:2") is None
        assert cache.get("product:1") == "Widget"
        assert cache.get("product:2") == "Gadget"

    def test_contains(self):
        """Test __contains__ operator"""
        cache = LRUCache(max_size=10)

        cache.set("key1", "value1")

        assert "key1" in cache
        assert "nonexistent" not in cache

    def test_contains_expired(self):
        """Test __contains__ with expired entry"""
        cache = LRUCache(max_size=10, ttl_seconds=1)

        cache.set("key1", "value1")
        assert "key1" in cache

        # Wait for expiration
        time.sleep(1.1)

        assert "key1" not in cache

    def test_len(self):
        """Test __len__ operator"""
        cache = LRUCache(max_size=10)

        assert len(cache) == 0

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        assert len(cache) == 2

    def test_get_stats(self):
        """Test getting cache statistics"""
        cache = LRUCache(max_size=10, ttl_seconds=3600)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.get("key1")  # Hit
        cache.get("key3")  # Miss

        stats = cache.get_stats()

        assert stats["size"] == 2
        assert stats["max_size"] == 10
        assert stats["ttl_seconds"] == 3600
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["total_requests"] == 2
        assert stats["hit_rate"] == 0.5
        assert stats["miss_rate"] == 0.5

    def test_reset_metrics(self):
        """Test resetting cache metrics"""
        cache = LRUCache(max_size=10)

        cache.set("key1", "value1")
        cache.get("key1")
        cache.get("key2")

        assert cache.metrics.hits == 1
        assert cache.metrics.misses == 1

        cache.reset_metrics()

        assert cache.metrics.hits == 0
        assert cache.metrics.misses == 0
        assert cache.size == 1  # Cache content unchanged

    def test_repr(self):
        """Test string representation"""
        cache = LRUCache(max_size=10)

        cache.set("key1", "value1")
        cache.get("key1")

        repr_str = repr(cache)
        assert "LRUCache" in repr_str
        assert "1/10" in repr_str  # size/max_size


class TestSchemaManagerCaching:
    """Test SchemaManager caching integration"""

    def test_schema_manager_with_cache_enabled(self):
        """Test SchemaManager with caching enabled"""
        from aiecs.domain.knowledge_graph.schema.schema_manager import SchemaManager
        from aiecs.domain.knowledge_graph.schema.entity_type import EntityType
        from aiecs.domain.knowledge_graph.schema.property_schema import PropertySchema, PropertyType

        manager = SchemaManager(cache_size=100, ttl_seconds=3600, enable_cache=True)

        # Create entity type
        person_type = EntityType(
            name="Person",
            description="A person",
            properties={
                "name": PropertySchema(name="name", property_type=PropertyType.STRING)
            }
        )
        manager.create_entity_type(person_type)

        # First get - should miss cache and load from schema
        result1 = manager.get_entity_type("Person")
        assert result1 is not None
        assert result1.name == "Person"

        # Second get - should hit cache
        result2 = manager.get_entity_type("Person")
        assert result2 is not None
        assert result2.name == "Person"

        # Check cache stats
        stats = manager.get_cache_stats()
        assert stats["enabled"] is True
        assert stats["entity_types"]["hits"] >= 1

    def test_schema_manager_with_cache_disabled(self):
        """Test SchemaManager with caching disabled"""
        from aiecs.domain.knowledge_graph.schema.schema_manager import SchemaManager
        from aiecs.domain.knowledge_graph.schema.entity_type import EntityType
        from aiecs.domain.knowledge_graph.schema.property_schema import PropertySchema, PropertyType

        manager = SchemaManager(enable_cache=False)

        # Create entity type
        person_type = EntityType(
            name="Person",
            description="A person",
            properties={
                "name": PropertySchema(name="name", property_type=PropertyType.STRING)
            }
        )
        manager.create_entity_type(person_type)

        # Get entity type
        result = manager.get_entity_type("Person")
        assert result is not None

        # Cache stats should show disabled
        stats = manager.get_cache_stats()
        assert stats["enabled"] is False

    def test_cache_invalidation_on_update(self):
        """Test cache invalidation when entity type is updated"""
        from aiecs.domain.knowledge_graph.schema.schema_manager import SchemaManager
        from aiecs.domain.knowledge_graph.schema.entity_type import EntityType
        from aiecs.domain.knowledge_graph.schema.property_schema import PropertySchema, PropertyType

        manager = SchemaManager(cache_size=100, enable_cache=True)

        # Create and cache entity type
        person_type = EntityType(
            name="Person",
            description="A person",
            properties={
                "name": PropertySchema(name="name", property_type=PropertyType.STRING)
            }
        )
        manager.create_entity_type(person_type)
        manager.get_entity_type("Person")  # Cache it

        # Update entity type
        updated_person = EntityType(
            name="Person",
            description="Updated description",
            properties={
                "name": PropertySchema(name="name", property_type=PropertyType.STRING),
                "age": PropertySchema(name="age", property_type=PropertyType.INTEGER)
            }
        )
        manager.update_entity_type(updated_person)

        # Get should return updated version (cache was invalidated)
        result = manager.get_entity_type("Person")
        assert result.description == "Updated description"
        assert "age" in result.properties

    def test_cache_invalidation_on_delete(self):
        """Test cache invalidation when entity type is deleted"""
        from aiecs.domain.knowledge_graph.schema.schema_manager import SchemaManager
        from aiecs.domain.knowledge_graph.schema.entity_type import EntityType
        from aiecs.domain.knowledge_graph.schema.property_schema import PropertySchema, PropertyType

        manager = SchemaManager(cache_size=100, enable_cache=True)

        # Create and cache entity type
        person_type = EntityType(
            name="Person",
            description="A person",
            properties={
                "name": PropertySchema(name="name", property_type=PropertyType.STRING)
            }
        )
        manager.create_entity_type(person_type)
        manager.get_entity_type("Person")  # Cache it

        # Delete entity type
        manager.delete_entity_type("Person")

        # Get should return None
        result = manager.get_entity_type("Person")
        assert result is None

    def test_manual_cache_invalidation(self):
        """Test manual cache invalidation"""
        from aiecs.domain.knowledge_graph.schema.schema_manager import SchemaManager
        from aiecs.domain.knowledge_graph.schema.entity_type import EntityType
        from aiecs.domain.knowledge_graph.schema.property_schema import PropertySchema, PropertyType

        manager = SchemaManager(cache_size=100, enable_cache=True)

        # Create entity types
        person_type = EntityType(
            name="Person",
            description="A person",
            properties={
                "name": PropertySchema(name="name", property_type=PropertyType.STRING)
            }
        )
        manager.create_entity_type(person_type)
        manager.get_entity_type("Person")  # Cache it

        # Invalidate specific type
        manager.invalidate_cache("Person")

        # Invalidate all
        manager.invalidate_cache()

        stats = manager.get_cache_stats()
        assert stats["entity_types"]["size"] == 0

    def test_cleanup_expired_cache(self):
        """Test cleanup of expired cache entries"""
        from aiecs.domain.knowledge_graph.schema.schema_manager import SchemaManager

        manager = SchemaManager(cache_size=100, ttl_seconds=1, enable_cache=True)

        # Cleanup should work even with no entries
        removed = manager.cleanup_expired_cache()
        assert removed["entity_types"] == 0

    def test_reset_cache_metrics(self):
        """Test resetting cache metrics"""
        from aiecs.domain.knowledge_graph.schema.schema_manager import SchemaManager
        from aiecs.domain.knowledge_graph.schema.entity_type import EntityType
        from aiecs.domain.knowledge_graph.schema.property_schema import PropertySchema, PropertyType

        manager = SchemaManager(cache_size=100, enable_cache=True)

        # Create and access entity type
        person_type = EntityType(
            name="Person",
            description="A person",
            properties={
                "name": PropertySchema(name="name", property_type=PropertyType.STRING)
            }
        )
        manager.create_entity_type(person_type)
        manager.get_entity_type("Person")

        # Reset metrics
        manager.reset_cache_metrics()

        stats = manager.get_cache_stats()
        assert stats["entity_types"]["hits"] == 0
        assert stats["entity_types"]["misses"] == 0

