# AIECS Knowledge Graph

**Status**: Enhanced Capabilities Complete ✅

AIECS Knowledge Graph provides advanced graph-based knowledge storage, retrieval, reasoning, and fusion capabilities for AI applications.

## Features

### Core Capabilities (✅ Complete)

- **Domain Models**: Entity, Relation, Path, Query, Result models with Pydantic validation
- **Schema Management**: Type-safe schema definitions with caching for improved performance
- **Storage Backends**: In-Memory, SQLite, and PostgreSQL support
- **Structured Data Import**: Import CSV and JSON data with schema mapping (100-300 rows/second)
- **Text Similarity Utilities**: BM25, Jaccard, Cosine similarity, Levenshtein distance, fuzzy matching

### New Enhanced Features (✅ Complete)

- **Runnable Pattern**: Composable graph operations with async/sync compatibility
- **Knowledge Fusion**: Cross-document entity merging with conflict resolution (5 strategies)
- **Result Reranking**: Improve search relevance with 4 reranking strategies (text, semantic, structural, hybrid)
- **Logical Query Parsing**: Convert natural language to structured logical queries
- **Schema Caching**: 3-5x performance improvement with 70-95% hit rate
- **Query Optimization**: 40-70% faster query execution with cost-based optimization
- **Performance Benchmarks**: Comprehensive benchmarks and optimization guides

### Storage Backends

- **In-Memory**: Fast, networkx-based storage for development (100K+ nodes)
- **SQLite**: File-based persistence for single-user applications (1M+ nodes)
- **PostgreSQL**: Production-grade storage with pgvector support (10M+ nodes)

## Quick Start

### Basic Usage

```python
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore

# Initialize store
store = InMemoryGraphStore()
await store.initialize()

# Add entities
alice = Entity(
    id="alice",
    entity_type="Person",
    properties={"name": "Alice", "age": 30}
)
await store.add_entity(alice)

bob = Entity(id="bob", entity_type="Person", properties={"name": "Bob"})
await store.add_entity(bob)

# Add relation
knows = Relation(
    id="r1",
    relation_type="KNOWS",
    source_id="alice",
    target_id="bob"
)
await store.add_relation(knows)

# Query neighbors (Tier 1 method)
neighbors = await store.get_neighbors("alice", direction="outgoing")
print(f"Alice knows: {[n.properties['name'] for n in neighbors]}")

# Graph traversal (Tier 2 method - works automatically!)
paths = await store.traverse("alice", max_depth=3)
print(f"Found {len(paths)} paths")

# Cleanup
await store.close()
```

### Schema Management

```python
from aiecs.domain.knowledge_graph.schema import (
    SchemaManager,
    EntityType,
    RelationType,
    PropertySchema,
    PropertyType
)

# Create schema manager
manager = SchemaManager()

# Define entity type
person_type = EntityType(
    name="Person",
    description="A person entity",
    properties={
        "name": PropertySchema(
            name="name",
            property_type=PropertyType.STRING,
            required=True
        ),
        "age": PropertySchema(
            name="age",
            property_type=PropertyType.INTEGER,
            min_value=0,
            max_value=150
        )
    }
)
manager.create_entity_type(person_type)

# Define relation type
knows_type = RelationType(
    name="KNOWS",
    description="Person knows another person",
    source_entity_types=["Person"],
    target_entity_types=["Person"]
)
manager.create_relation_type(knows_type)

# Validate entity
is_valid = manager.validate_entity("Person", {"name": "Alice", "age": 30})
```

## Architecture

### Two-Tier Storage Interface

AIECS's knowledge graph uses an innovative two-tier interface design:

**Tier 1 - Basic Interface (MUST IMPLEMENT)**:
- `add_entity()`, `get_entity()`
- `add_relation()`, `get_relation()`
- `get_neighbors()`
- `initialize()`, `close()`

**Tier 2 - Advanced Interface (HAS DEFAULTS)**:
- `traverse()` - Multi-hop graph traversal
- `find_paths()` - Path finding between entities
- `subgraph_query()` - Extract subgraphs
- `vector_search()` - Semantic search
- `execute_query()` - Generic query execution

### Why This Matters

1. **Minimal Implementation**: Implement just 7 Tier 1 methods, get all Tier 2 methods for free
2. **Gradual Optimization**: Start with defaults, optimize later for your specific backend
3. **Storage Agnostic**: Application code works with any storage backend
4. **Custom Adapters**: Easy to integrate Neo4j, ArangoDB, or any graph database

Example:

