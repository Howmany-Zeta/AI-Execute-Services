# Knowledge Graph Migration Guide

## Overview

This guide helps you integrate AIECS Knowledge Graph capabilities into your existing AIECS applications. Whether you're adding knowledge graphs to an existing agent, migrating from another graph system, or upgrading between versions, this guide covers the migration path.

## For New Users

If you're adding knowledge graph capabilities to an existing AIECS application for the first time:

### Step 1: Install Dependencies

Knowledge graph features are included in AIECS core. For specific backends:

```bash
# For SQLite support (included by default)
pip install aiecs

# For PostgreSQL support
pip install aiecs[postgres]

# Or install all optional dependencies
pip install aiecs[all]
```

### Step 2: Choose a Storage Backend

Select the appropriate backend for your use case:

| Backend | Use Case | Installation |
|---------|----------|--------------|
| InMemoryGraphStore | Development, testing, small graphs | Included |
| SQLiteGraphStore | Production, persistent storage, medium graphs | Included |
| PostgreSQLGraphStore | Large-scale production, multi-user | `pip install aiecs[postgres]` |

### Step 3: Initialize Graph Store

Add graph store initialization to your application:

```python
# Before (existing AIECS app)
from aiecs.domain.agent.agents.hybrid_agent import HybridAgent

agent = HybridAgent(
    llm_client=llm_client,
    tools=tools
)

# After (with knowledge graph)
from aiecs.domain.agent.agents.hybrid_agent import HybridAgent
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore

# Initialize graph store
graph_store = InMemoryGraphStore()
await graph_store.initialize()

# Create agent with graph capabilities
agent = HybridAgent(
    llm_client=llm_client,
    tools=tools,
    graph_store=graph_store  # Add graph store
)
```

### Step 4: Add Knowledge Graph Tools

Register knowledge graph tools with your agent:

```python
from aiecs.tools.knowledge_graph import (
    KnowledgeGraphBuilderTool,
    GraphSearchTool,
    GraphReasoningTool
)

# Initialize tools
builder_tool = KnowledgeGraphBuilderTool(graph_store=graph_store)
search_tool = GraphSearchTool(graph_store=graph_store)
reasoning_tool = GraphReasoningTool(graph_store=graph_store)

await builder_tool._initialize()
await search_tool._initialize()
await reasoning_tool._initialize()

# Add to agent's tool list
agent.tools.extend([builder_tool, search_tool, reasoning_tool])
```

### Step 5: Use Graph Memory (Optional)

Integrate graph-based memory into your context engine:

```python
from aiecs.domain.context.graph_memory import ContextEngineWithGraph

# Before
context_engine = ContextEngine()

# After
context_engine = ContextEngineWithGraph(graph_store=graph_store)
await context_engine.initialize()
```

## Migrating from Other Graph Systems

### From Neo4j

If you're migrating from Neo4j, you can:

1. **Option A**: Create a Neo4j adapter (see [Custom Backend Guide](./backend/CUSTOM_BACKEND_GUIDE.md))
2. **Option B**: Export from Neo4j and import to AIECS

**Export from Neo4j**:

```cypher
// Export entities
MATCH (n)
RETURN n.id AS id, labels(n)[0] AS type, properties(n) AS properties

// Export relations
MATCH (a)-[r]->(b)
RETURN a.id AS source_id, b.id AS target_id, type(r) AS relation_type, properties(r) AS properties
```

**Import to AIECS**:

```python
import csv
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation

# Import entities
with open('entities.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        entity = Entity(
            id=row['id'],
            entity_type=row['type'],
            properties=eval(row['properties'])  # Parse properties
        )
        await graph_store.add_entity(entity)

# Import relations
with open('relations.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        relation = Relation(
            id=f"rel_{row['source_id']}_{row['target_id']}",
            relation_type=row['relation_type'],
            source_id=row['source_id'],


### From RDF/Triple Stores

If you're migrating from RDF triple stores (e.g., Apache Jena, Virtuoso):

```python
from rdflib import Graph as RDFGraph
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation

# Load RDF data
rdf_graph = RDFGraph()
rdf_graph.parse("data.ttl", format="turtle")

# Convert subjects and objects to entities
entities = {}
for s, p, o in rdf_graph:
    # Add subject as entity
    if str(s) not in entities:
        entities[str(s)] = Entity(
            id=str(s),
            entity_type="Resource",
            properties={"uri": str(s)}
        )

    # Add object as entity if it's a URI
    if isinstance(o, URIRef) and str(o) not in entities:
        entities[str(o)] = Entity(
            id=str(o),
            entity_type="Resource",
            properties={"uri": str(o)}
        )

# Add entities to graph store
for entity in entities.values():
    await graph_store.add_entity(entity)

