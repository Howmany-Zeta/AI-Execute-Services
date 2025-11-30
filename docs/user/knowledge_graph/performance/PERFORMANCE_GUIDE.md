# Graph Storage Performance Guide

Complete guide to optimizing graph storage performance in AIECS Knowledge Graph.

---

## Quick Start

### Enable All Optimizations

```python
from aiecs.infrastructure.graph_storage import PostgresGraphStore
from aiecs.infrastructure.graph_storage.cache import GraphStoreCache, GraphStoreCacheConfig
from aiecs.infrastructure.graph_storage.batch_operations import BatchOperationsMixin
from aiecs.infrastructure.graph_storage.performance_monitoring import PerformanceMonitor

class OptimizedGraphStore(PostgresGraphStore, BatchOperationsMixin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Enable caching
        self.cache = GraphStoreCache(GraphStoreCacheConfig(
            redis_url="redis://localhost:6379/0",
            ttl=300
        ))
        
        # Enable monitoring
        self.monitor = PerformanceMonitor(
            slow_query_threshold_ms=100.0
        )
    
    async def initialize(self):
        await super().initialize()
        await self.cache.initialize()
        await self.monitor.initialize()
    
    async def close(self):
        await self.cache.close()
        await super().close()

# Usage
store = OptimizedGraphStore()
await store.initialize()

# Benefit from all optimizations
await store.batch_add_entities(entities)  # Batch operations
entity = await store.get_entity("id")  # Cached
```

---

## 1. Caching

### Redis Configuration

```python
from aiecs.infrastructure.graph_storage.cache import GraphStoreCacheConfig

# Production configuration
config = GraphStoreCacheConfig(
    enabled=True,
    ttl=300,  # 5 minutes
    max_cache_size_mb=1000,  # In-memory fallback size
    redis_url="redis://localhost:6379/0",
    key_prefix="graph:"
)
```

### Usage Patterns

**Basic Caching**:
```python
cache = GraphStoreCache(config)
await cache.initialize()

# Cache a query result
result = await cache.get_or_set(
    "entity:person_1",
    lambda: store.get_entity("person_1"),
    ttl=300
)
```

**Cache Invalidation**:
```python
# Invalidate entity cache
await cache.invalidate_entity("person_1")

# Invalidate relation cache
await cache.invalidate_relation("rel_1")

# Clear all cache
await cache.clear()
```

**Decorator Pattern**:
```python
from aiecs.infrastructure.graph_storage.cache import cached_method

class MyStore(GraphStore):
    @cached_method(lambda self, entity_id: f"entity:{entity_id}", ttl=300)
    async def get_entity(self, entity_id: str):
        # Your implementation
        pass
```

### Performance Impact

- Cache hit: ~0.1ms (vs ~10-100ms database query)
- Recommended for: Frequently accessed entities, hot paths
- Not recommended for: Rapidly changing data, write-heavy workloads

---

## 2. Batch Operations

### Bulk Insertion

**Entities**:
```python
# Generate test data
entities = [
    Entity(id=f"e{i}", entity_type="Person", properties={"name": f"Person {i}"})
    for i in range(10000)
]

# Batch insert (100x faster than individual inserts)
count = await store.batch_add_entities(
    entities,
    batch_size=1000,
    use_copy=True  # Use PostgreSQL COPY for max performance
)
print(f"Inserted {count} entities")
```

**Relations**:
```python
# Generate test relations
relations = [
    Relation(id=f"r{i}", source_id=f"e{i}", target_id=f"e{i+1}", 
             relation_type="KNOWS", properties={})
    for i in range(9999)
]

# Batch insert
count = await store.batch_add_relations(relations, batch_size=1000)
```

### Bulk Deletion

```python
# Delete multiple entities
entity_ids = [f"e{i}" for i in range(10000)]
count = await store.batch_delete_entities(entity_ids, batch_size=1000)

# Delete multiple relations
relation_ids = [f"r{i}" for i in range(10000)]
count = await store.batch_delete_relations(relation_ids, batch_size=1000)
```

### Optimal Batch Size

```python
from aiecs.infrastructure.graph_storage.batch_operations import estimate_batch_size

# For entities averaging 1KB each, target 10MB batches
batch_size = estimate_batch_size(avg_item_size_bytes=1024, target_batch_size_mb=10)
# Returns ~10,000
```

### Performance Impact

- COPY method: ~100x faster than individual inserts
- Multi-row INSERT: ~10-20x faster
- Example: 10,000 entities in 300ms vs 30s

---

## 3. Index Optimization

### Analyze Indexes

```python
from aiecs.infrastructure.graph_storage.index_optimization import IndexOptimizer

optimizer = IndexOptimizer(store.pool)

# Get all indexes
indexes = await optimizer.analyze_indexes()
for idx in indexes:
    print(f"{idx.index_name}: {idx.usage_count} uses, {idx.size_mb}MB")

# Find unused indexes
unused = await optimizer.get_unused_indexes(min_usage_threshold=10)
print(f"Found {len(unused)} unused indexes")
```