```python
class CustomGraphStore(GraphStore):
    # Implement only Tier 1 methods
    async def add_entity(self, entity): ...
    async def get_entity(self, entity_id): ...
    async def add_relation(self, relation): ...
    async def get_relation(self, relation_id): ...
    async def get_neighbors(self, entity_id, ...): ...
    async def initialize(self): ...
    async def close(self): ...
    
    # Tier 2 methods work automatically!
    # traverse(), find_paths(), etc. all work via defaults

# Later, optimize for your backend:
class OptimizedGraphStore(CustomGraphStore):
    async def traverse(self, ...):
        # Use database-specific optimization
        return await self._use_recursive_cte()
```

## API Reference

See [API Reference](./API_REFERENCE.md) for detailed API reference.

## Testing

All Phase 1 components have comprehensive test coverage:

```bash
# Run all knowledge graph tests
poetry run pytest test/unit_tests/knowledge_graph/ -v
poetry run pytest test/integration_tests/knowledge_graph/ -v

# Run with coverage
poetry run pytest test/unit_tests/knowledge_graph/ test/integration_tests/knowledge_graph/ --cov=aiecs.domain.knowledge_graph --cov=aiecs.infrastructure.graph_storage --cov-report=html
```

Test Results (Phase 1):
- ✅ 13 domain model tests
- ✅ 16 schema management tests
- ✅ 15 InMemoryGraphStore integration tests
- **Total: 44 tests, all passing**

## Documentation

