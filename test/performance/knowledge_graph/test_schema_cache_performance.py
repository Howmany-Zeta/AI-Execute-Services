"""
Performance benchmarks for schema caching
"""

import pytest
import time
from aiecs.domain.knowledge_graph.schema.schema_manager import SchemaManager
from aiecs.domain.knowledge_graph.schema.entity_type import EntityType
from aiecs.domain.knowledge_graph.schema.relation_type import RelationType
from aiecs.domain.knowledge_graph.schema.property_schema import PropertySchema, PropertyType


@pytest.fixture
def populated_schema_manager():
    """Create a schema manager with many entity and relation types"""
    manager = SchemaManager(cache_size=1000, ttl_seconds=3600, enable_cache=True)
    
    # Create 50 entity types
    for i in range(50):
        entity_type = EntityType(
            name=f"EntityType{i}",
            description=f"Entity type {i}",
            properties={
                "id": PropertySchema(name="id", property_type=PropertyType.STRING),
                "name": PropertySchema(name="name", property_type=PropertyType.STRING),
                f"field{i}": PropertySchema(name=f"field{i}", property_type=PropertyType.STRING)
            }
        )
        manager.create_entity_type(entity_type)
    
    # Create 50 relation types
    for i in range(50):
        relation_type = RelationType(
            name=f"RelationType{i}",
            description=f"Relation type {i}",
            properties={
                "weight": PropertySchema(name="weight", property_type=PropertyType.FLOAT)
            }
        )
        manager.create_relation_type(relation_type)
    
    return manager


class TestSchemaCachePerformance:
    """Performance benchmarks for schema caching"""
    
    def test_cache_hit_rate_with_repeated_access(self, populated_schema_manager):
        """Test cache hit rate with repeated access to same types"""
        manager = populated_schema_manager
        
        # Reset metrics
        manager.reset_cache_metrics()
        
        # Access same 10 entity types repeatedly (100 times each)
        for _ in range(100):
            for i in range(10):
                manager.get_entity_type(f"EntityType{i}")
        
        # Check cache stats
        stats = manager.get_cache_stats()
        entity_stats = stats["entity_types"]
        
        print(f"\n=== Cache Performance (Repeated Access) ===")
        print(f"Total requests: {entity_stats['total_requests']}")
        print(f"Cache hits: {entity_stats['hits']}")
        print(f"Cache misses: {entity_stats['misses']}")
        print(f"Hit rate: {entity_stats['hit_rate']:.2%}")
        print(f"Cache size: {entity_stats['size']}/{entity_stats['max_size']}")
        
        # With caching, hit rate should be very high (>99%)
        # First access of each type is a miss, subsequent 99 are hits
        # Expected: 10 misses, 990 hits = 99% hit rate
        assert entity_stats['hit_rate'] > 0.95, f"Hit rate too low: {entity_stats['hit_rate']:.2%}"
        assert entity_stats['hits'] >= 900
        assert entity_stats['misses'] <= 100
    
    def test_cache_performance_vs_no_cache(self, populated_schema_manager):
        """Compare performance with and without caching"""
        # Test with cache
        manager_cached = populated_schema_manager
        manager_cached.reset_cache_metrics()
        
        start_time = time.time()
        for _ in range(1000):
            for i in range(10):
                manager_cached.get_entity_type(f"EntityType{i}")
        cached_duration = time.time() - start_time
        
        # Test without cache
        manager_no_cache = SchemaManager(enable_cache=False)
        for i in range(50):
            entity_type = EntityType(
                name=f"EntityType{i}",
                description=f"Entity type {i}",
                properties={
                    "id": PropertySchema(name="id", property_type=PropertyType.STRING),
                    "name": PropertySchema(name="name", property_type=PropertyType.STRING),
                }
            )
            manager_no_cache.create_entity_type(entity_type)
        
        start_time = time.time()
        for _ in range(1000):
            for i in range(10):
                manager_no_cache.get_entity_type(f"EntityType{i}")
        no_cache_duration = time.time() - start_time
        
        speedup = no_cache_duration / cached_duration if cached_duration > 0 else 0
        
        print(f"\n=== Performance Comparison ===")
        print(f"With cache: {cached_duration:.4f}s")
        print(f"Without cache: {no_cache_duration:.4f}s")
        print(f"Speedup: {speedup:.2f}x")
        
        # Cache should provide significant speedup
        # Note: Speedup may vary, but should be noticeable
        assert cached_duration < no_cache_duration, "Cache should be faster"
    
    def test_cache_hit_rate_with_random_access(self, populated_schema_manager):
        """Test cache hit rate with random access pattern"""
        import random
        
        manager = populated_schema_manager
        manager.reset_cache_metrics()
        
        # Random access to entity types
        random.seed(42)
        for _ in range(1000):
            type_index = random.randint(0, 49)
            manager.get_entity_type(f"EntityType{type_index}")
        
        stats = manager.get_cache_stats()
        entity_stats = stats["entity_types"]
        
        print(f"\n=== Cache Performance (Random Access) ===")
        print(f"Total requests: {entity_stats['total_requests']}")
        print(f"Cache hits: {entity_stats['hits']}")
        print(f"Cache misses: {entity_stats['misses']}")
        print(f"Hit rate: {entity_stats['hit_rate']:.2%}")
        
        # With random access, hit rate should still be good (>70%)
        # because we're accessing from a limited set (50 types)
        assert entity_stats['hit_rate'] > 0.70, f"Hit rate too low: {entity_stats['hit_rate']:.2%}"
    
    def test_cache_eviction_behavior(self):
        """Test cache eviction with small cache size"""
        # Create manager with small cache
        manager = SchemaManager(cache_size=10, enable_cache=True)
        
        # Create 50 entity types
        for i in range(50):
            entity_type = EntityType(
                name=f"EntityType{i}",
                description=f"Entity type {i}",
                properties={
                    "id": PropertySchema(name="id", property_type=PropertyType.STRING)
                }
            )
            manager.create_entity_type(entity_type)
        
        # Access all 50 types
        for i in range(50):
            manager.get_entity_type(f"EntityType{i}")
        
        stats = manager.get_cache_stats()
        entity_stats = stats["entity_types"]
        
        print(f"\n=== Cache Eviction Test ===")
        print(f"Cache size: {entity_stats['size']}/{entity_stats['max_size']}")
        print(f"Evictions: {entity_stats['evictions']}")
        
        # Cache should be full
        assert entity_stats['size'] == 10
        # Should have evicted 40 entries (50 - 10)
        assert entity_stats['evictions'] >= 40

