# Custom Backend Implementation Guide

This guide explains how to implement a custom graph storage backend for AIECS Knowledge Graph, allowing you to use databases like Neo4j, ArangoDB, Amazon Neptune, or any other graph database.

---

## Overview

The AIECS Knowledge Graph uses a **two-tier interface design**:

- **Tier 1 (Basic)**: Must implement - Core CRUD operations
- **Tier 2 (Advanced)**: Has defaults - Complex queries (can optimize)

This design allows you to create a **minimal adapter** that works immediately, then optionally optimize performance by overriding Tier 2 methods.

---

## Quick Start: Minimal Implementation

To create a working custom backend, you only need to implement **7 Tier 1 methods**:

```python
from aiecs.infrastructure.graph_storage.base import GraphStore
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation

class MyCustomGraphStore(GraphStore):
    """Minimal custom backend - only Tier 1 methods"""
    
    async def initialize(self) -> None:
        """Initialize your backend (connect to database, etc.)"""
        pass
    
    async def close(self) -> None:
        """Close connections and cleanup"""
        pass
    
    async def add_entity(self, entity: Entity) -> None:
        """Add entity to your backend"""
        pass
    
    async def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get entity by ID"""
        pass
    
    async def add_relation(self, relation: Relation) -> None:
        """Add relation to your backend"""
        pass
    
    async def get_relation(self, relation_id: str) -> Optional[Relation]:
        """Get relation by ID"""
        pass
    
    async def get_neighbors(
        self,
        entity_id: str,
        direction: str = "both",
        relation_types: Optional[List[str]] = None
    ) -> List[Entity]:
        """Get neighboring entities"""
        pass
```

**That's it!** Once you implement these 7 methods, your backend will work with all AIECS Knowledge Graph features. Tier 2 methods (path finding, traversal, etc.) will automatically use these basic operations.

---

## Tier 1: Basic Interface (Required)

### Method Details

### 1. `initialize() -> None`

Initialize your backend. Called once before use.

**What to do:**
- Create database connections
- Initialize data structures
- Create tables/indexes if needed
- Set up any required configuration

**Example:**
```python
async def initialize(self) -> None:
    """Initialize Neo4j connection"""
    from neo4j import AsyncGraphDatabase
    
    self.driver = AsyncGraphDatabase.driver(
        self.uri,
        auth=(self.user, self.password)
    )
    self._initialized = True
```

### 2. `close() -> None`

Cleanup and close connections. Called when shutting down.

**What to do:**
- Close database connections
- Flush pending writes
- Cleanup resources

**Example:**
```python
async def close(self) -> None:
    """Close Neo4j driver"""
    if self.driver:
        await self.driver.close()
    self._initialized = False
```

### 3. `add_entity(entity: Entity) -> None`

Add an entity to the graph.

**Parameters:**
- `entity`: Entity object with `id`, `entity_type`, `properties`, optional `embedding`

**Requirements:**
- Raise `ValueError` if entity with same ID already exists
- Store entity properties (dict) and embedding (numpy array or None)

**Example:**
```python
async def add_entity(self, entity: Entity) -> None:
    """Add entity to Neo4j"""
    if not self._initialized:
        raise RuntimeError("Store not initialized")
    
    # Check if exists
    async with self.driver.session() as session:
        result = await session.run(
            "MATCH (n {id: $id}) RETURN n",
            id=entity.id
        )
        if await result.single():
            raise ValueError(f"Entity {entity.id} already exists")
        
        # Create node
        await session.run(
            """
            CREATE (n:Entity {
                id: $id,
                entity_type: $type,
                properties: $props
            })
            """,
            id=entity.id,
            type=entity.entity_type,
            props=entity.properties
        )
```

### 4. `get_entity(entity_id: str) -> Optional[Entity]`

Retrieve an entity by ID.

**Parameters:**
- `entity_id`: Entity ID to retrieve

