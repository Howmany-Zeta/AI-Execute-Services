# Graph Search Tool Documentation

## Overview

The **Graph Search Tool** is an AIECS tool that provides powerful knowledge graph search capabilities through multiple search modes. It enables AI agents to query knowledge graphs using vector similarity, graph structure, hybrid approaches, and advanced retrieval strategies.

## Tool Registration

- **Tool Name**: `graph_search`
- **Tool Class**: `GraphSearchTool`
- **Auto-registered**: Yes (via `@register_tool` decorator)

## Features

The tool supports **7 search modes**:

1. **Vector Search** - Semantic similarity search using embeddings
2. **Graph Search** - Structure-based exploration from seed entities
3. **Hybrid Search** - Combined vector + graph search
4. **PageRank** - Importance ranking using Personalized PageRank
5. **Multi-Hop** - N-hop neighbor discovery
6. **Filtered** - Property-based entity filtering
7. **Traverse** - Pattern-based graph traversal

## Input Schema

### Required Parameters

- `mode` (string): Search mode - one of:
  - `"vector"` - Vector similarity search
  - `"graph"` - Graph structure search
  - `"hybrid"` - Combined search
  - `"pagerank"` - PageRank importance
  - `"multihop"` - Multi-hop neighbors
  - `"filtered"` - Filtered retrieval
  - `"traverse"` - Pattern traversal

### Optional Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | None | Natural language query (auto-converted to embedding) |
| `query_embedding` | List[float] | None | Pre-computed query embedding vector |
| `seed_entity_ids` | List[string] | None | Starting entity IDs (for graph/pagerank/multihop/traverse) |
| `entity_type` | string | None | Filter by entity type (e.g., "Person", "Company") |
| `property_filters` | object | None | Filter by properties (e.g., `{"role": "Engineer"}`) |
| `relation_types` | List[string] | None | Filter by relation types |
| `max_results` | integer | 10 | Maximum results to return (1-100) |
| `max_depth` | integer | 2 | Maximum traversal depth (1-5) |
| `vector_threshold` | float | 0.0 | Minimum similarity threshold (0.0-1.0) |
| `vector_weight` | float | 0.6 | Vector weight in hybrid mode (0.0-1.0) |
| `graph_weight` | float | 0.4 | Graph weight in hybrid mode (0.0-1.0) |
| `expand_results` | boolean | true | Expand results with neighbors (hybrid) |
| `use_cache` | boolean | true | Enable result caching |
| `enable_reranking` | boolean | false | Enable result reranking for improved relevance |
| `rerank_strategy` | string | "text" | Reranking strategy: "text", "semantic", "structural", "hybrid" |

### Reranking Parameters

The tool supports **result reranking** to improve search relevance by re-scoring initial results using additional signals:

- **`enable_reranking`** (boolean, default: false): Enable/disable reranking
- **`rerank_strategy`** (string, default: "text"): Reranking strategy:
  - `"text"`: Text similarity reranking (BM25-based)
  - `"semantic"`: Semantic similarity using embeddings
  - `"structural"`: Graph structure importance (centrality, PageRank)
  - `"hybrid"`: Combines all signals for best results

**When to use reranking:**
- When initial search results need refinement
- For complex queries requiring multiple relevance signals
- When combining vector and graph search (hybrid mode)
- To boost precision at the cost of slight latency increase

## Output Format

### Success Response

```json
{
  "success": true,
  "mode": "hybrid",
  "num_results": 5,
  "results": [
    {
      "entity_id": "person_1",
      "entity_type": "Person",
      "properties": {
        "name": "Alice",
        "role": "Engineer"
      },
      "score": 0.95,
      "score_type": "combined"  // Optional, depends on mode
    }
  ]
}
```

### Error Response

```json
{
  "success": false,
  "error": "Error message here"
}
```

## Usage Examples

### Example 1: Vector Search

Find entities semantically similar to a query.

```python
result = tool.execute({
    "mode": "vector",
    "query": "machine learning researchers",
    "max_results": 10,
    "vector_threshold": 0.7
})
```

