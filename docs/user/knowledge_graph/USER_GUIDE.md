# AIECS Knowledge Graph User Guide

## Introduction

Welcome to the AIECS Knowledge Graph User Guide! This guide will help you get started with building, querying, and reasoning over knowledge graphs in your AI applications.

### What is a Knowledge Graph?

A knowledge graph is a structured representation of knowledge that captures:
- **Entities**: Things in your domain (people, companies, products, concepts)
- **Relations**: Connections between entities (works_for, located_in, knows)
- **Properties**: Attributes of entities and relations (name, age, start_date)

Knowledge graphs enable:
- **Structured Knowledge Storage**: Organize information in a queryable format
- **Multi-Hop Reasoning**: Answer complex questions by traversing relationships
- **Knowledge Fusion**: Merge information from multiple sources
- **Semantic Search**: Find relevant information using meaning, not just keywords

### Why Use AIECS Knowledge Graph?

- **Self-Contained**: No external graph database required
- **Multiple Backends**: InMemory, SQLite, PostgreSQL - choose what fits your needs
- **Easy to Use**: Simple API for common operations
- **Powerful**: Advanced features like reasoning, fusion, and optimization
- **Extensible**: Add custom storage backends easily

## Quick Start

### Installation

AIECS Knowledge Graph is included with AIECS. Install the optional dependencies for specific backends:

```bash
# For SQLite support (included by default)
pip install aiecs

# For PostgreSQL support
pip install aiecs[postgres]

# For all features
pip install aiecs[all]
```

### Your First Knowledge Graph

Let's create a simple knowledge graph about people and companies:

```python
import asyncio
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore

async def main():
    # 1. Initialize storage
    store = InMemoryGraphStore()
    await store.initialize()

    # 2. Create entities
    alice = Entity(
        id="alice",
        entity_type="Person",
        properties={"name": "Alice Smith", "age": 30, "role": "Engineer"}
    )

    bob = Entity(
        id="bob",
        entity_type="Person",
        properties={"name": "Bob Jones", "age": 25, "role": "Designer"}
    )

    tech_corp = Entity(
        id="tech_corp",
        entity_type="Company",
        properties={"name": "Tech Corp", "industry": "Technology"}
    )

    # 3. Add entities to graph
    await store.add_entity(alice)
    await store.add_entity(bob)
    await store.add_entity(tech_corp)

    # 4. Create relations
    alice_works = Relation(
        id="rel_1",
        relation_type="WORKS_FOR",
        source_id="alice",
        target_id="tech_corp",
        properties={"start_date": "2020-01-01"}
    )

    bob_works = Relation(
        id="rel_2",
        relation_type="WORKS_FOR",
        source_id="bob",
        target_id="tech_corp",
        properties={"start_date": "2021-06-01"}
    )

    alice_knows_bob = Relation(
        id="rel_3",
        relation_type="KNOWS",
        source_id="alice",
        target_id="bob"
    )

    # 5. Add relations to graph
    await store.add_relation(alice_works)
    await store.add_relation(bob_works)
    await store.add_relation(alice_knows_bob)

    # 6. Query the graph
    # Get Alice's neighbors
    neighbors = await store.get_neighbors("alice", direction="outgoing")
    print(f"Alice is connected to: {[n.properties['name'] for n in neighbors]}")

    # Find paths from Alice
    paths = await store.traverse("alice", max_depth=2)
    print(f"Found {len(paths)} paths from Alice")

    # 7. Cleanup
    await store.close()

# Run
asyncio.run(main())
```

**Output**:
```
Alice is connected to: ['Bob Jones', 'Tech Corp']
Found 3 paths from Alice
```

Congratulations! You've created your first knowledge graph.

## Core Concepts

### Entities

Entities represent nodes in your knowledge graph. Each entity has:
- **ID**: Unique identifier
- **Type**: Category (Person, Company, Product, etc.)
- **Properties**: Key-value attributes
- **Metadata**: Optional metadata (source, confidence, timestamps)

```python
entity = Entity(
    id="unique_id",
    entity_type="Person",
    properties={
        "name": "Alice",
        "age": 30,
        "email": "alice@example.com"
    },
    metadata={
        "source": "document_1",
        "confidence": 0.95
    }
)
```

### Relations

Relations represent edges connecting entities. Each relation has:
- **ID**: Unique identifier
- **Type**: Relationship type (WORKS_FOR, KNOWS, LOCATED_IN, etc.)
- **Source**: Starting entity ID
- **Target**: Ending entity ID
- **Properties**: Relationship attributes
- **Metadata**: Optional metadata

```python
relation = Relation(
    id="rel_id",
    relation_type="WORKS_FOR",
    source_id="person_1",
    target_id="company_1",
    properties={
        "role": "Engineer",
        "start_date": "2020-01-01"
    }
)
```

### Paths

Paths represent sequences of entities connected by relations:

```python
from aiecs.domain.knowledge_graph.models.path import Path

path = Path(
    entities=[alice, tech_corp, project],
    relations=[works_for_relation, manages_relation],
    score=0.85
)

print(f"Path length: {path.length()} hops")
print(f"Entities: {path.get_entity_ids()}")
```

### Storage Backends

AIECS provides three built-in storage backends:

#### InMemoryGraphStore

**Best for**: Development, testing, small graphs (< 100K nodes)

```python
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore

store = InMemoryGraphStore()
await store.initialize()
```

**Pros**: Very fast, no setup required
**Cons**: Data lost when process ends, limited by RAM

#### SQLiteGraphStore

**Best for**: Production apps, persistent storage, medium graphs (< 1M nodes)

```python
from aiecs.infrastructure.graph_storage.sqlite import SQLiteGraphStore

store = SQLiteGraphStore(db_path="knowledge.db")
await store.initialize()
```

**Pros**: Persistent, no server required, optimized queries
**Cons**: Single-process only, slower than in-memory

#### PostgreSQLGraphStore

**Best for**: Large-scale production, multi-user apps, huge graphs (10M+ nodes)

```python
from aiecs.infrastructure.graph_storage.postgresql import PostgreSQLGraphStore

store = PostgreSQLGraphStore(
    connection_string="postgresql://user:pass@localhost/db"
)
await store.initialize()
```

**Pros**: Scalable, concurrent access, pgvector support
**Cons**: Requires PostgreSQL server

## Common Tasks

### Task 1: Building a Graph from Text

Extract entities and relations from unstructured text:

```python
from aiecs.tools.knowledge_graph import KnowledgeGraphBuilderTool

# Initialize tool
builder = KnowledgeGraphBuilderTool()
await builder._initialize()

# Extract from text
text = """
Alice Smith is a software engineer at Tech Corp in San Francisco.
She has been working there since 2020 and leads the AI team.
Bob Jones, a designer, also works at Tech Corp.
"""

result = await builder.run(
    op="kg_builder",
    action="build_from_text",
    text=text,
    entity_types=["Person", "Company", "Location"]
)

print(f"Extracted {result['entities_added']} entities")
print(f"Extracted {result['relations_added']} relations")
```

### Task 2: Importing CSV Data

Import structured data from CSV files:

```python
from aiecs.application.knowledge_graph.builder.schema_mapping import (
    SchemaMapping,
    EntityMapping,
    RelationMapping
)
from aiecs.application.knowledge_graph.builder.structured_pipeline import (
    StructuredDataPipeline
)

# Define schema mapping
mapping = SchemaMapping(
    entity_mappings=[
        EntityMapping(
            source_columns=["person_id", "name", "age"],
            entity_type="Person",
            property_mapping={
                "id": "person_id",
                "name": "name",
                "age": "age"
            },
            id_column="person_id"
        ),
        EntityMapping(
            source_columns=["company_id", "company_name"],
            entity_type="Company",
            property_mapping={
                "id": "company_id",
                "name": "company_name"
            },
            id_column="company_id"
        )
    ],
    relation_mappings=[
        RelationMapping(
            source_id_column="person_id",
            target_id_column="company_id",
            relation_type="WORKS_FOR",
            property_mapping={
                "role": "role",
                "start_date": "start_date"
            }
        )
    ]
)

# Import CSV
pipeline = StructuredDataPipeline(mapping=mapping, graph_store=store)
result = await pipeline.import_from_csv("employees.csv")

print(f"Imported {result.entities_added} entities")
print(f"Imported {result.relations_added} relations")
```

### Task 3: Searching the Graph

Perform different types of searches:

```python
from aiecs.tools.knowledge_graph import GraphSearchTool

search_tool = GraphSearchTool()
await search_tool._initialize()

# Vector search (semantic similarity)
result = await search_tool.run(
    op="graph_search",
    mode="vector",
    query="machine learning experts",
    top_k=10
)

# Graph traversal search
result = await search_tool.run(
    op="graph_search",
    mode="graph",
    start_entity_id="alice",
    max_depth=3,
    relation_types=["WORKS_FOR", "KNOWS"]
)

# Hybrid search (combines vector + graph)
result = await search_tool.run(
    op="graph_search",
    mode="hybrid",
    query="senior engineers in San Francisco",
    top_k=10,
    enable_reranking=True,
    rerank_strategy="hybrid"
)
```

### Task 4: Multi-Hop Reasoning

Answer complex questions by traversing the graph:

```python
from aiecs.tools.knowledge_graph import GraphReasoningTool

reasoning_tool = GraphReasoningTool()
await reasoning_tool._initialize()

# Multi-hop question answering
result = await reasoning_tool.run(
    op="graph_reasoning",
    mode="multi_hop",
    query="How is Alice connected to Project X?",
    start_entity_id="alice",
    end_entity_id="project_x",
    max_hops=5
)

print(f"Answer: {result['answer']}")
print(f"Reasoning steps: {result['reasoning_steps']}")
print(f"Evidence paths: {len(result['paths'])}")
```