**Returns:**
- `Entity` object if found, `None` otherwise

**Example:**
```python
async def get_entity(self, entity_id: str) -> Optional[Entity]:
    """Get entity from Neo4j"""
    async with self.driver.session() as session:
        result = await session.run(
            "MATCH (n {id: $id}) RETURN n",
            id=entity_id
        )
        record = await result.single()
        if not record:
            return None
        
        node = record["n"]
        return Entity(
            id=node["id"],
            entity_type=node["entity_type"],
            properties=node["properties"]
        )
```

### 5. `add_relation(relation: Relation) -> None`

Add a relation between entities.

**Parameters:**
- `relation`: Relation object with `id`, `source_id`, `target_id`, `relation_type`, `properties`, `weight`

**Requirements:**
- Raise `ValueError` if relation with same ID already exists
- Raise `ValueError` if source or target entity doesn't exist
- Store relation properties and weight

**Example:**
```python
async def add_relation(self, relation: Relation) -> None:
    """Add relation to Neo4j"""
    # Verify entities exist
    source = await self.get_entity(relation.source_id)
    target = await self.get_entity(relation.target_id)
    if not source or not target:
        raise ValueError("Source or target entity not found")
    
    async with self.driver.session() as session:
        await session.run(
            """
            MATCH (a {id: $source}), (b {id: $target})
            CREATE (a)-[r:RELATION {
                id: $id,
                relation_type: $type,
                properties: $props,
                weight: $weight
            }]->(b)
            """,
            source=relation.source_id,
            target=relation.target_id,
            id=relation.id,
            type=relation.relation_type,
            props=relation.properties,
            weight=relation.weight
        )
```

### 6. `get_relation(relation_id: str) -> Optional[Relation]`

Retrieve a relation by ID.

**Parameters:**
- `relation_id`: Relation ID to retrieve

**Returns:**
- `Relation` object if found, `None` otherwise

**Example:**
```python
async def get_relation(self, relation_id: str) -> Optional[Relation]:
    """Get relation from Neo4j"""
    async with self.driver.session() as session:
        result = await session.run(
            "MATCH ()-[r {id: $id}]-() RETURN r, startNode(r) as source, endNode(r) as target",
            id=relation_id
        )
        record = await result.single()
        if not record:
            return None
        
        rel = record["r"]
        return Relation(
            id=rel["id"],
            source_id=record["source"]["id"],
            target_id=record["target"]["id"],
            relation_type=rel["relation_type"],
            properties=rel["properties"],
            weight=rel.get("weight", 1.0)
        )
```

### 7. `get_neighbors(entity_id, relation_type, direction) -> List[Entity]`

Get neighboring entities.

**Parameters:**
- `entity_id`: Entity to get neighbors for
- `relation_type`: Optional single relation type to filter by (can be extended to support list)
- `direction`: `"incoming"`, `"outgoing"`, or `"both"` (default: `"outgoing"`)

**Returns:**
- List of `Entity` objects

**Note**: Some implementations (like PostgresGraphStore) extend this to support `relation_types` (list) instead of `relation_type` (single). The base interface uses `relation_type` for compatibility.

**Example:**
```python
    async def get_neighbors(
        self,
        entity_id: str,
        relation_type: Optional[str] = None,
        direction: str = "outgoing"
    ) -> List[Entity]:
        """Get neighbors from Neo4j"""
        if not self._initialized:
            raise RuntimeError("Store not initialized")
        
        async with self.driver.session() as session:
            if direction == "outgoing":
                query = "MATCH (n {id: $id})-[r]->(m) RETURN m"
            elif direction == "incoming":
                query = "MATCH (n {id: $id})<-[r]-(m) RETURN m"
            else:  # both
                query = "MATCH (n {id: $id})-[r]-(m) RETURN m"
            
            if relation_type:
                query = query.replace("RETURN", "WHERE r.relation_type = $type RETURN")
            
            params = {"id": entity_id}
            if relation_type:
                params["type"] = relation_type
            
            result = await session.run(query, **params)
            entities = []
            async for record in result:
                node = record["m"]
                entities.append(Entity(
                    id=node["id"],
                    entity_type=node["entity_type"],
                    properties=node["properties"]
                ))
            return entities
```