**Use Cases:**
- Content discovery
- Semantic similarity matching
- Finding related entities

### Example 2: Graph Search

Explore graph structure from seed entities.

```python
result = tool.execute({
    "mode": "graph",
    "seed_entity_ids": ["company_1"],
    "max_depth": 2,
    "max_results": 20
})
```

**Use Cases:**
- Relationship exploration
- Network analysis
- Connected entity discovery

### Example 3: Hybrid Search

Combine vector similarity with graph structure.

```python
result = tool.execute({
    "mode": "hybrid",
    "query": "AI research papers",
    "seed_entity_ids": ["author_1"],
    "vector_weight": 0.6,
    "graph_weight": 0.4,
    "max_results": 15
})
```

**Use Cases:**
- Comprehensive search
- Balanced semantic + structural results
- Context-aware retrieval

### Example 4: PageRank Search

Find influential entities in the graph.

```python
result = tool.execute({
    "mode": "pagerank",
    "seed_entity_ids": ["key_person"],
    "max_results": 10
})
```

**Use Cases:**
- Influence analysis
- Authority ranking
- Central entity identification

### Example 5: Multi-Hop Search

Discover entities within N hops.

```python
result = tool.execute({
    "mode": "multihop",
    "seed_entity_ids": ["person_1"],
    "max_depth": 3,
    "max_results": 25
})
```

**Use Cases:**
- Friend-of-friend discovery
- Local network exploration
- Proximity-based search

### Example 6: Filtered Search

Precise filtering by entity properties.

```python
result = tool.execute({
    "mode": "filtered",
    "entity_type": "Person",
    "property_filters": {
        "role": "Engineer",
        "level": "Senior",
        "location": "SF"
    },
    "max_results": 50
})
```

**Use Cases:**
- Attribute-based selection
- Data validation queries
- Precise entity lookup

### Example 7: Pattern-Based Traversal

Follow specific relationship patterns.

```python
result = tool.execute({
    "mode": "traverse",
    "seed_entity_ids": ["start_node"],
    "relation_types": ["WORKS_FOR", "LOCATED_IN"],
    "max_depth": 2,
    "max_results": 15
})
```

**Use Cases:**
- Pattern matching
- Path discovery
- Relationship chain exploration

### Example 8: Search with Reranking

Improve search relevance using reranking.

```python
# Hybrid search with semantic reranking
result = tool.execute({
    "mode": "hybrid",
    "query": "machine learning experts in computer vision",
    "max_results": 20,
    "enable_reranking": True,
    "rerank_strategy": "semantic"
})
```

**Reranking Strategies:**

1. **Text Reranking** - BM25-based text similarity
```python
result = tool.execute({
    "mode": "vector",
    "query": "database optimization",
    "enable_reranking": True,
    "rerank_strategy": "text"
})
```

2. **Semantic Reranking** - Deep semantic similarity
```python
result = tool.execute({
    "mode": "hybrid",
    "query": "natural language processing",
    "enable_reranking": True,
    "rerank_strategy": "semantic"
})
```

3. **Structural Reranking** - Graph importance signals
```python
result = tool.execute({
    "mode": "graph",
    "seed_entity_ids": ["person_1"],
    "enable_reranking": True,
    "rerank_strategy": "structural"
})
```

4. **Hybrid Reranking** - All signals combined (best results)
```python
result = tool.execute({
    "mode": "hybrid",
    "query": "AI researchers",
    "enable_reranking": True,
    "rerank_strategy": "hybrid",
    "max_results": 10
})
```

**Use Cases:**
- Improving precision for complex queries
- Combining multiple relevance signals
- Refining large result sets
- Production search systems

## Advanced Usage

### Combining with Other Tools

```python
# First, search for relevant entities
search_result = graph_search_tool.execute({
    "mode": "hybrid",
    "query": "AI research",
    "max_results": 5
})

# Then, build more knowledge from found entities
for entity in search_result["results"]:
    entity_id = entity["entity_id"]
    # Use entity_id for further operations
```

### Caching for Performance

