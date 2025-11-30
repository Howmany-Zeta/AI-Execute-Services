# Adapter Testing Guide

This guide explains how to test your custom graph storage backend adapter to ensure it works correctly with AIECS Knowledge Graph.

---

## Testing Strategy

### 1. Unit Tests (Tier 1 Methods)

Test each Tier 1 method individually:

```python
import pytest
from your_backend import YourGraphStore
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation

@pytest.mark.asyncio
async def test_initialize_and_close():
    """Test initialization and cleanup"""
    store = YourGraphStore(...)
    await store.initialize()
    assert store._initialized is True
    
    await store.close()
    assert store._initialized is False

@pytest.mark.asyncio
async def test_add_and_get_entity():
    """Test entity CRUD operations"""
    store = YourGraphStore(...)
    await store.initialize()
    
    # Add entity
    entity = Entity(
        id="test_entity",
        entity_type="Person",
        properties={"name": "Alice", "age": 30}
    )
    await store.add_entity(entity)
    
    # Get entity
    retrieved = await store.get_entity("test_entity")
    assert retrieved is not None
    assert retrieved.id == "test_entity"
    assert retrieved.entity_type == "Person"
    assert retrieved.properties["name"] == "Alice"
    
    await store.close()

@pytest.mark.asyncio
async def test_add_entity_duplicate():
    """Test that duplicate entities raise error"""
    store = YourGraphStore(...)
    await store.initialize()
    
    entity = Entity(id="dup", entity_type="Test", properties={})
    await store.add_entity(entity)
    
    # Try to add again
    with pytest.raises(ValueError, match="already exists"):
        await store.add_entity(entity)
    
    await store.close()

@pytest.mark.asyncio
async def test_add_and_get_relation():
    """Test relation CRUD operations"""
    store = YourGraphStore(...)
    await store.initialize()
    
    # Create entities first
    e1 = Entity(id="e1", entity_type="Person", properties={})
    e2 = Entity(id="e2", entity_type="Person", properties={})
    await store.add_entity(e1)
    await store.add_entity(e2)
    
    # Add relation
    relation = Relation(
        id="r1",
        source_id="e1",
        target_id="e2",
        relation_type="KNOWS",
        properties={"since": "2020"}
    )
    await store.add_relation(relation)
    
    # Get relation
    retrieved = await store.get_relation("r1")
    assert retrieved is not None
    assert retrieved.relation_type == "KNOWS"
    assert retrieved.properties["since"] == "2020"
    
    await store.close()

@pytest.mark.asyncio
async def test_get_neighbors():
    """Test neighbor queries"""
    store = YourGraphStore(...)
    await store.initialize()
    
    # Create graph: A -> B -> C
    entities = [
        Entity(id="a", entity_type="Node", properties={}),
        Entity(id="b", entity_type="Node", properties={}),
        Entity(id="c", entity_type="Node", properties={}),
    ]
    for e in entities:
        await store.add_entity(e)
    
    relations = [
        Relation(id="r1", source_id="a", target_id="b", relation_type="CONNECTS", properties={}),
        Relation(id="r2", source_id="b", target_id="c", relation_type="CONNECTS", properties={}),
    ]
    for r in relations:
        await store.add_relation(r)
    
    # Test outgoing neighbors
    neighbors = await store.get_neighbors("a", direction="outgoing")
    assert len(neighbors) == 1
    assert neighbors[0].id == "b"
    
    # Test incoming neighbors
    neighbors = await store.get_neighbors("c", direction="incoming")
    assert len(neighbors) == 1
    assert neighbors[0].id == "b"
    
    # Test both directions
    neighbors = await store.get_neighbors("b", direction="both")
    assert len(neighbors) == 2
    neighbor_ids = {n.id for n in neighbors}
    assert neighbor_ids == {"a", "c"}
    
    await store.close()
```

### 2. Compatibility Tests

Use the application layer functions to test compatibility:

```python
from test.integration_tests.graph_storage.test_backend_compatibility import (
    application_add_person,
    application_add_relationship,
    application_find_friends,
    application_get_person_info,
)

@pytest.mark.asyncio
async def test_application_layer_compatibility():
    """Test that application layer works with your backend"""
    store = YourGraphStore(...)
    await store.initialize()
    
    # Application layer code should work without changes
    await application_add_person(store, "p1", "Alice", 30)
    await application_add_person(store, "p2", "Bob", 25)
    await application_add_relationship(store, "p1", "p2", "KNOWS")
    
    # Verify
    alice = await application_get_person_info(store, "p1")
    assert alice is not None
    assert alice["name"] == "Alice"
    
    friends = await application_find_friends(store, "p1")
    assert len(friends) == 1
    assert friends[0].properties["name"] == "Bob"
    
    await store.close()
```

### 3. Tier 2 Method Tests

Test that Tier 2 methods work (using default implementations or your optimizations):