---

## Tier 2: Advanced Interface (Optional Optimizations)

Tier 2 methods have default implementations that use Tier 1 methods. You can override them for better performance using database-specific features.

### Available Tier 2 Methods

1. **`find_paths(source_id, target_id, max_depth, limit)`**
   - Default: Uses BFS with Tier 1 methods
   - Optimize: Use database-specific path finding (e.g., Cypher `shortestPath`, Gremlin `repeat()`)

2. **`traverse(entity_id, max_depth, relation_types, limit)`**
   - Default: Recursive neighbor queries
   - Optimize: Use recursive queries (Cypher `MATCH path = ...`, Gremlin traversal)

3. **`subgraph_query(entity_ids, max_depth)`**
   - Default: Collects entities and relations
   - Optimize: Use subgraph extraction queries

4. **`vector_search(query_vector, limit, threshold)`**
   - Default: Brute-force similarity search
   - Optimize: Use vector indexes (e.g., Neo4j vector search, ArangoDB vector indexes)

5. **`execute_query(query: GraphQuery)`**
   - Default: Decomposes query into Tier 1 operations
   - Optimize: Translate directly to database query language

### Example: Optimized Path Finding

```python
class OptimizedNeo4jGraphStore(Neo4jGraphStore):
    """Neo4j store with optimized Tier 2 methods"""
    
    async def find_paths(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 3,
        limit: Optional[int] = 10
    ) -> List[Path]:
        """Use Cypher shortestPath for efficient path finding"""
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH path = shortestPath(
                    (a {id: $source})-[*1..$max_depth]-(b {id: $target})
                )
                RETURN path
                LIMIT $limit
                """,
                source=source_id,
                target=target_id,
                max_depth=max_depth,
                limit=limit or 10
            )
            
            paths = []
            async for record in result:
                path = record["path"]
                # Convert Cypher path to Path object
                paths.append(self._cypher_path_to_path(path))
            return paths
```

---

## Complete Example: Neo4j Adapter

Here's a complete minimal Neo4j adapter:

```python
"""
Neo4j Graph Store Adapter (Example Implementation)

This is a reference implementation showing how to create a custom backend.
It implements only Tier 1 methods, so Tier 2 methods work automatically.
"""

from typing import List, Optional
from neo4j import AsyncGraphDatabase

from aiecs.infrastructure.graph_storage.base import GraphStore
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation


class Neo4jGraphStore(GraphStore):
    """Neo4j backend adapter (minimal implementation)"""
    
    def __init__(self, uri: str, user: str, password: str):
        """
        Initialize Neo4j adapter
        
        Args:
            uri: Neo4j connection URI (e.g., "bolt://localhost:7687")
            user: Neo4j username
            password: Neo4j password
        """
        super().__init__()
        self.uri = uri
        self.user = user
        self.password = password
        self.driver = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize Neo4j connection"""
        from neo4j import AsyncGraphDatabase
        
        self.driver = AsyncGraphDatabase.driver(
            self.uri,
            auth=(self.user, self.password)
        )
        
        # Verify connection
        async with self.driver.session() as session:
            await session.run("RETURN 1")
        
        self._initialized = True
    
    async def close(self) -> None:
        """Close Neo4j connection"""
        if self.driver:
            await self.driver.close()
        self._initialized = False
    
    async def add_entity(self, entity: Entity) -> None:
        """Add entity to Neo4j"""
        if not self._initialized:
            raise RuntimeError("Store not initialized")
        
        async with self.driver.session() as session:
            # Check if exists
            result = await session.run(
                "MATCH (n {id: $id}) RETURN n",
                id=entity.id
            )
            if await result.single():
                raise ValueError(f"Entity {entity.id} already exists")
            
            # Create node with label from entity_type
            await session.run(
                f"""
                CREATE (n:{entity.entity_type} {{
                    id: $id,
                    entity_type: $type,
                    properties: $props
                }})
                """,
                id=entity.id,
                type=entity.entity_type,
                props=entity.properties
            )
            await session.commit()
    
    async def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get entity from Neo4j"""
        if not self._initialized:
            raise RuntimeError("Store not initialized")
        
        async with self.driver.session() as session:
            result = await session.run(
                "MATCH (n {id: $id}) RETURN n",
                id=entity_id
            )
            record = await result.single()
            if not record:
                return None
            
            node = record["n"]
            return Entity(
                id=node["id"],
                entity_type=node["entity_type"],
                properties=node["properties"]
            )
    
    async def add_relation(self, relation: Relation) -> None:
        """Add relation to Neo4j"""
        if not self._initialized:
            raise RuntimeError("Store not initialized")
        
        # Verify entities exist
        source = await self.get_entity(relation.source_id)
        target = await self.get_entity(relation.target_id)
        if not source or not target:
            raise ValueError("Source or target entity not found")
        
        async with self.driver.session() as session:
            await session.run(
                f"""
                MATCH (a {{id: $source}}), (b {{id: $target}})
                CREATE (a)-[r:{relation.relation_type} {{
                    id: $id,
                    relation_type: $type,
                    properties: $props,
                    weight: $weight
                }}]->(b)
                """,
                source=relation.source_id,
                target=relation.target_id,
                id=relation.id,
                type=relation.relation_type,
                props=relation.properties,
                weight=relation.weight
            )
            await session.commit()
    
    async def get_relation(self, relation_id: str) -> Optional[Relation]:
        """Get relation from Neo4j"""
        if not self._initialized:
            raise RuntimeError("Store not initialized")
        
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH ()-[r {id: $id}]-()
                RETURN r, 
                       startNode(r).id as source_id,
                       endNode(r).id as target_id
                """,
                id=relation_id
            )
            record = await result.single()
            if not record:
                return None
            
            rel = record["r"]
            return Relation(
                id=rel["id"],
                source_id=record["source_id"],
                target_id=record["target_id"],
                relation_type=rel["relation_type"],
                properties=rel["properties"],
                weight=rel.get("weight", 1.0)
            )
    
    async def get_neighbors(
        self,
        entity_id: str,
        relation_type: Optional[str] = None,
        direction: str = "outgoing"
    ) -> List[Entity]:
        """Get neighbors from Neo4j"""
        if not self._initialized:
            raise RuntimeError("Store not initialized")
        
        async with self.driver.session(database=self.database) as session:
            if direction == "outgoing":
                query = "MATCH (n {id: $id})-[r]->(m) RETURN DISTINCT m"
            elif direction == "incoming":
                query = "MATCH (n {id: $id})<-[r]-(m) RETURN DISTINCT m"
            else:  # both
                query = "MATCH (n {id: $id})-[r]-(m) RETURN DISTINCT m"
            
            if relation_type:
                query = query.replace("RETURN", "WHERE r.relation_type = $type RETURN")
            
            params = {"id": entity_id}
            if relation_type:
                params["type"] = relation_type
            
            result = await session.run(query, **params)
            entities = []
            async for record in result:
                node = record["m"]
                entities.append(Entity(
                    id=node["id"],
                    entity_type=node["entity_type"],
                    properties=node["properties"]
                ))
            return entities
```

**Usage:**
```python
# Create and use Neo4j backend
store = Neo4jGraphStore(
    uri="bolt://localhost:7687",
    user="neo4j",
    password="password"
)
await store.initialize()

# Works with all AIECS features!
entity = Entity(id="e1", entity_type="Person", properties={"name": "Alice"})
await store.add_entity(entity)

# Tier 2 methods work automatically
paths = await store.find_paths("e1", "e2", max_depth=3)
```