# Convert predicates to relations
for s, p, o in rdf_graph:
    if isinstance(o, URIRef):  # Only create relations for URI objects
        relation = Relation(
            id=f"rel_{hash((str(s), str(p), str(o)))}",
            relation_type=str(p).split('/')[-1],  # Use predicate name
            source_id=str(s),
            target_id=str(o)
        )
        await graph_store.add_relation(relation)
```

## Upgrading Storage Backends

### From InMemory to SQLite

When your graph grows beyond memory limits:

```python
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore
from aiecs.infrastructure.graph_storage.sqlite import SQLiteGraphStore

# Step 1: Export from InMemory
old_store = InMemoryGraphStore()
await old_store.initialize()
# ... (your existing data)

# Get all entities and relations
all_entities = []
all_relations = []

# Assuming you have a way to iterate (implementation-specific)
# For InMemory, you can access the internal graph
for entity_id in old_store._entities.keys():
    entity = await old_store.get_entity(entity_id)
    all_entities.append(entity)

for relation_id in old_store._relations.keys():
    relation = await old_store.get_relation(relation_id)
    all_relations.append(relation)

# Step 2: Import to SQLite
new_store = SQLiteGraphStore(db_path="knowledge.db")
await new_store.initialize()

for entity in all_entities:
    await new_store.add_entity(entity)

for relation in all_relations:
    await new_store.add_relation(relation)

# Step 3: Update your application to use new store
# Replace old_store with new_store in your code
await old_store.close()
```

### From SQLite to PostgreSQL

When you need multi-user access and better performance:

```python
from aiecs.infrastructure.graph_storage.sqlite import SQLiteGraphStore
from aiecs.infrastructure.graph_storage.postgresql import PostgreSQLGraphStore

# Step 1: Connect to both stores
sqlite_store = SQLiteGraphStore(db_path="knowledge.db")
await sqlite_store.initialize()

pg_store = PostgreSQLGraphStore(
    connection_string="postgresql://user:pass@localhost/db"
)
await pg_store.initialize()

# Step 2: Batch export/import for efficiency
batch_size = 1000

# Export entities in batches
# (Implementation depends on your SQLite store's query capabilities)
offset = 0
while True:
    # Get batch of entities
    entities = await sqlite_store.get_entities_batch(offset, batch_size)
    if not entities:
        break

    # Import to PostgreSQL
    for entity in entities:
        await pg_store.add_entity(entity)

    offset += batch_size
    print(f"Migrated {offset} entities...")

# Export relations in batches
offset = 0
while True:
    relations = await sqlite_store.get_relations_batch(offset, batch_size)
    if not relations:
        break

    for relation in relations:
        await pg_store.add_relation(relation)

    offset += batch_size
    print(f"Migrated {offset} relations...")

# Step 3: Update configuration
# Update your app config to use PostgreSQL connection string
await sqlite_store.close()
```

## Configuration Migration

### Environment Variables

Update your environment configuration:

```bash
# Before (no knowledge graph)
AIECS_LLM_PROVIDER=openai
AIECS_LLM_MODEL=gpt-4

# After (with knowledge graph)
AIECS_LLM_PROVIDER=openai
AIECS_LLM_MODEL=gpt-4

# Knowledge Graph Configuration
AIECS_KG_BACKEND=postgresql  # or sqlite, inmemory
AIECS_KG_CONNECTION_STRING=postgresql://user:pass@localhost/aiecs_kg
AIECS_KG_POOL_SIZE=10
AIECS_KG_ENABLE_CACHING=true
```

### Configuration File

Update your `config.yaml` or `config.json`:

```yaml
# Before
llm:
  provider: openai
  model: gpt-4

# After
llm:
  provider: openai
  model: gpt-4

knowledge_graph:
  backend: postgresql
  connection_string: postgresql://user:pass@localhost/aiecs_kg
  pool_size: 10
  enable_caching: true
  cache_ttl_seconds: 3600
