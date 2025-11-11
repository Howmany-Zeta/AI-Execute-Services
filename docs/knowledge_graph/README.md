# AIECS Knowledge Graph

**Status**: Phase 1 Complete ✅

AIECS Knowledge Graph provides advanced graph-based knowledge storage, retrieval, and reasoning capabilities for AI applications.

## Features

### Phase 1: Foundation (✅ Complete)

- **Domain Models**: Entity, Relation, Path, Query, Result models with Pydantic validation
- **Schema Management**: Type-safe schema definitions for entities and relations
- **Two-Tier Storage Interface**: Innovative design allowing minimal implementations with full functionality
- **In-Memory Graph Store**: Fast, networkx-based storage for development and testing

### Coming Soon

- **Phase 2**: Knowledge Graph Builder - Document-to-graph extraction
- **Phase 3**: SQLite Storage - File-based persistence
- **Phase 4**: Reasoning Engine - Multi-hop reasoning, logical inference
- **Phase 5**: Agent Integration - HybridAgent with graph capabilities
- **Phase 6**: PostgreSQL Backend - Production-grade storage

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

See [API Documentation](./api.md) for detailed API reference.

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

## Examples

See the [examples directory](./examples/) for complete working examples:

- [Basic Graph Operations](./examples/01_basic_operations.py)
- [Schema Management](./examples/02_schema_management.py)
- [Graph Traversal](./examples/03_traversal.py)
- [Custom Storage Backend](./examples/04_custom_backend.py)

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

## Roadmap

- [x] **Phase 1**: Foundation (Domain models, Schema, Two-tier interface, InMemory store)
- [ ] **Phase 2**: Knowledge Graph Builder (Extract entities/relations from documents)
- [ ] **Phase 3**: SQLite Storage (File-based persistence)
- [ ] **Phase 4**: Reasoning Engine (Multi-hop reasoning, logical inference)
- [ ] **Phase 5**: Agent Integration (HybridAgent with graph capabilities)
- [ ] **Phase 6**: PostgreSQL Backend (Production-grade storage)

## License

MIT License - See [LICENSE](../../LICENSE) for details.

## References

- [OpenSpec Proposal](../../openspec/changes/integrate-openspg-knowledge-graph/)
- [Design Document](../../openspec/changes/integrate-openspg-knowledge-graph/design.md)
- [Extraction Checklist](../../openspec/changes/integrate-openspg-knowledge-graph/EXTRACTION_CHECKLIST.md)

