# Agent Integration with Knowledge Graph

This document describes how to integrate knowledge graph capabilities with AIECS agents.

## Overview

The knowledge graph integration provides agents with:
- **Persistent Knowledge Storage**: Store and retrieve entities and relations
- **Graph-Aware Reasoning**: Use graph structure for multi-hop reasoning
- **Knowledge-Augmented ReAct Loop**: Automatic knowledge retrieval during reasoning
- **Graph Query Tools**: Built-in tools for graph operations

## Agent Types

### 1. HybridAgent (Original)

The original `HybridAgent` provides standard ReAct loop functionality without knowledge graph integration.

**Use When**:
- You don't need knowledge graph capabilities
- You want backward compatibility
- Simple tool-based reasoning is sufficient

**Example**:
```python
from aiecs.domain.agent import HybridAgent, AgentConfiguration
from aiecs.llm import OpenAIClient

agent = HybridAgent(
    agent_id="hybrid_1",
    name="Standard Hybrid Agent",
    llm_client=llm_client,
    tools=["web_search", "calculator"],
    config=AgentConfiguration()
)
```

### 2. KnowledgeAwareAgent (Enhanced)

The `KnowledgeAwareAgent` extends `HybridAgent` with knowledge graph integration.

**Features**:
- Knowledge-augmented ReAct loop (Retrieve → Reason → Act → Observe)
- Automatic knowledge retrieval before reasoning
- Graph reasoning tool integration
- Knowledge-guided action selection

**Use When**:
- You need knowledge graph capabilities
- You want multi-hop reasoning
- You need persistent knowledge storage
- You want graph-augmented prompts

**Example**:
```python
from aiecs.domain.agent import KnowledgeAwareAgent, AgentConfiguration
from aiecs.infrastructure.graph_storage import InMemoryGraphStore

# Create graph store
graph_store = InMemoryGraphStore()
await graph_store.initialize()

# Create knowledge-aware agent
agent = KnowledgeAwareAgent(
    agent_id="kg_agent_1",
    name="Knowledge-Aware Agent",
    llm_client=llm_client,
    tools=["web_search"],
    config=AgentConfiguration(),
    graph_store=graph_store
)

await agent.initialize()
```

### 3. GraphAwareAgentMixin (Reusable)

The `GraphAwareAgentMixin` provides reusable graph functionality for any agent class.

**Features**:
- Knowledge formatting utilities
- Graph query helpers
- Knowledge context management
- Can be mixed into any agent

**Use When**:
- You want to add graph capabilities to a custom agent
- You need reusable graph utilities
- You want consistent knowledge formatting

**Example**:
```python
from aiecs.domain.agent import BaseAIAgent, GraphAwareAgentMixin
from aiecs.infrastructure.graph_storage import InMemoryGraphStore

class CustomGraphAgent(BaseAIAgent, GraphAwareAgentMixin):
    def __init__(self, agent_id, name, config, graph_store):
        super().__init__(agent_id, name, AgentType.DEVELOPER, config)
        self.graph_store = graph_store

# Use mixin methods
agent = CustomGraphAgent(..., graph_store=graph_store)
neighbors = await agent.get_entity_neighbors("alice")
formatted = agent.format_entities(neighbors)
```

## Integration Patterns

### Pattern 1: Direct Integration

Use `KnowledgeAwareAgent` for full knowledge graph integration.

```python
from aiecs.domain.agent import KnowledgeAwareAgent
from aiecs.infrastructure.graph_storage import InMemoryGraphStore

graph_store = InMemoryGraphStore()
await graph_store.initialize()

agent = KnowledgeAwareAgent(
    agent_id="agent_1",
    name="KG Agent",
    llm_client=llm_client,
    tools=[],
    config=config,
    graph_store=graph_store
)

await agent.initialize()
```

### Pattern 2: Mixin Integration

Use `GraphAwareAgentMixin` to add graph capabilities to custom agents.

```python
from aiecs.domain.agent import BaseAIAgent, GraphAwareAgentMixin

class MyAgent(BaseAIAgent, GraphAwareAgentMixin):
    def __init__(self, graph_store, ...):
        super().__init__(...)
        self.graph_store = graph_store
```

### Pattern 3: Conditional Integration

Enable/disable graph capabilities based on configuration.

```python
agent = KnowledgeAwareAgent(
    ...,
    graph_store=graph_store if use_kg else None,
    enable_graph_reasoning=use_kg
)
```

## Graph Store Options

### InMemoryGraphStore

**Use For**:
- Development and testing
- Small graphs (< 100K nodes)
- Prototyping
- Temporary knowledge

**Example**:
```python
from aiecs.infrastructure.graph_storage import InMemoryGraphStore

graph_store = InMemoryGraphStore()
await graph_store.initialize()
```

### SQLiteGraphStore

**Use For**:
- Production applications
- Persistent knowledge storage
- Medium-sized graphs (< 1M nodes)
- Single-process applications