### Task 5: Knowledge Fusion

Merge duplicate entities from multiple sources:

```python
from aiecs.application.knowledge_graph.fusion import KnowledgeFusion

# After importing data from multiple sources
fusion = KnowledgeFusion(
    graph_store=store,
    similarity_threshold=0.85,
    conflict_resolution_strategy="most_complete"
)

# Fuse entities
stats = await fusion.fuse_cross_document_entities(
    entity_types=["Person", "Company"]
)

print(f"Analyzed {stats['entities_analyzed']} entities")
print(f"Merged {stats['entities_merged']} duplicates")
print(f"Resolved {stats['conflicts_resolved']} conflicts")
```

## Schema Management

Define and validate your knowledge graph schema:

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
        ),
        "email": PropertySchema(
            name="email",
            property_type=PropertyType.STRING,
            required=False
        )
    }
)
manager.create_entity_type(person_type)

# Define relation type
works_for_type = RelationType(
    name="WORKS_FOR",
    description="Employment relationship",
    source_entity_types=["Person"],
    target_entity_types=["Company"],
    properties={
        "role": PropertySchema(
            name="role",
            property_type=PropertyType.STRING
        ),
        "start_date": PropertySchema(
            name="start_date",
            property_type=PropertyType.DATE
        )
    }
)
manager.create_relation_type(works_for_type)

# Validate entities
is_valid = manager.validate_entity("Person", {
    "name": "Alice",
    "age": 30,
    "email": "alice@example.com"
})
print(f"Entity valid: {is_valid}")
```

## Best Practices

### 1. Choose the Right Storage Backend

- **Development/Testing**: Use `InMemoryGraphStore` for fast iteration
- **Small Production Apps**: Use `SQLiteGraphStore` for persistence without server
- **Large Production Apps**: Use `PostgreSQLGraphStore` for scale and concurrency

### 2. Define Your Schema

Always define entity and relation types before building your graph:

```python
# Define schema first
manager.create_entity_type(person_type)
manager.create_relation_type(works_for_type)

# Then build graph
await store.add_entity(entity)
```

### 3. Use Meaningful IDs

Use descriptive, stable IDs for entities:

```python
# Good: Stable, meaningful IDs
entity = Entity(id="person_alice_smith", ...)
entity = Entity(id="company_tech_corp", ...)

# Avoid: Random UUIDs unless necessary
entity = Entity(id="a1b2c3d4-...", ...)
```

### 4. Add Metadata

Include source and confidence information:

```python
entity = Entity(
    id="person_1",
    entity_type="Person",
    properties={"name": "Alice"},
    metadata={
        "source": "document_1",
        "confidence": 0.95,
        "extracted_at": "2025-11-15T10:00:00Z"
    }
)
```

### 5. Use Knowledge Fusion

When importing from multiple sources, use fusion to merge duplicates:

```python
# Import from multiple sources
await pipeline.import_from_csv("source1.csv")
await pipeline.import_from_csv("source2.csv")

# Fuse duplicates
fusion = KnowledgeFusion(store, similarity_threshold=0.85)
await fusion.fuse_cross_document_entities()
```

### 6. Enable Reranking for Better Results

Use reranking to improve search quality:

```python
result = await search_tool.run(
    op="graph_search",
    mode="hybrid",
    query="machine learning experts",
    enable_reranking=True,
    rerank_strategy="hybrid"  # Combines multiple signals
)
```

### 7. Optimize Performance

- Use schema caching for repeated queries
- Batch operations when possible
- Choose appropriate max_depth for traversals
- Use filters to reduce result sets

## Next Steps

- **Tutorials**: See [End-to-End Tutorial](./tutorials/END_TO_END_TUTORIAL.md) and [Multi-Hop Reasoning Tutorial](./tutorials/MULTI_HOP_REASONING_TUTORIAL.md) for step-by-step guides
- **Examples**: Check [CSV-to-Graph Tutorial](./examples/csv_to_graph_tutorial.md) and [JSON-to-Graph Tutorial](./examples/json_to_graph_tutorial.md) for working code
- **API Reference**: Read [API_REFERENCE.md](./API_REFERENCE.md) for detailed API docs
- **Performance**: See [PERFORMANCE_GUIDE.md](./PERFORMANCE_GUIDE.md) for optimization tips
- **Troubleshooting**: Check [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for common issues

## Getting Help

- **Documentation**: Browse the [docs/knowledge_graph/](.) directory
- **Examples**: See [CSV-to-Graph Tutorial](./examples/csv_to_graph_tutorial.md) and [JSON-to-Graph Tutorial](./examples/json_to_graph_tutorial.md) for examples
- **Issues**: Report bugs or request features on GitHub

Happy knowledge graphing! 🚀



