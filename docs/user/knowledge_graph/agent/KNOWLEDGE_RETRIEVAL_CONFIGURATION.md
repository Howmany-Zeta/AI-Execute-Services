# Knowledge Retrieval Configuration Guide

This guide documents the configuration options for knowledge retrieval in `KnowledgeAwareAgent`.

## Table of Contents

1. [Configuration Overview](#configuration-overview)
2. [Retrieval Strategy Options](#retrieval-strategy-options)
3. [Caching Configuration](#caching-configuration)
4. [Entity Extraction Configuration](#entity-extraction-configuration)
5. [Performance Tuning](#performance-tuning)
6. [Configuration Examples](#configuration-examples)

---

## Configuration Overview

The `KnowledgeAwareAgent` supports comprehensive configuration for knowledge retrieval through the `AgentConfiguration` model. All configuration options can be set when creating the agent.

### Basic Configuration

```python
from aiecs.domain.agent import KnowledgeAwareAgent, AgentConfiguration
from aiecs.infrastructure.graph_storage import InMemoryGraphStore

config = AgentConfiguration(
    retrieval_strategy="hybrid",
    enable_knowledge_caching=True,
    cache_ttl=300,
    max_context_size=50,
)

agent = KnowledgeAwareAgent(
    agent_id="agent_1",
    name="Knowledge Agent",
    llm_client=llm_client,
    tools=[],
    config=config,
    graph_store=graph_store
)
```

---

## Retrieval Strategy Options

The `retrieval_strategy` parameter controls how knowledge is retrieved from the graph.

### Available Strategies

#### 1. `"vector"` - Vector Similarity Search

**Description**: Uses semantic similarity via embeddings to find relevant entities.

**How It Works**:
- Converts query to embedding vector
- Computes cosine similarity with entity embeddings
- Returns top-k most similar entities

**Use Cases**:
- Semantic similarity queries
- Content discovery
- Finding conceptually related entities

**Example**:
```python
config = AgentConfiguration(
    retrieval_strategy="vector",
    max_context_size=10
)
```

**Performance**: O(n) where n = number of entities with embeddings

**Requirements**: 
- LLM client must support `get_embeddings()` method
- Entities must have embeddings stored

---

#### 2. `"graph"` - Graph Traversal Search

**Description**: Explores graph structure starting from seed entities.

**How It Works**:
- Extracts seed entities from query (via entity extraction)
- Traverses graph edges using BFS
- Scores entities by depth (closer = higher score)

**Use Cases**:
- Relationship exploration
- Network analysis
- Finding connected entities
- Multi-hop queries

**Example**:
```python
config = AgentConfiguration(
    retrieval_strategy="graph",
    max_context_size=20
)
```

**Performance**: O(b^d) where b = branching factor, d = depth

**Requirements**:
- Seed entities must be extractable from query
- Graph must have relationships between entities

**Note**: If no seed entities are found, the system will attempt to use vector search to find seeds.

---

#### 3. `"hybrid"` - Combined Vector + Graph Search

**Description**: Combines vector similarity with graph structure traversal.

**How It Works**:
1. Performs vector search to find initial candidates
2. Expands results with graph neighbors
3. Combines scores using weighted averaging (default: 60% vector, 40% graph)

**Use Cases**:
- Comprehensive search requiring both semantic and structural signals
- Context-aware retrieval
- Balanced results

**Example**:
```python
config = AgentConfiguration(
    retrieval_strategy="hybrid",
    max_context_size=15
)
```

**Performance**: O(n + b^d) - combines vector and graph search

**Requirements**:
- LLM client must support embeddings
- Entities must have embeddings
- Graph must have relationships

---

#### 4. `"auto"` - Automatic Strategy Selection

**Description**: Automatically selects the best strategy based on query characteristics.

**How It Works**:
- Analyzes query using `QueryIntentClassifier`
- Selects strategy based on query type:
  - Semantic queries → `vector"`
  - Relationship queries → `"graph"`
  - General queries → `"hybrid"`

**Use Cases**:
- Dynamic query handling
- Optimal strategy selection without manual configuration

**Example**:
```python
config = AgentConfiguration(
    retrieval_strategy="auto",
    max_context_size=20
)
```

**Performance**: Varies based on selected strategy

**Requirements**:
- QueryIntentClassifier must be available
- Falls back to hybrid if classification fails

---

### Strategy Selection Guidelines

| Query Type | Recommended Strategy | Reason |
|------------|---------------------|--------|
| "Find articles about machine learning" | `vector` | Semantic similarity |
| "Who does Alice know?" | `graph` | Relationship traversal |
| "Find people working at TechCorp" | `hybrid` | Needs both semantic and structural |
| "What is machine learning?" | `auto` | Let system decide |

---

## Caching Configuration

Knowledge retrieval results can be cached to improve performance for repeated queries.

### Configuration Options

#### `enable_knowledge_caching`

**Type**: `bool`  
**Default**: `True`  
**Description**: Enable/disable caching for knowledge retrieval results.

```python
config = AgentConfiguration(
    enable_knowledge_caching=True  # Enable caching
)
```

**Benefits**:
- Faster response times for repeated queries
- Reduced load on graph store
- Lower API costs (fewer embedding generations)

---

#### `cache_ttl`

**Type**: `int`  
**Default**: `300` (5 minutes)  
**Description**: Cache time-to-live in seconds.

```python
config = AgentConfiguration(
    enable_knowledge_caching=True,
    cache_ttl=600  # Cache for 10 minutes
)
```

**Guidelines**:
- **Short TTL (60-300s)**: Frequently changing knowledge, real-time data
- **Medium TTL (300-1800s)**: Stable knowledge, moderate update frequency
- **Long TTL (1800-3600s)**: Static knowledge, rarely changes

**Cache Backend**:
- Uses Redis if available (via `REDIS_HOST` environment variable)
- Falls back to in-memory cache if Redis not available

---

### Cache Invalidation

Caches are automatically invalidated when:
- TTL expires
- Graph store data changes (if supported)
- Manual invalidation via agent methods

---

## Entity Extraction Configuration

Entity extraction identifies entities from queries to use as seed entities for graph traversal.

### Configuration Option

#### `entity_extraction_provider`

**Type**: `str`  
**Default**: `"llm"`  
**Description**: Entity extraction provider to use.

**Available Providers**:

1. **`"llm"`** - LLM-based extraction (default)
   - Uses LLM to extract entities from text
   - Supports custom entity types
   - More accurate but slower

2. **`"ner"`** - Named Entity Recognition
   - Uses NER models for extraction
   - Faster but less flexible
   - Limited to standard entity types

3. **Custom provider name**
   - Use custom provider registered via `LLMClientFactory`
   - Allows integration with external extraction services

**Example**:
```python
config = AgentConfiguration(
    entity_extraction_provider="llm"  # Use LLM-based extraction
)
```

---

## Performance Tuning

### `max_context_size`

**Type**: `int`  
**Default**: `50`  
**Description**: Maximum number of knowledge entities to include in context.

```python
config = AgentConfiguration(
    max_context_size=20  # Limit to 20 entities
)
```

**Guidelines**:
- **Small (10-20)**: Fast retrieval, focused context
- **Medium (20-50)**: Balanced performance and context
- **Large (50-100)**: Comprehensive context, slower retrieval

**Impact**:
- Larger values → more context but slower retrieval
- Smaller values → faster retrieval but less context

---

### Context Prioritization

Entities are prioritized using:
1. **Relevance Score**: From search strategy (vector similarity or graph distance)
2. **Recency**: More recent entities prioritized
3. **Relevance Threshold**: Entities below threshold are filtered out

**Configuration** (internal, not directly configurable):
- Relevance weight: 60%
- Recency weight: 40%
- Default relevance threshold: 0.3

---

## Configuration Examples

### Example 1: Fast Semantic Search

```python
config = AgentConfiguration(
    retrieval_strategy="vector",
    enable_knowledge_caching=True,
    cache_ttl=600,  # 10 minutes
    max_context_size=10  # Small context for speed
)

agent = KnowledgeAwareAgent(
    agent_id="fast_agent",
    name="Fast Semantic Agent",
    llm_client=llm_client,
    tools=[],
    config=config,
    graph_store=graph_store
)
```

**Use Case**: Fast semantic similarity queries with caching

---

### Example 2: Comprehensive Graph Exploration

```python
config = AgentConfiguration(
    retrieval_strategy="graph",
    enable_knowledge_caching=False,  # Disable cache for fresh results
    max_context_size=50,  # Larger context
    entity_extraction_provider="llm"
)

agent = KnowledgeAwareAgent(
    agent_id="explorer_agent",
    name="Graph Explorer Agent",
    llm_client=llm_client,
    tools=[],
    config=config,
    graph_store=graph_store
)
```

**Use Case**: Deep graph exploration with fresh results

---

### Example 3: Balanced Hybrid Search

```python
config = AgentConfiguration(
    retrieval_strategy="hybrid",
    enable_knowledge_caching=True,
    cache_ttl=300,  # 5 minutes
    max_context_size=30,  # Balanced context size
    entity_extraction_provider="llm"
)

agent = KnowledgeAwareAgent(
    agent_id="hybrid_agent",
    name="Hybrid Search Agent",
    llm_client=llm_client,
    tools=[],
    config=config,
    graph_store=graph_store
)
```

**Use Case**: General-purpose knowledge retrieval

---

### Example 4: Auto Strategy with Custom Cache

```python
config = AgentConfiguration(
    retrieval_strategy="auto",  # Automatic strategy selection
    enable_knowledge_caching=True,
    cache_ttl=1800,  # 30 minutes (for stable knowledge)
    max_context_size=25
)

agent = KnowledgeAwareAgent(
    agent_id="auto_agent",
    name="Auto Strategy Agent",
    llm_client=llm_client,
    tools=[],
    config=config,
    graph_store=graph_store
)
```

**Use Case**: Flexible queries with optimal strategy selection

---

## Environment Variables

Some configuration can also be set via environment variables:

```bash
# Retrieval strategy
export KG_RETRIEVAL_STRATEGY="hybrid"

# Cache configuration
export KG_ENABLE_CACHE="true"
export KG_CACHE_TTL="300"

# Entity extraction
export KG_ENTITY_EXTRACTION_PROVIDER="llm"
```

**Note**: Programmatic configuration (via `AgentConfiguration`) takes precedence over environment variables.

---

## Best Practices

### 1. Choose Strategy Based on Query Type

- **Semantic queries**: Use `"vector"`
- **Relationship queries**: Use `"graph"`
- **General queries**: Use `"hybrid"` or `"auto"`

### 2. Tune Cache TTL Based on Data Stability

- **Stable knowledge**: Longer TTL (10-30 minutes)
- **Dynamic knowledge**: Shorter TTL (1-5 minutes)

### 3. Balance Context Size

- Start with default (50)
- Reduce if retrieval is too slow
- Increase if context is insufficient

### 4. Monitor Performance

- Track cache hit rates
- Monitor retrieval latency
- Adjust configuration based on metrics

---

## Troubleshooting

### Issue: Retrieval Strategy Not Working

**Symptom**: Selected strategy doesn't seem to be used

**Solutions**:
- Verify LLM client supports `get_embeddings()` for vector/hybrid strategies
- Check that entities have embeddings stored
- Ensure graph has relationships for graph strategy
- Verify seed entities can be extracted for graph strategy

### Issue: Cache Not Working

**Symptom**: Cache hit rate is 0%

**Solutions**:
- Verify `enable_knowledge_caching=True`
- Check Redis connection (if using Redis backend)
- Ensure queries are identical (cache key includes query text and strategy)

### Issue: Too Many/Few Entities Retrieved

**Symptom**: Context size doesn't match expectations

**Solutions**:
- Adjust `max_context_size` parameter
- Check relevance threshold settings
- Verify graph has sufficient entities

---

## Related Documentation

- [Retrieval Strategies Guide](../search/SEARCH_STRATEGIES.md)
- [Agent Integration Guide](./AGENT_INTEGRATION.md)
- [Performance Guide](../PERFORMANCE_GUIDE.md)
- [Configuration Guide](../CONFIGURATION_GUIDE.md)