### Get Recommendations

```python
# Get missing index recommendations
recommendations = await optimizer.get_missing_index_recommendations()

for rec in recommendations:
    print(f"[{rec.estimated_benefit}] {rec.reason}")
    print(f"  SQL: {rec.create_sql}")
```

### Apply Optimizations

```python
# Dry run (show what would be done)
results = await optimizer.apply_recommendations(recommendations, dry_run=True)

# Apply recommendations
results = await optimizer.apply_recommendations(recommendations, dry_run=False)
print(f"Applied: {len(results['applied'])}")
print(f"Failed: {len(results['failed'])}")
```

### Full Optimization Report

```python
report = await optimizer.get_optimization_report()

print(f"Total indexes: {report['indexes']['total_count']}")
print(f"Unused indexes: {report['indexes']['unused_count']}")
print(f"Recommendations: {report['summary']['total_recommendations']}")
print(f"  High priority: {report['summary']['high_priority']}")
print(f"  Medium priority: {report['summary']['medium_priority']}")
```

### Maintenance

```python
# Run VACUUM ANALYZE for better query plans
await optimizer.vacuum_analyze()  # All tables
await optimizer.vacuum_analyze('graph_entities')  # Specific table
```

---

## 4. Performance Monitoring

### Setup

```python
from aiecs.infrastructure.graph_storage.performance_monitoring import PerformanceMonitor

monitor = PerformanceMonitor(
    enabled=True,
    slow_query_threshold_ms=100.0,
    log_slow_queries=True
)
await monitor.initialize()
```

### Track Queries

```python
# Using context manager
async with monitor.track_query("get_entity", query):
    result = await conn.fetch(query, entity_id)

# Manual recording
duration_ms = 123.45
await monitor.record_query("get_entity", query, duration_ms, row_count=1)
```

### Analyze Query Plans

```python
# Get query execution plan
plan = await monitor.analyze_query_plan(
    conn,
    "SELECT * FROM graph_entities WHERE entity_type = $1",
    ("Person",)
)

# Check for warnings
warnings = plan.get_warnings()
for warning in warnings:
    print(f"⚠️  {warning}")

# Example warnings:
# - "Sequential scan detected - consider adding index"
# - "Inefficient nested loop - consider optimizing join"
# - "High query cost (12345) - consider optimization"
```

### Performance Reports

```python
# Get comprehensive report
report = monitor.get_performance_report()

print(f"Total queries: {report['total_queries']}")
print(f"Average time: {report['avg_query_time_ms']:.2f}ms")
print(f"Slow queries: {report['slow_query_count']}")

# Top slow queries
for query in report['top_slow_queries']:
    print(f"{query['query_type']}: {query['avg_time_ms']:.2f}ms "
          f"(p95: {query['p95_ms']:.2f}ms)")

# Get stats for specific query type
entity_stats = monitor.get_query_stats(query_type="get_entity")
```

### Prepared Statement Caching

```python
from aiecs.infrastructure.graph_storage.performance_monitoring import PreparedStatementCache

cache = PreparedStatementCache(max_size=100)

# Get or create prepared statement
stmt = await cache.get_or_prepare(
    conn,
    "get_entity",
    "SELECT * FROM graph_entities WHERE id = $1"
)

# Use prepared statement (faster query planning)
result = await conn.fetch(stmt, entity_id)
```

---

## 5. Benchmarking

### Run Benchmarks

```bash
# Run all benchmarks
pytest test/performance/test_graph_storage_benchmarks.py -v -m benchmark

# Run specific benchmark
pytest test/performance/test_graph_storage_benchmarks.py::TestGraphStorageBenchmarks::test_bulk_entity_insertion -v

# Compare backends
pytest test/performance/test_graph_storage_benchmarks.py::TestGraphStorageBenchmarks::test_neighbor_queries -v
```

### Custom Benchmarks

```python
import time

# Benchmark custom operation
async def benchmark_operation():
    store = OptimizedGraphStore()
    await store.initialize()
    
    # Prepare test data
    entities = generate_test_entities(10000)
    
    # Benchmark
    start = time.time()
    await store.batch_add_entities(entities)
    duration = time.time() - start
    
    print(f"Inserted 10,000 entities in {duration:.2f}s")
    print(f"Rate: {10000 / duration:.0f} entities/second")
    
    await store.close()
```

---

## Best Practices

### 1. Choose the Right Backend

**InMemoryGraphStore**:
- ✅ Development, testing
- ✅ Small graphs (< 100K nodes)
- ✅ Temporary data
- ❌ Production, persistence needed

**SQLiteGraphStore**:
- ✅ Small to medium graphs (< 1M nodes)
- ✅ Single-user applications
- ✅ Embedded systems
- ❌ High concurrency, large scale