```python
@pytest.mark.asyncio
async def test_path_finding():
    """Test path finding (Tier 2 method)"""
    store = YourGraphStore(...)
    await store.initialize()
    
    # Create chain: A -> B -> C -> D
    entities = [Entity(id=f"e{i}", entity_type="Node", properties={}) for i in range(4)]
    for e in entities:
        await store.add_entity(e)
    
    for i in range(3):
        await store.add_relation(Relation(
            id=f"r{i}",
            source_id=f"e{i}",
            target_id=f"e{i+1}",
            relation_type="CONNECTS",
            properties={}
        ))
    
    # Find paths (should work with default implementation)
    paths = await store.find_paths("e0", "e3", max_depth=5)
    assert len(paths) > 0
    assert paths[0].nodes[0].id == "e0"
    assert paths[0].nodes[-1].id == "e3"
    
    await store.close()

@pytest.mark.asyncio
async def test_traverse():
    """Test graph traversal (Tier 2 method)"""
    store = YourGraphStore(...)
    await store.initialize()
    
    # Create graph
    # ... add entities and relations
    
    # Traverse (should work with default implementation)
    results = await store.traverse("start_node", max_depth=3)
    assert len(results) > 0
    
    await store.close()
```

### 4. Performance Tests

If you've optimized Tier 2 methods, test their performance:

```python
@pytest.mark.asyncio
async def test_optimized_path_finding():
    """Test optimized path finding performance"""
    store = YourGraphStore(...)
    await store.initialize()
    
    # Create large graph
    # ... add many entities and relations
    
    import time
    start = time.time()
    paths = await store.find_paths("source", "target", max_depth=10)
    elapsed = time.time() - start
    
    assert len(paths) > 0
    assert elapsed < 1.0  # Should be fast with optimization
    print(f"Path finding took {elapsed:.2f}s")
    
    await store.close()
```

### 5. Error Handling Tests

Test error conditions:

```python
@pytest.mark.asyncio
async def test_error_handling():
    """Test error handling"""
    store = YourGraphStore(...)
    
    # Test operations without initialization
    with pytest.raises(RuntimeError, match="not initialized"):
        await store.add_entity(Entity(id="test", entity_type="Test", properties={}))
    
    await store.initialize()
    
    # Test duplicate entity
    entity = Entity(id="dup", entity_type="Test", properties={})
    await store.add_entity(entity)
    with pytest.raises(ValueError):
        await store.add_entity(entity)
    
    # Test relation with non-existent entities
    with pytest.raises(ValueError):
        await store.add_relation(Relation(
            id="r1",
            source_id="nonexistent",
            target_id="nonexistent2",
            relation_type="TEST",
            properties={}
        ))
    
    await store.close()
```

### 6. Transaction Tests (if supported)

If your backend supports transactions:

```python
@pytest.mark.asyncio
async def test_transactions():
    """Test transaction support"""
    store = YourGraphStore(...)
    await store.initialize()
    
    # Test successful transaction
    async with store.transaction():
        await store.add_entity(Entity(id="tx1", entity_type="Test", properties={}))
        await store.add_entity(Entity(id="tx2", entity_type="Test", properties={}))
    
    # Both should be committed
    assert await store.get_entity("tx1") is not None
    assert await store.get_entity("tx2") is not None
    
    # Test rollback
    try:
        async with store.transaction():
            await store.add_entity(Entity(id="rollback", entity_type="Test", properties={}))
            raise ValueError("Test rollback")
    except ValueError:
        pass
    
    # Entity should not exist
    assert await store.get_entity("rollback") is None
    
    await store.close()
```

---

## Running Compatibility Tests

You can use the existing compatibility test suite:

```python
# In your test file
from test.integration_tests.graph_storage.test_backend_compatibility import (
    TestApplicationLayerCompatibility,
    TestBackendSwitching,
    TestApplicationLayerAbstraction,
)

# Create a fixture for your backend
@pytest.fixture
async def your_backend_store():
    store = YourGraphStore(...)
    await store.initialize()
    yield store
    await store.close()

# Run compatibility tests
class TestYourBackendCompatibility(TestApplicationLayerCompatibility):
    """Run compatibility tests with your backend"""
    
    @pytest.fixture
    async def inmemory_store(self):
        # Override to use your backend
        store = YourGraphStore(...)
        await store.initialize()
        yield store
        await store.close()
    
    # All tests from TestApplicationLayerCompatibility will run
```

---

## Test Checklist

Use this checklist to ensure your adapter is fully tested:

### Tier 1 Methods
- [ ] `initialize()` - Creates connections, sets up schema
- [ ] `close()` - Cleans up resources
- [ ] `add_entity()` - Adds entity, raises error on duplicate
- [ ] `get_entity()` - Retrieves entity, returns None if not found
- [ ] `add_relation()` - Adds relation, validates entities exist
- [ ] `get_relation()` - Retrieves relation, returns None if not found
- [ ] `get_neighbors()` - Returns neighbors in all directions