```

## Breaking Changes

### Version Compatibility

The knowledge graph feature is additive and doesn't break existing AIECS functionality. However, be aware of:

1. **New Dependencies**: PostgreSQL backend requires `asyncpg`
2. **Configuration**: New configuration options for graph storage
3. **Tools**: New tools need to be registered if you want agents to use them

### API Changes

No breaking changes to existing AIECS APIs. Knowledge graph is opt-in.

## Testing Your Migration

### Validation Checklist

After migration, verify:

- [ ] All entities migrated correctly
- [ ] All relations migrated correctly
- [ ] Entity properties preserved
- [ ] Relation properties preserved
- [ ] Graph traversal works
- [ ] Search functionality works
- [ ] Performance is acceptable

### Validation Script

```python
async def validate_migration(old_store, new_store):
    """Validate that migration was successful"""

    # Count entities
    old_entity_count = await old_store.count_entities()
    new_entity_count = await new_store.count_entities()
    assert old_entity_count == new_entity_count, "Entity count mismatch"

    # Count relations
    old_relation_count = await old_store.count_relations()
    new_relation_count = await new_store.count_relations()
    assert old_relation_count == new_relation_count, "Relation count mismatch"

    # Sample entity verification
    sample_entity_id = "sample_id"
    old_entity = await old_store.get_entity(sample_entity_id)
    new_entity = await new_store.get_entity(sample_entity_id)
    assert old_entity.properties == new_entity.properties, "Entity properties mismatch"

    # Sample traversal verification
    old_paths = await old_store.traverse(sample_entity_id, max_depth=2)
    new_paths = await new_store.traverse(sample_entity_id, max_depth=2)
    assert len(old_paths) == len(new_paths), "Traversal results mismatch"

    print("✅ Migration validation passed!")
```

## Rollback Plan

If you need to rollback:

### Backup Before Migration

```python
import json
from datetime import datetime

async def backup_graph_store(store, backup_path):
    """Create a backup of the graph store"""

    backup_data = {
        "timestamp": datetime.now().isoformat(),
        "entities": [],
        "relations": []
    }

    # Export all entities
    # (Implementation depends on your store)
    for entity_id in await store.get_all_entity_ids():
        entity = await store.get_entity(entity_id)
        backup_data["entities"].append({
            "id": entity.id,
            "entity_type": entity.entity_type,
            "properties": entity.properties,
            "metadata": entity.metadata
        })

    # Export all relations
    for relation_id in await store.get_all_relation_ids():
        relation = await store.get_relation(relation_id)
        backup_data["relations"].append({
            "id": relation.id,
            "relation_type": relation.relation_type,
            "source_id": relation.source_id,
            "target_id": relation.target_id,
            "properties": relation.properties,
            "metadata": relation.metadata
        })

    # Save to file
    with open(backup_path, 'w') as f:
        json.dump(backup_data, f, indent=2)

    print(f"✅ Backup saved to {backup_path}")
```

### Restore from Backup

```python
async def restore_from_backup(store, backup_path):
    """Restore graph store from backup"""

    with open(backup_path, 'r') as f:
        backup_data = json.load(f)

    # Restore entities
    for entity_data in backup_data["entities"]:
        entity = Entity(**entity_data)
        await store.add_entity(entity)

    # Restore relations
    for relation_data in backup_data["relations"]:
        relation = Relation(**relation_data)
        await store.add_relation(relation)

    print(f"✅ Restored from {backup_path}")
```

## Performance Considerations

### Batch Operations

For large migrations, use batch operations:

```python
async def batch_migrate(source_store, target_store, batch_size=1000):
    """Migrate in batches for better performance"""

    # Use transactions if supported
    async with target_store.transaction():
        offset = 0
        while True:
            entities = await source_store.get_entities_batch(offset, batch_size)
            if not entities:
                break

            # Batch insert
            await target_store.add_entities_batch(entities)
            offset += batch_size

            if offset % 10000 == 0:
                print(f"Migrated {offset} entities...")
```

### Indexing

After migration, rebuild indexes:

```python
# For SQLite
await sqlite_store.rebuild_indexes()

# For PostgreSQL
await pg_store.rebuild_indexes()
await pg_store.analyze_tables()  # Update statistics
```

## Getting Help

- **Documentation**: See [README.md](./README.md) for overview
- **Examples**: Check [examples/](./examples/) for migration examples
- **Troubleshooting**: See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
- **Issues**: Report migration issues on GitHub

## Next Steps

After successful migration:

1. **Test thoroughly**: Run your test suite
2. **Monitor performance**: Check query performance
3. **Optimize**: Use caching and query optimization features
4. **Document**: Update your application documentation

Happy migrating! 🚀


### From NetworkX

If you have existing NetworkX graphs:

```python
import networkx as nx
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation

# Your existing NetworkX graph
G = nx.Graph()
# ... (your graph data)

# Convert to AIECS
for node_id, node_data in G.nodes(data=True):
    entity = Entity(
        id=str(node_id),
        entity_type=node_data.get('type', 'Unknown'),
        properties=node_data
    )
    await graph_store.add_entity(entity)

for source, target, edge_data in G.edges(data=True):
    relation = Relation(
        id=f"rel_{source}_{target}",
        relation_type=edge_data.get('type', 'CONNECTED_TO'),
        source_id=str(source),
        target_id=str(target),
        properties=edge_data
    )
    await graph_store.add_relation(relation)
```


