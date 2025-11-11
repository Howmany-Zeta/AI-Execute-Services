# Knowledge Graph Search Strategies

## Overview

The knowledge graph system provides multiple sophisticated search strategies for querying entities and relationships. Each strategy is optimized for different use cases and can be combined for powerful query capabilities.

## Search Strategy Types

### 1. Vector Search

**Purpose**: Find entities semantically similar to a query using vector embeddings.

**How It Works**:
- Converts query to embedding vector
- Computes cosine similarity with all entity embeddings
- Returns top-k most similar entities

**Use Cases**:
- Content discovery
- Semantic similarity matching
- Finding related concepts

**Example**:
```python
results = await graph_store.vector_search(
    query_embedding=[0.1, 0.2, 0.3, ...],
    entity_type="Article",
    max_results=10,
    score_threshold=0.7
)
```

**Performance**: O(n) where n = number of entities with embeddings

### 2. Graph Structure Search

**Purpose**: Explore graph structure from seed entities.

**How It Works**:
- Starts from seed entities
- Traverses graph edges (BFS)
- Scores by depth (closer = higher score)

**Use Cases**:
- Relationship exploration
- Network analysis
- Connected entity discovery

**Example**:
```python
neighbors = await graph_store.get_neighbors(
    entity_id="person_1",
    relation_type="KNOWS",
    direction="outgoing"
)
```

**Performance**: O(b^d) where b = branching factor, d = depth

### 3. Hybrid Search

**Purpose**: Combine vector similarity with graph structure.

**How It Works**:
1. Performs vector search
2. Expands results with graph neighbors
3. Combines scores with weighted averaging

**Use Cases**:
- Comprehensive search
- Context-aware retrieval
- Balanced semantic + structural results

**Example**:
```python
from aiecs.application.knowledge_graph.search.hybrid_search import (
    HybridSearchStrategy,
    HybridSearchConfig,
    SearchMode
)

strategy = HybridSearchStrategy(graph_store)

config = HybridSearchConfig(
    mode=SearchMode.HYBRID,
    vector_weight=0.6,
    graph_weight=0.4,
    max_results=10
)

results = await strategy.search(
    query_embedding=[0.1, 0.2, ...],
    config=config
)
```

**Performance**: O(n + b^d) - combines vector and graph search

### 4. Personalized PageRank

**Purpose**: Find influential entities using random walk algorithm.

**How It Works**:
- Random walk with restart at seed entities
- Iterates until convergence
- Ranks entities by visit frequency

**Use Cases**:
- Influence analysis
- Authority ranking
- Central entity identification

**Example**:
```python
from aiecs.application.knowledge_graph.retrieval.retrieval_strategies import (
    PersonalizedPageRank
)

ppr = PersonalizedPageRank(graph_store)

results = await ppr.retrieve(
    seed_entity_ids=["key_person"],
    max_results=20,
    alpha=0.15  # restart probability
)
```

**Performance**: O(iterations × edges) - typically 10-50 iterations

### 5. Multi-Hop Retrieval

**Purpose**: Discover entities within N hops from seeds.

**How It Works**:
- Breadth-first expansion from seeds
- Scores decay with hop distance
- Configurable depth limit

**Use Cases**:
- Friend-of-friend discovery
- Local network exploration
- Proximity-based search

**Example**:
```python
from aiecs.application.knowledge_graph.retrieval.retrieval_strategies import (
    MultiHopRetrieval
)

retrieval = MultiHopRetrieval(graph_store)

results = await retrieval.retrieve(
    seed_entity_ids=["start_node"],
    max_hops=2,
    score_decay=0.5,
    max_results=50
)
```

**Performance**: O(b^d) where b = branching factor, d = max_hops

### 6. Filtered Retrieval

**Purpose**: Precise entity selection by properties.

**How It Works**:
- Filters entities by type and properties
- Supports exact matches and custom functions
- Scores by match quality

**Use Cases**:
- Attribute-based selection
- Data validation queries
- Precise entity lookup

**Example**:
```python
from aiecs.application.knowledge_graph.retrieval.retrieval_strategies import (
    FilteredRetrieval
)

retrieval = FilteredRetrieval(graph_store)

results = await retrieval.retrieve(
    entity_type="Person",
    property_filters={"role": "Engineer", "level": "Senior"},
    max_results=100
)
```

**Performance**: O(n) where n = candidate entities