### Tier 2 Methods (Default or Optimized)
- [ ] `find_paths()` - Finds paths between entities
- [ ] `traverse()` - Traverses graph from entity
- [ ] `subgraph_query()` - Extracts subgraph
- [ ] `get_stats()` - Returns graph statistics

### Error Handling
- [ ] Operations fail gracefully when not initialized
- [ ] Duplicate entities raise ValueError
- [ ] Relations with non-existent entities raise ValueError
- [ ] Invalid parameters raise appropriate errors

### Compatibility
- [ ] Application layer functions work without changes
- [ ] Can switch between backends without code changes
- [ ] All GraphStore interface methods implemented

### Performance (if optimized)
- [ ] Tier 2 methods perform better than defaults
- [ ] Batch operations work efficiently
- [ ] Connection pooling works correctly

---

## Example Test Suite

Here's a complete example test suite:

```python
"""
Complete test suite for custom backend adapter
"""

import pytest
from your_backend import YourGraphStore
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation


@pytest.fixture
async def store():
    """Create test store instance"""
    store = YourGraphStore(
        # Your connection parameters
    )
    await store.initialize()
    yield store
    await store.close()


class TestTier1Methods:
    """Test Tier 1 (required) methods"""
    
    @pytest.mark.asyncio
    async def test_initialize_close(self, store):
        """Test initialization and cleanup"""
        assert store._initialized is True
    
    @pytest.mark.asyncio
    async def test_entity_operations(self, store):
        """Test entity CRUD"""
        entity = Entity(id="test", entity_type="Test", properties={"key": "value"})
        await store.add_entity(entity)
        
        retrieved = await store.get_entity("test")
        assert retrieved is not None
        assert retrieved.properties["key"] == "value"
    
    @pytest.mark.asyncio
    async def test_relation_operations(self, store):
        """Test relation CRUD"""
        # Create entities
        e1 = Entity(id="e1", entity_type="Test", properties={})
        e2 = Entity(id="e2", entity_type="Test", properties={})
        await store.add_entity(e1)
        await store.add_entity(e2)
        
        # Create relation
        relation = Relation(
            id="r1",
            source_id="e1",
            target_id="e2",
            relation_type="CONNECTS",
            properties={}
        )
        await store.add_relation(relation)
        
        retrieved = await store.get_relation("r1")
        assert retrieved is not None
    
    @pytest.mark.asyncio
    async def test_get_neighbors(self, store):
        """Test neighbor queries"""
        # Create graph
        # ... add entities and relations
        
        neighbors = await store.get_neighbors("entity_id", direction="both")
        assert isinstance(neighbors, list)


class TestTier2Methods:
    """Test Tier 2 (optional) methods"""
    
    @pytest.mark.asyncio
    async def test_path_finding(self, store):
        """Test path finding"""
        # Create test graph
        # ... add entities and relations
        
        paths = await store.find_paths("source", "target", max_depth=5)
        assert len(paths) > 0
    
    @pytest.mark.asyncio
    async def test_traverse(self, store):
        """Test graph traversal"""
        # Create test graph
        # ... add entities and relations
        
        results = await store.traverse("start", max_depth=3)
        assert len(results) > 0


class TestCompatibility:
    """Test compatibility with application layer"""
    
    @pytest.mark.asyncio
    async def test_application_functions(self, store):
        """Test application layer functions work"""
        from test.integration_tests.graph_storage.test_backend_compatibility import (
            application_add_person,
            application_find_friends,
        )
        
        await application_add_person(store, "p1", "Alice", 30)
        friends = await application_find_friends(store, "p1")
        assert isinstance(friends, list)


class TestErrorHandling:
    """Test error handling"""
    
    @pytest.mark.asyncio
    async def test_not_initialized(self):
        """Test operations fail when not initialized"""
        store = YourGraphStore(...)
        with pytest.raises(RuntimeError):
            await store.add_entity(Entity(id="test", entity_type="Test", properties={}))
    
    @pytest.mark.asyncio
    async def test_duplicate_entity(self, store):
        """Test duplicate entity raises error"""
        entity = Entity(id="dup", entity_type="Test", properties={})
        await store.add_entity(entity)
        with pytest.raises(ValueError):
            await store.add_entity(entity)
```

---

## Summary

Testing your adapter involves:

1. ✅ **Unit tests** for each Tier 1 method
2. ✅ **Compatibility tests** using application layer functions
3. ✅ **Tier 2 tests** to verify default implementations work
4. ✅ **Performance tests** if you've optimized Tier 2 methods
5. ✅ **Error handling tests** for edge cases

**The compatibility test suite ensures your adapter works seamlessly with AIECS!**

