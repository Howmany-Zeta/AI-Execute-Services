# Knowledge Graph Performance Guide

## Overview

This guide documents the performance characteristics of the AIECS Knowledge Graph system, including benchmarks for new features and optimization recommendations.

## Table of Contents

1. [Structured Data Import Performance](#structured-data-import-performance)
2. [Reranking Performance](#reranking-performance)
3. [Schema Caching Performance](#schema-caching-performance)
4. [Query Optimization Performance](#query-optimization-performance)
5. [Knowledge Fusion Performance](#knowledge-fusion-performance)
6. [Performance Comparison](#performance-comparison)
7. [Optimization Recommendations](#optimization-recommendations)

## Structured Data Import Performance

### CSV Import Benchmarks

**Small Dataset (100 rows)**
- **Throughput**: 50-100 rows/second
- **Latency**: ~1-2 seconds
- **Memory**: Low (streaming import)

**Medium Dataset (1,000 rows)**
- **Throughput**: 100-200 rows/second
- **Latency**: ~5-10 seconds
- **Memory**: Moderate (batch processing)

**Large Dataset (10,000 rows)**
- **Throughput**: 150-300 rows/second
- **Latency**: ~30-60 seconds
- **Memory**: Moderate (configurable batch size)

### JSON Import Benchmarks

**Small Dataset (500 records)**
- **Throughput**: 100-200 records/second
- **Latency**: ~2-5 seconds
- **Memory**: Low to Moderate

**Large Dataset (5,000 records)**
- **Throughput**: 150-250 records/second
- **Latency**: ~20-30 seconds
- **Memory**: Moderate

### Import Performance Factors

**Batch Size Impact:**
- Batch size 50: ~50-100 rows/second
- Batch size 100: ~100-200 rows/second
- Batch size 500: ~150-300 rows/second

**Optimal Settings:**
```python
# For small datasets (<1K rows)
batch_size = 50
skip_errors = False

# For medium datasets (1K-10K rows)
batch_size = 100
skip_errors = True

# For large datasets (>10K rows)
batch_size = 500
skip_errors = True
```

## Reranking Performance

### Strategy Latency Comparison

**100 Entities, Top-K=20:**

| Strategy | Latency | Overhead | Use Case |
|----------|---------|----------|----------|
| Text Similarity | 50-100ms | Low | Fast, keyword-focused |
| Semantic | 100-200ms | Medium | Meaning-focused |
| Structural | 80-150ms | Medium | Graph-aware |
| Hybrid | 150-300ms | High | Best results |

### Reranking Overhead

**Search without reranking**: 10-20ms  
**Search with text reranking**: 60-120ms (3-6x overhead)  
**Search with hybrid reranking**: 160-320ms (8-16x overhead)

**Recommendation**: Use reranking when precision is more important than latency.

### Scaling Characteristics

**Latency vs. Number of Entities:**
- 50 entities: 30-60ms
- 100 entities: 50-100ms
- 200 entities: 100-200ms
- 500 entities: 250-500ms

**Latency vs. Top-K:**
- Top-K=10: 40-80ms
- Top-K=20: 50-100ms
- Top-K=50: 80-150ms
- Top-K=100: 120-200ms

## Schema Caching Performance

### Cache Hit Rate

**Typical Workloads:**
- Repeated schema lookups: 90-95% hit rate
- Mixed workloads: 70-80% hit rate
- Random access: 40-50% hit rate

### Performance Improvement

**Without Cache:**
- Schema lookup: 5-10ms
- 100 lookups: 500-1000ms

**With Cache:**
- Cache hit: <1ms
- Cache miss: 5-10ms
- 100 lookups (80% hit rate): 100-200ms

**Speedup**: 3-5x for typical workloads

### Cache Configuration

**Optimal Settings:**
```python
# Development
cache_size = 100
ttl_seconds = 300  # 5 minutes

# Production
cache_size = 1000
ttl_seconds = 3600  # 1 hour

# High-performance
cache_size = 5000
ttl_seconds = 7200  # 2 hours
```

## Query Optimization Performance

### Optimization Time Reduction

**Simple Queries (1-3 steps):**
- Unoptimized: 10-20ms
- Optimized: 5-10ms
- **Improvement**: 40-50%

**Medium Queries (4-7 steps):**
- Unoptimized: 50-100ms
- Optimized: 20-40ms
- **Improvement**: 50-60%

**Complex Queries (8+ steps):**
- Unoptimized: 200-500ms
- Optimized: 80-200ms
- **Improvement**: 60-70%

### Optimization Strategies

**Cost-Based Optimization:**
- Join reordering: 20-40% improvement
- Filter pushdown: 30-50% improvement
- Index selection: 40-60% improvement

**Combined Optimizations:**
- Total improvement: 60-80% for complex queries

## Knowledge Fusion Performance

### Fusion Throughput

**Small Graph (50 entities):**
- Duration: 1-3 seconds
- Throughput: 15-50 entities/second
- Merge groups: 5-10

**Medium Graph (200 entities):**
- Duration: 5-15 seconds
- Throughput: 10-40 entities/second
- Merge groups: 20-40

**Large Graph (1,000 entities):**
- Duration: 30-90 seconds
- Throughput: 10-30 entities/second
- Merge groups: 100-200

### Similarity Threshold Impact

**Threshold 0.95 (strict):**
- Fewer merges, faster execution
- Duration: 5-10 seconds (200 entities)

**Threshold 0.85 (balanced):**
- Moderate merges, moderate speed
- Duration: 10-20 seconds (200 entities)

**Threshold 0.70 (lenient):**
- More merges, slower execution
- Duration: 20-40 seconds (200 entities)

### Conflict Resolution Performance

| Strategy | Latency per Conflict | Use Case |
|----------|---------------------|----------|
| most_complete | <1ms | Fast, general |
| most_recent | <1ms | Fast, time-based |
| most_confident | 1-2ms | Moderate, quality |
| longest | <1ms | Fast, text |
| keep_all | <1ms | Fast, preserve all |

## Performance Comparison

### Before vs. After Optimizations

**Search Performance:**
- Before: 50-100ms (no reranking)
- After: 100-300ms (with hybrid reranking)
- Trade-off: 2-3x latency for better precision

**Import Performance:**
- Before: Manual entity creation (10-20 entities/second)
- After: Structured import (100-300 rows/second)
- **Improvement**: 5-30x faster

**Schema Operations:**
- Before: No caching (5-10ms per lookup)
- After: With caching (<1ms for hits)
- **Improvement**: 5-10x faster for repeated lookups

**Query Execution:**
- Before: No optimization (100-500ms)
- After: With optimization (40-200ms)
- **Improvement**: 40-70% faster

## Optimization Recommendations

### 1. Structured Data Import

**For Best Throughput:**
- Use batch size 100-500
- Enable skip_errors for large datasets
- Use PostgreSQL for very large imports (>100K rows)

**Example:**
```python
pipeline = StructuredDataPipeline(
    mapping=schema_mapping,
    graph_store=store,
    batch_size=500,
    skip_errors=True
)
```

### 2. Search and Reranking

**For Low Latency:**
- Use text reranking only
- Limit top_k to 20-50
- Disable reranking for simple queries

**For High Precision:**
- Use hybrid reranking
- Increase top_k to 100-200
- Accept 2-3x latency overhead

**Example:**
```python
# Low latency
result = search(query, enable_reranking=True, rerank_strategy="text", top_k=20)

# High precision
result = search(query, enable_reranking=True, rerank_strategy="hybrid", top_k=100)
```

### 3. Schema Caching

**For Best Performance:**
- Enable caching in production
- Set TTL to 1-2 hours
- Use cache size 1000-5000

**Example:**
```python
schema_manager = SchemaManager(
    cache_size=1000,
    ttl_seconds=3600,
    enable_cache=True
)
```

### 4. Query Optimization

**For Complex Queries:**
- Enable query optimization
- Use balanced strategy
- Monitor query statistics

**Example:**
```python
optimizer = QueryOptimizer(
    enable_optimization=True,
    strategy="balanced"
)
```

### 5. Knowledge Fusion

**For Large Graphs:**
- Use similarity threshold 0.85-0.90
- Use most_complete conflict resolution
- Run fusion periodically, not on every update

**Example:**
```python
fusion = KnowledgeFusion(
    graph_store=store,
    similarity_threshold=0.85,
    conflict_resolution_strategy="most_complete"
)
```

## See Also

- [Configuration Guide](./CONFIGURATION_GUIDE.md)
- [Reranking Strategies Guide](./reasoning/reranking-strategies-guide.md)
- [Schema Caching Guide](./reasoning/schema-caching-guide.md)
- [Query Optimization Guide](./reasoning/query-optimization-guide.md)