### 7. Pattern-Based Traversal

**Purpose**: Follow specific relationship patterns.

**How It Works**:
- Uses PathPattern to specify constraints
- Traverses graph matching pattern
- Returns paths and entities

**Use Cases**:
- Pattern matching
- Path discovery
- Relationship chain exploration

**Example**:
```python
from aiecs.application.knowledge_graph.traversal.enhanced_traversal import (
    EnhancedTraversal
)
from aiecs.domain.knowledge_graph.models.path_pattern import PathPattern

traversal = EnhancedTraversal(graph_store)

pattern = PathPattern(
    relation_types=["WORKS_FOR", "LOCATED_IN"],
    max_depth=2,
    allow_cycles=False
)

paths = await traversal.traverse_with_pattern(
    start_entity_id="person_1",
    pattern=pattern,
    max_results=10
)
```

**Performance**: O(paths × depth) - depends on pattern complexity

## Strategy Comparison

| Strategy | Best For | Speed | Precision | Scalability |
|----------|----------|-------|-----------|-------------|
| Vector | Semantic similarity | Fast | High | Medium |
| Graph | Structure exploration | Fast | Medium | High |
| Hybrid | Balanced search | Medium | High | Medium |
| PageRank | Influence ranking | Medium | High | Medium |
| Multi-Hop | Local exploration | Fast | Medium | High |
| Filtered | Precise selection | Fast | Very High | High |
| Traverse | Pattern matching | Medium | High | Medium |

## Combining Strategies

### Pattern 1: Vector → Graph

```python
# Find semantically similar entities
vector_results = await graph_store.vector_search(
    query_embedding=query,
    max_results=5
)

# Explore their graph neighbors
seeds = [e.id for e, _ in vector_results]
graph_results = await multihop.retrieve(
    seed_entity_ids=seeds,
    max_hops=2
)
```

### Pattern 2: PageRank → Filter

```python
# Find influential entities
pagerank_results = await ppr.retrieve(
    seed_entity_ids=["key_node"],
    max_results=50
)

# Filter by properties
filtered = [
    e for e, score in pagerank_results
    if e.properties.get("verified") == True
]
```

### Pattern 3: Hybrid with Caching

```python
from aiecs.application.knowledge_graph.retrieval.retrieval_strategies import (
    RetrievalCache
)

cache = RetrievalCache(max_size=100, ttl=300)

results = await cache.get_or_compute(
    cache_key="frequent_query",
    compute_fn=lambda: hybrid_strategy.search(...)
)
```

## Performance Optimization

### 1. Use Appropriate Strategy

- **Small graphs (< 1K entities)**: Any strategy works well
- **Medium graphs (1K-10K)**: Vector, Graph, Multi-Hop, Filtered
- **Large graphs (> 10K)**: Filtered, Graph (with depth limits)

### 2. Limit Search Scope

```python
# Use entity_type filter
results = await vector_search(
    query_embedding=query,
    entity_type="Person",  # Reduces search space
    max_results=10
)
```

### 3. Set Reasonable Limits

```python
# Limit depth for graph operations
results = await multihop.retrieve(
    seed_entity_ids=seeds,
    max_hops=2,  # Keep ≤ 3 for performance
    max_results=50  # Reasonable limit
)
```

### 4. Enable Caching

```python
# Cache frequent queries
cache = RetrievalCache(max_size=100, ttl=300)
results = await cache.get_or_compute(...)
```

### 5. Batch Operations

```python
# Use transactions for multiple operations
async with store.transaction():
    await store.add_entity(e1)
    await store.add_entity(e2)
    # More efficient than individual commits
```

## Best Practices

1. **Choose the Right Strategy**: Match strategy to use case
2. **Set Thresholds**: Use similarity thresholds to filter low-quality results
3. **Limit Depth**: Keep graph traversal depth ≤ 3 for performance
4. **Use Filters**: Entity type and property filters reduce search space
5. **Cache Results**: Enable caching for repeated queries
6. **Combine Strategies**: Use multiple strategies for comprehensive results

## See Also

- [Hybrid Search Documentation](./HYBRID_SEARCH.md)
- [Advanced Retrieval Strategies](./RETRIEVAL_STRATEGIES.md)
- [Graph Traversal Guide](./TRAVERSAL.md)
- [Graph Search Tool Documentation](../tools/GRAPH_SEARCH_TOOL.md)
- [Examples](../../examples/)