---

## Testing Your Adapter

### Basic Testing

Create tests to verify your Tier 1 implementation:

```python
import pytest
from your_backend import YourGraphStore

@pytest.mark.asyncio
async def test_basic_operations():
    """Test basic CRUD operations"""
    store = YourGraphStore(...)
    await store.initialize()
    
    # Test add/get entity
    entity = Entity(id="test", entity_type="Test", properties={})
    await store.add_entity(entity)
    retrieved = await store.get_entity("test")
    assert retrieved is not None
    
    await store.close()
```

### Compatibility Testing

Use the compatibility test suite to verify your adapter works with the application layer:

```python
from test.integration_tests.graph_storage.test_backend_compatibility import (
    application_add_person,
    application_find_friends,
    # ... other application functions
)

@pytest.mark.asyncio
async def test_application_compatibility():
    """Test that application layer works with your backend"""
    store = YourGraphStore(...)
    await store.initialize()
    
    # Application layer code should work without changes
    await application_add_person(store, "p1", "Alice", 30)
    friends = await application_find_friends(store, "p1")
    
    assert len(friends) >= 0  # Should work regardless of backend
```

### Performance Testing

Test Tier 2 optimizations:

```python
@pytest.mark.asyncio
async def test_path_finding_performance():
    """Test optimized path finding"""
    store = YourGraphStore(...)
    await store.initialize()
    
    # Create test graph
    # ... add entities and relations
    
    import time
    start = time.time()
    paths = await store.find_paths("source", "target", max_depth=5)
    elapsed = time.time() - start
    
    assert len(paths) > 0
    assert elapsed < 1.0  # Should be fast with optimization
```

---

## Best Practices

### 1. Error Handling

Always raise appropriate exceptions:

```python
async def add_entity(self, entity: Entity) -> None:
    if not self._initialized:
        raise RuntimeError("Store not initialized")
    
    if entity.id in existing_ids:
        raise ValueError(f"Entity {entity.id} already exists")
```

### 2. Transaction Support (Optional)

If your backend supports transactions, implement the `transaction()` context manager:

```python
@asynccontextmanager
async def transaction(self):
    """Transaction context manager"""
    async with self.driver.session() as session:
        async with session.begin_transaction() as tx:
            yield tx
            await tx.commit()
```

### 3. Connection Pooling

Use connection pooling for better performance:

```python
def __init__(self, ...):
    self.pool = ConnectionPool(...)

async def get_neighbors(self, ...):
    async with self.pool.acquire() as conn:
        # Use connection
        pass
```

### 4. Batch Operations

Implement batch operations for better performance:

```python
async def add_entities_batch(self, entities: List[Entity]) -> None:
    """Add multiple entities efficiently"""
    # Use batch insert if available
    pass
```

---

## Migration from Other Backends

If you're migrating from an existing backend:

1. **Implement Tier 1 methods** first
2. **Test basic operations** work
3. **Run compatibility tests** to verify
4. **Optimize Tier 2 methods** for performance
5. **Migrate data** using migration tools

---

## Additional Resources

- **Base Interface**: `aiecs.infrastructure.graph_storage.base.GraphStore`
- **Reference Implementations**:
  - `InMemoryGraphStore` - Simple in-memory implementation
  - `SQLiteGraphStore` - File-based SQL implementation
  - `PostgresGraphStore` - Production PostgreSQL implementation
- **Examples**: See `docs/knowledge_graph/examples/`

---

## Summary

Creating a custom backend is straightforward:

1. ✅ Implement **7 Tier 1 methods** (minimal requirement)
2. ✅ Your backend works with all AIECS features immediately
3. ⚡ Optionally optimize **Tier 2 methods** for better performance
4. ✅ Test using compatibility test suite

**The two-tier design means you can start simple and optimize later!**