**PostgresGraphStore**:
- ✅ Production deployments
- ✅ Large graphs (> 1M nodes)
- ✅ High concurrency
- ✅ Advanced features (JSONB, pgvector)

### 2. Optimize for Your Workload

**Read-Heavy Workload**:
- Enable caching with high TTL
- Optimize indexes for common queries
- Use read replicas if available

**Write-Heavy Workload**:
- Use batch operations
- Reduce index overhead
- Lower cache TTL
- Consider async writes

**Mixed Workload**:
- Moderate caching (5-10 min TTL)
- Selective indexing
- Monitor query patterns
- Adjust based on metrics

### 3. Monitor and Tune

```python
# Regular monitoring
async def monitor_performance():
    report = monitor.get_performance_report()
    
    # Alert on high average query time
    if report['avg_query_time_ms'] > 50:
        print(f"⚠️  High avg query time: {report['avg_query_time_ms']:.2f}ms")
    
    # Alert on many slow queries
    if report['slow_query_count'] > 100:
        print(f"⚠️  {report['slow_query_count']} slow queries detected")
    
    # Check index usage
    optimizer_report = await optimizer.get_optimization_report()
    if optimizer_report['indexes']['unused_count'] > 5:
        print(f"⚠️  {optimizer_report['indexes']['unused_count']} unused indexes")
```

### 4. Optimize Indexes Regularly

```python
# Weekly maintenance
async def weekly_maintenance():
    optimizer = IndexOptimizer(pool)
    
    # VACUUM ANALYZE for updated statistics
    await optimizer.vacuum_analyze()
    
    # Check for new recommendations
    recommendations = await optimizer.get_missing_index_recommendations()
    if recommendations:
        print(f"Found {len(recommendations)} index recommendations")
        # Review and apply manually
```

---

## Performance Checklist

### Initial Setup
- [ ] Choose appropriate backend for use case
- [ ] Enable connection pooling
- [ ] Create optimal indexes
- [ ] Enable performance monitoring

### For Production
- [ ] Enable Redis caching
- [ ] Configure cache TTL appropriately
- [ ] Use batch operations for bulk writes
- [ ] Monitor slow queries
- [ ] Regular VACUUM ANALYZE
- [ ] Review index usage monthly

### For Development
- [ ] Use InMemoryGraphStore for tests
- [ ] Enable performance monitoring
- [ ] Profile critical operations
- [ ] Test with realistic data volumes

---

## Troubleshooting

### Slow Queries

1. **Enable monitoring**:
   ```python
   monitor = PerformanceMonitor(slow_query_threshold_ms=50.0)
   ```

2. **Analyze query plan**:
   ```python
   plan = await monitor.analyze_query_plan(conn, slow_query)
   print(plan.get_warnings())
   ```

3. **Check indexes**:
   ```python
   optimizer = IndexOptimizer(pool)
   recommendations = await optimizer.get_missing_index_recommendations()
   ```

### Cache Not Working

1. **Check cache status**:
   ```python
   print(cache._initialized)  # Should be True
   print(cache.backend)  # Should not be None
   ```

2. **Test cache manually**:
   ```python
   await cache.backend.set("test", "value", 60)
   value = await cache.backend.get("test")
   print(value)  # Should print "value"
   ```

3. **Check Redis connection**:
   ```bash
   redis-cli ping  # Should return "PONG"
   ```

### High Memory Usage

1. **Check cache size**:
   ```python
   # Reduce cache size
   config = GraphStoreCacheConfig(max_cache_size_mb=500)
   ```

2. **Reduce TTL**:
   ```python
   config = GraphStoreCacheConfig(ttl=60)  # 1 minute
   ```

3. **Clear cache**:
   ```python
   await cache.clear()
   ```

---

## Summary

### Performance Gains

| Optimization | Speedup | Use Case |
|--------------|---------|----------|
| Redis Caching | 100-1000x | Frequently accessed data |
| Batch INSERT (COPY) | 100x | Bulk data loading |
| Batch INSERT (Multi-row) | 10-20x | Medium bulk operations |
| Composite Indexes | 10-50x | Filtered queries |
| GIN Indexes | 100-1000x | JSONB property searches |
| Prepared Statements | 2-5x | Repeated queries |

### Quick Wins

1. **Enable batch operations** for bulk writes (+100x)
2. **Add composite indexes** for common filters (+10-50x)
3. **Enable Redis caching** for hot data (+100-1000x)
4. **Use prepared statements** for repeated queries (+2-5x)

### Next Steps

1. Profile your specific workload
2. Apply relevant optimizations
3. Monitor performance metrics
4. Iterate based on results

---

For more information, see:
- `docs/knowledge_graph/PHASE6_TASK6.3_COMPLETE.md` - Complete implementation details
- `test/performance/test_graph_storage_benchmarks.py` - Benchmark examples
- `aiecs/infrastructure/graph_storage/` - Implementation code