### Getting Started
- **[User Guide](./USER_GUIDE.md)** - Comprehensive user guide with examples
- **[Quick Start](#quick-start)** - Get started in 5 minutes
- **[Migration Guide](../../developer/knowledge_graph/MIGRATION_GUIDE.md)** - Integrate knowledge graphs into existing apps

### Reference Documentation
- **[API Reference](./API_REFERENCE.md)** - Complete API documentation
- **[Configuration Guide](./CONFIGURATION_GUIDE.md)** - Configuration options and examples
- **[Performance Guide](./PERFORMANCE_GUIDE.md)** - Performance optimization tips
- **[Troubleshooting](./TROUBLESHOOTING.md)** - Common issues and solutions

### Developer Resources
- **[Developer Guide](../../developer/knowledge_graph/DEVELOPER_GUIDE.md)** - Extend knowledge graph components
- **Backend Development** - Custom backend development
  - [Custom Backend Guide](../../developer/knowledge_graph/backend/CUSTOM_BACKEND_GUIDE.md)
  - [SQLite Backend](../../developer/knowledge_graph/storage/SQLITE_BACKEND.md)
- **[Reasoning Guides](./reasoning/REASONING_ENGINE.md)** - Advanced reasoning features
  - [Reasoning Engine](./reasoning/REASONING_ENGINE.md)
  - [Logic Query Parser](./reasoning/logic_query_parser.md)
  - [Reranking Strategies Guide](./reasoning/reranking-strategies-guide.md)
  - [Schema Caching Guide](./reasoning/schema-caching-guide.md)

### Tutorials
- **[End-to-End Tutorial](./tutorials/END_TO_END_TUTORIAL.md)** - Complete workflow
- **[Domain-Specific Tutorial](./tutorials/DOMAIN_SPECIFIC_TUTORIAL.md)** - Build a medical knowledge graph
- **[Multi-Hop Reasoning Tutorial](./tutorials/MULTI_HOP_REASONING_TUTORIAL.md)** - Complex question answering
- **[CSV-to-Graph Tutorial](./examples/csv_to_graph_tutorial.md)** - Import structured data

### Deployment
- **[Production Deployment](./deployment/PRODUCTION_DEPLOYMENT.md)** - Production best practices
- **[Security Guide](./deployment/SECURITY.md)** - Security considerations

## Examples

See [CSV-to-Graph Tutorial](./examples/csv_to_graph_tutorial.md) and [JSON-to-Graph Tutorial](./examples/json_to_graph_tutorial.md) for complete working examples and step-by-step guides.

## Structured Data Import

Import CSV and JSON data into knowledge graphs:

- **[Schema Mapping Guide](./SCHEMA_MAPPING_GUIDE.md)**: Complete guide to configuring schema mappings
- **[StructuredDataPipeline Guide](./STRUCTURED_DATA_PIPELINE.md)**: Usage guide for importing structured data
- **[CSV-to-Graph Tutorial](./examples/csv_to_graph_tutorial.md)**: Step-by-step CSV import tutorial
- **[JSON-to-Graph Tutorial](./examples/json_to_graph_tutorial.md)**: Step-by-step JSON import tutorial

### Quick Example

```python
from aiecs.application.knowledge_graph.builder.schema_mapping import (
    SchemaMapping,
    EntityMapping
)
from aiecs.application.knowledge_graph.builder.structured_pipeline import StructuredDataPipeline
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore

# Define mapping
mapping = SchemaMapping(
    entity_mappings=[
        EntityMapping(
            source_columns=["id", "name"],
            entity_type="Person",
            property_mapping={"id": "id", "name": "name"},
            id_column="id"
        )
    ]
)

# Import CSV
store = InMemoryGraphStore()
await store.initialize()
pipeline = StructuredDataPipeline(mapping=mapping, graph_store=store)
result = await pipeline.import_from_csv("data.csv")
print(f"Added {result.entities_added} entities")
```

## Development

### Project Structure

```
aiecs/
├── domain/knowledge_graph/          # Domain models and business logic
│   ├── models/                      # Entity, Relation, Path, Query models
│   └── schema/                      # Schema management
├── infrastructure/graph_storage/    # Storage implementations
│   ├── base.py                      # Two-tier GraphStore interface
│   └── in_memory.py                 # InMemory implementation
├── application/knowledge_graph/     # Application services (Phase 2+)
└── tools/knowledge_graph/           # Agent tools (Phase 2+)

test/
├── unit_tests/knowledge_graph/      # Unit tests
└── integration_tests/knowledge_graph/ # Integration tests
```

### Contributing

When implementing new storage backends:

1. Inherit from `GraphStore`
2. Implement all Tier 1 methods (7 methods)
3. Test that Tier 2 methods work automatically
4. Optionally optimize Tier 2 methods for your backend
5. Add integration tests

## New Features Quick Start

### Structured Data Import

```python
from aiecs.tools.knowledge_graph import KnowledgeGraphBuilderTool

builder = KnowledgeGraphBuilderTool()
await builder._initialize()

# Import CSV with schema mapping
result = await builder.run(
    op="kg_builder",
    action="build_from_structured_data",
    data_path="employees.csv",
    schema_mapping={
        "entity_mappings": [{
            "entity_type": "Person",
            "id_column": "person_id",
            "property_mappings": {"name": "full_name"}
        }]
    }
)
```

### Search with Reranking

```python
from aiecs.tools.knowledge_graph import GraphSearchTool

tool = GraphSearchTool()
result = await tool.run(
    op="graph_search",
    mode="hybrid",
    query="machine learning experts",
    enable_reranking=True,
    rerank_strategy="hybrid"
)
```

### Knowledge Fusion

```python
from aiecs.application.knowledge_graph.fusion import KnowledgeFusion

fusion = KnowledgeFusion(store, similarity_threshold=0.85)
stats = await fusion.fuse_cross_document_entities()
```

## Documentation

### Getting Started
- [Configuration Guide](./CONFIGURATION_GUIDE.md)
- [Performance Guide](./PERFORMANCE_GUIDE.md)
- [Runnable Pattern](./RUNNABLE_PATTERN.md)

### Data Import
- [Structured Data Pipeline](./STRUCTURED_DATA_PIPELINE.md)
- [Schema Mapping Guide](./SCHEMA_MAPPING_GUIDE.md)
- [CSV Tutorial](./examples/csv_to_graph_tutorial.md)
- [JSON Tutorial](./examples/json_to_graph_tutorial.md)

### Search and Reasoning
- [Result Reranker API](./reasoning/result-reranker-api.md)
- [Schema Caching Guide](./reasoning/schema-caching-guide.md)
- [Logic Query Parser](./reasoning/logic_query_parser.md)

### Tools
- [Graph Builder Tool](./tools/GRAPH_BUILDER_TOOL.md)
- [Graph Search Tool](./tools/GRAPH_SEARCH_TOOL.md)
- [Graph Reasoning Tool](./tools/GRAPH_REASONING_TOOL.md)

### Deployment
- [Production Deployment](./deployment/PRODUCTION_DEPLOYMENT.md)
- [Security Guide](./deployment/SECURITY.md)

## Performance

- **CSV Import**: 100-300 rows/second
- **Reranking**: 50-300ms latency
- **Schema Cache**: 70-95% hit rate, 3-5x speedup
- **Query Optimization**: 40-70% faster

See [Performance Guide](./PERFORMANCE_GUIDE.md) for details.

## Roadmap

- [x] **Phase 1**: Foundation (Domain models, Schema, Two-tier interface, InMemory store)
- [x] **Phase 2**: Knowledge Graph Builder (Extract entities/relations from documents)
- [x] **Phase 3**: Storage Backends (SQLite, PostgreSQL with pgvector)
- [x] **Phase 4**: Enhanced Capabilities (Runnable pattern, Knowledge fusion, Reranking, Query optimization)
- [x] **Phase 5**: Testing & Documentation (111+ unit tests, 67 integration tests, comprehensive docs)
- [ ] **Phase 6**: Advanced Features (Visualization, Advanced reasoning, Real-time updates)

## License

MIT License - See the project root LICENSE file for details.