**Example**:
```python
from aiecs.infrastructure.graph_storage import SQLiteGraphStore

graph_store = SQLiteGraphStore(db_path="knowledge.db")
await graph_store.initialize()
```

## Available Tools

### GraphSearchTool

Provides multiple search modes for knowledge graph queries.

**Modes**:
- `vector` - Vector similarity search
- `graph` - Graph traversal search
- `hybrid` - Combined vector + graph search
- `pagerank` - Personalized PageRank
- `multihop` - Multi-hop neighbor retrieval
- `filtered` - Filtered retrieval
- `traverse` - Pattern-based traversal

**Example**:
```python
# Agent automatically has access to graph_search tool
result = await agent.execute_task({
    "description": "Find people who work at TechCorp"
})
```

### GraphReasoningTool

Provides reasoning capabilities over the knowledge graph.

**Modes**:
- `query_plan` - Plan complex queries
- `multi_hop` - Multi-hop reasoning
- `inference` - Logical inference
- `evidence_synthesis` - Evidence-based reasoning
- `full_reasoning` - Complete reasoning pipeline

**Example**:
```python
# Agent automatically has access to graph_reasoning tool
result = await agent.execute_task({
    "description": "How is Alice connected to TechCorp?"
})
```

## Knowledge-Augmented ReAct Loop

The `KnowledgeAwareAgent` uses an enhanced ReAct loop:

```
1. RETRIEVE: Get relevant knowledge from graph
2. THINK: LLM reasons with retrieved knowledge
3. ACT: Execute tool or provide answer
4. OBSERVE: Review results and continue
```

**Benefits**:
- Agents have context from knowledge graph
- Better reasoning with structured knowledge
- Automatic knowledge retrieval
- Transparent process (visible in reasoning steps)

### Retrieval Strategies

The agent supports multiple retrieval strategies configured via `AgentConfiguration.retrieval_strategy`:

- **`"vector"`**: Semantic similarity search using embeddings
- **`"graph"`**: Graph traversal from seed entities
- **`"hybrid"`**: Combined vector + graph search (default)
- **`"auto"`**: Automatic strategy selection based on query

See [Knowledge Retrieval Configuration Guide](./KNOWLEDGE_RETRIEVAL_CONFIGURATION.md) for details.

### Caching

Knowledge retrieval results are cached by default to improve performance:

- **Cache Backend**: Redis (if available) or in-memory fallback
- **Cache TTL**: Configurable via `AgentConfiguration.cache_ttl` (default: 300 seconds)
- **Cache Key**: Based on query text and retrieval strategy

See [Metrics and Monitoring Guide](./METRICS_AND_MONITORING.md) for cache performance tracking.

## Best Practices

### 1. Graph Store Initialization

Always initialize the graph store before creating the agent:

```python
graph_store = InMemoryGraphStore()
await graph_store.initialize()

agent = KnowledgeAwareAgent(..., graph_store=graph_store)
await agent.initialize()
```

### 2. Graceful Degradation

Handle cases where graph store is unavailable:

```python
if graph_store and agent.validate_graph_store():
    # Use graph capabilities
    neighbors = await agent.get_entity_neighbors("alice")
else:
    # Fall back to standard behavior
    pass
```

### 3. Knowledge Formatting

Use mixin methods for consistent formatting:

```python
# Format entities for display
formatted = agent.format_entities(entities)

# Format path for explanation
path_str = agent.format_path(path)
```

### 4. Error Handling

Always handle errors gracefully:

```python
try:
    result = await agent.execute_task(task, context)
except Exception as e:
    logger.error(f"Task execution failed: {e}")
    # Handle error
```

### 5. Resource Cleanup

Always close graph store when done:

```python
try:
    # Use agent
    result = await agent.execute_task(task)
finally:
    await agent.shutdown()
    await graph_store.close()
```

## Performance Considerations

### Knowledge Retrieval

- Retrieval happens before each reasoning step
- Limit retrieval to relevant entities
- Cache retrieved knowledge when possible

### Graph Store Selection

- **InMemoryGraphStore**: Fast but not persistent
- **SQLiteGraphStore**: Persistent but slower
- Choose based on your requirements

### Query Optimization

- Use appropriate search modes
- Limit result sets
- Filter by entity types when possible

## Troubleshooting

### Graph Store Not Available

**Symptom**: Warnings about graph store not available

**Solution**: Ensure graph store is initialized before agent creation

### Knowledge Not Retrieved

**Symptom**: No knowledge retrieved during reasoning

**Solution**: Check that `enable_graph_reasoning=True` and graph store has data

### Tool Not Found

**Symptom**: `graph_search` or `graph_reasoning` tool not available

**Solution**: Ensure graph store is provided to `KnowledgeAwareAgent`

## Next Steps

- See examples in `docs/knowledge_graph/examples/`
- Read tool documentation in `docs/knowledge_graph/tools/`
- Check reasoning engine docs in `docs/knowledge_graph/reasoning/`