```python
# Enable caching (default)
result1 = tool.execute({
    "mode": "vector",
    "query": "frequent query",
    "use_cache": true
})

# Second call uses cache
result2 = tool.execute({
    "mode": "vector",
    "query": "frequent query",
    "use_cache": true
})  # Much faster!
```

### Entity Type Filtering

```python
# Only search Person entities
result = tool.execute({
    "mode": "hybrid",
    "query": "software engineer",
    "entity_type": "Person",
    "max_results": 20
})
```

## Performance Considerations

### Search Mode Performance

| Mode | Complexity | Best For | Typical Time |
|------|-----------|----------|--------------|
| Vector | O(n) | Small-medium graphs (< 10K entities) | Fast |
| Graph | O(b^d) | Local exploration (depth ≤ 3) | Fast |
| Hybrid | O(n + b^d) | Balanced search | Medium |
| PageRank | O(iterations × edges) | Graphs < 10K nodes | Medium |
| Multi-Hop | O(b^d) | Shallow depth (≤ 3) | Fast |
| Filtered | O(n) | Property-based queries | Fast |
| Traverse | O(paths) | Pattern matching | Medium |

### Optimization Tips

1. **Use appropriate max_results**: Lower values are faster
2. **Limit max_depth**: Keep ≤ 3 for graph/multihop modes
3. **Enable caching**: Significantly improves repeated queries
4. **Use vector_threshold**: Reduces vector search space
5. **Apply entity_type filter**: Narrows search scope

## Error Handling

### Common Errors

**Invalid Mode**
```json
{
  "success": false,
  "error": "Unknown search mode: invalid_mode"
}
```

**Missing Required Parameters**
- Vector mode requires `query` or `query_embedding`
- Graph/PageRank/Multi-Hop modes require `seed_entity_ids`

### Error Recovery

```python
result = tool.execute({
    "mode": "vector",
    "query": "search query"
})

if not result["success"]:
    # Handle error
    print(f"Search failed: {result['error']}")
    # Fallback to different mode or parameters
else:
    # Process results
    for entity in result["results"]:
        print(f"Found: {entity['entity_id']}")
```

## Integration with Agent Workflows

### Agentic Pattern 1: Exploratory Search

```python
# Agent explores graph iteratively
current_entities = ["start_node"]
discovered = []

for depth in range(3):
    result = tool.execute({
        "mode": "multihop",
        "seed_entity_ids": current_entities,
        "max_depth": 1
    })
    
    discovered.extend(result["results"])
    current_entities = [e["entity_id"] for e in result["results"]]
```

### Agentic Pattern 2: Ranked Discovery

```python
# Agent finds and ranks important entities
pagerank_result = tool.execute({
    "mode": "pagerank",
    "seed_entity_ids": ["topic_entity"],
    "max_results": 20
})

# Filter by properties
filtered = [
    e for e in pagerank_result["results"]
    if e["properties"].get("verified") == True
]
```

### Agentic Pattern 3: Multi-Modal Search

```python
# Combine different search modes
vector_results = tool.execute({
    "mode": "vector",
    "query": "AI research"
})

# Use vector results as seeds for graph exploration
graph_results = tool.execute({
    "mode": "graph",
    "seed_entity_ids": [e["entity_id"] for e in vector_results["results"][:3]]
})
```

## Testing

The tool includes comprehensive unit tests covering:
- All 7 search modes
- Entity type filtering
- Property-based filtering
- Error handling
- Parameter validation

Run tests:
```bash
poetry run pytest test/unit_tests/tools/test_graph_search_tool.py -v
```

## See Also

- [Graph Builder Tool Documentation](./GRAPH_BUILDER_TOOL.md)
- [Search Strategies Documentation](../search/SEARCH_STRATEGIES.md)
- [Graph Reasoning Tool Documentation](./GRAPH_REASONING_TOOL.md)

## Support

For issues or questions:
- Check test examples in `test/unit_tests/tools/test_graph_search_tool.py`
- Review implementation in `aiecs/tools/knowledge_graph/graph_search_tool.py`
- See usage examples in `docs/knowledge_graph/examples/`

