"""
Unit tests for graph storage lazy loading module

Tests use real components (InMemoryGraphStore) when possible.
Only use mocks if pytest-cov limitations cause issues.
"""

import pytest
from aiecs.infrastructure.graph_storage import InMemoryGraphStore
from aiecs.infrastructure.graph_storage.lazy_loading import (
    LazyEntity,
    LazyRelation,
    LazyLoadingMixin,
    EntityBatchLoader,
    lazy_traverse
)
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation


class TestLazyEntity:
    """Test LazyEntity"""
    
    @pytest.fixture
    async def store(self):
        """Create and initialize in-memory graph store"""
        store = InMemoryGraphStore()
        await store.initialize()
        
        # Add test entity
        entity = Entity(
            id="e1",
            entity_type="Person",
            properties={"name": "Alice", "age": 30}
        )
        await store.add_entity(entity)
        
        yield store
        await store.close()
    
    def test_lazy_entity_init(self):
        """Test LazyEntity initialization"""
        lazy = LazyEntity(id="e1", entity_type="Person")
        
        assert lazy.id == "e1"
        assert lazy.entity_type == "Person"
        assert lazy._store is None
        assert lazy.is_loaded() is False
    
    @pytest.mark.asyncio
    async def test_lazy_entity_load(self, store):
        """Test loading lazy entity"""
        lazy = LazyEntity(id="e1", _store=store)
        
        assert lazy.is_loaded() is False
        
        entity = await lazy.load()
        
        assert entity is not None
        assert entity.id == "e1"
        assert entity.entity_type == "Person"
        assert lazy.is_loaded() is True
    
    @pytest.mark.asyncio
    async def test_lazy_entity_load_nonexistent(self, store):
        """Test loading non-existent entity"""
        lazy = LazyEntity(id="nonexistent", _store=store)
        
        entity = await lazy.load()
        
        assert entity is None
        assert lazy.is_loaded() is True  # Still marked as loaded (None result)
    
    @pytest.mark.asyncio
    async def test_lazy_entity_load_no_store(self):
        """Test loading without store"""
        lazy = LazyEntity(id="e1")
        
        with pytest.raises(RuntimeError):
            await lazy.load()
    
    @pytest.mark.asyncio
    async def test_lazy_entity_load_cached(self, store):
        """Test that loaded entity is cached"""
        lazy = LazyEntity(id="e1", _store=store)
        
        entity1 = await lazy.load()
        entity2 = await lazy.load()
        
        # Should return same object (cached)
        assert entity1 is entity2
    
    @pytest.mark.asyncio
    async def test_lazy_entity_load_force(self, store):
        """Test force reload"""
        lazy = LazyEntity(id="e1", _store=store)
        
        entity1 = await lazy.load()
        entity2 = await lazy.load(force=True)
        
        # Should reload (may be same or different object depending on store)
        assert entity1.id == entity2.id
    
    @pytest.mark.asyncio
    async def test_lazy_entity_get_property(self, store):
        """Test getting property from lazy entity"""
        lazy = LazyEntity(id="e1", _store=store)
        
        name = await lazy.get("name")
        age = await lazy.get("age")
        missing = await lazy.get("missing", default="default_value")
        
        assert name == "Alice"
        assert age == 30
        assert missing == "default_value"
    
    @pytest.mark.asyncio
    async def test_lazy_entity_get_property_nonexistent(self, store):
        """Test getting property from non-existent entity"""
        lazy = LazyEntity(id="nonexistent", _store=store)
        
        value = await lazy.get("name", default="default")
        
        assert value == "default"
    
    def test_lazy_entity_to_dict_not_loaded(self):
        """Test to_dict when not loaded"""
        lazy = LazyEntity(id="e1", entity_type="Person")
        
        result = lazy.to_dict()
        
        assert result["id"] == "e1"
        assert result["entity_type"] == "Person"
        assert "properties" not in result
    
    @pytest.mark.asyncio
    async def test_lazy_entity_to_dict_loaded(self, store):
        """Test to_dict when loaded"""
        lazy = LazyEntity(id="e1", _store=store)
        await lazy.load()
        
        result = lazy.to_dict()
        
        assert result["id"] == "e1"
        assert "properties" in result
        assert result["properties"]["name"] == "Alice"


class TestLazyRelation:
    """Test LazyRelation"""
    
    @pytest.fixture
    async def store(self):
        """Create and initialize in-memory graph store"""
        store = InMemoryGraphStore()
        await store.initialize()
        
        # Add entities and relation
        e1 = Entity(id="e1", entity_type="Person", properties={})
        e2 = Entity(id="e2", entity_type="Person", properties={})
        await store.add_entity(e1)
        await store.add_entity(e2)
        
        relation = Relation(
            id="r1",
            relation_type="KNOWS",
            source_id="e1",
            target_id="e2"
        )
        await store.add_relation(relation)
        
        yield store
        await store.close()
    
    def test_lazy_relation_init(self):
        """Test LazyRelation initialization"""
        lazy = LazyRelation(id="r1", source_id="e1", target_id="e2", relation_type="KNOWS")
        
        assert lazy.id == "r1"
        assert lazy.source_id == "e1"
        assert lazy.target_id == "e2"
        assert lazy.relation_type == "KNOWS"
        assert lazy.is_loaded() is False
    
    @pytest.mark.asyncio
    async def test_lazy_relation_load(self, store):
        """Test loading lazy relation"""
        lazy = LazyRelation(id="r1", source_id="e1", target_id="e2", _store=store)
        
        relation = await lazy.load()
        
        assert relation is not None
        assert relation.id == "r1"
        assert relation.relation_type == "KNOWS"
        assert lazy.is_loaded() is True
    
    @pytest.mark.asyncio
    async def test_lazy_relation_get_source(self, store):
        """Test getting source entity"""
        lazy = LazyRelation(id="r1", source_id="e1", target_id="e2", _store=store)
        
        source = await lazy.get_source()
        
        assert source is not None
        assert source.id == "e1"
    
    @pytest.mark.asyncio
    async def test_lazy_relation_get_target(self, store):
        """Test getting target entity"""
        lazy = LazyRelation(id="r1", source_id="e1", target_id="e2", _store=store)
        
        target = await lazy.get_target()
        
        assert target is not None
        assert target.id == "e2"
    
    @pytest.mark.asyncio
    async def test_lazy_relation_get_source_no_store(self):
        """Test getting source without store"""
        lazy = LazyRelation(id="r1", source_id="e1", target_id="e2")
        
        source = await lazy.get_source()
        
        assert source is None


class TestLazyLoadingMixin:
    """Test LazyLoadingMixin"""
    
    @pytest.fixture
    async def store(self):
        """Create store with LazyLoadingMixin"""
        class LazyStore(InMemoryGraphStore, LazyLoadingMixin):
            async def get_all_entities(self, entity_type=None, limit=None):
                """Get all entities (for testing)"""
                entities = list(self.entities.values())
                if entity_type:
                    entities = [e for e in entities if e.entity_type == entity_type]
                if limit:
                    entities = entities[:limit]
                return entities
        
        store = LazyStore()
        await store.initialize()
        
        # Add test entities
        for i in range(10):
            entity = Entity(
                id=f"e{i}",
                entity_type="Person" if i % 2 == 0 else "Company",
                properties={"index": i}
            )
            await store.add_entity(entity)
        
        yield store
        await store.close()
    
    @pytest.mark.asyncio
    async def test_get_lazy_entity(self, store):
        """Test getting single lazy entity"""
        lazy = await store.get_lazy_entity("e1")
        
        assert isinstance(lazy, LazyEntity)
        assert lazy.id == "e1"
        assert lazy._store == store
        assert lazy.is_loaded() is False
    
    @pytest.mark.asyncio
    async def test_get_lazy_entities(self, store):
        """Test getting multiple lazy entities"""
        lazy_entities = await store.get_lazy_entities()
        
        assert len(lazy_entities) == 10
        assert all(isinstance(le, LazyEntity) for le in lazy_entities)
        assert all(not le.is_loaded() for le in lazy_entities)
    
    @pytest.mark.asyncio
    async def test_get_lazy_entities_with_type(self, store):
        """Test getting lazy entities with type filter"""
        lazy_entities = await store.get_lazy_entities(entity_type="Person")
        
        assert len(lazy_entities) == 5  # Half are Person
        assert all(le.entity_type == "Person" for le in lazy_entities)
    
    @pytest.mark.asyncio
    async def test_get_lazy_entities_with_limit(self, store):
        """Test getting lazy entities with limit"""
        lazy_entities = await store.get_lazy_entities(limit=5)
        
        assert len(lazy_entities) == 5
    
    @pytest.mark.asyncio
    async def test_get_lazy_neighbors(self, store):
        """Test getting lazy neighbors"""
        # Add relations
        for i in range(5):
            relation = Relation(
                id=f"r{i}",
                relation_type="KNOWS",
                source_id="e0",
                target_id=f"e{i+1}"
            )
            await store.add_relation(relation)
        
        lazy_neighbors = await store.get_lazy_neighbors("e0")
        
        assert len(lazy_neighbors) == 5
        assert all(isinstance(ln, LazyEntity) for ln in lazy_neighbors)
        assert all(not ln.is_loaded() for ln in lazy_neighbors)


class TestEntityBatchLoader:
    """Test EntityBatchLoader"""
    
    @pytest.fixture
    async def store(self):
        """Create and initialize in-memory graph store"""
        store = InMemoryGraphStore()
        await store.initialize()
        
        # Add test entities
        for i in range(20):
            entity = Entity(
                id=f"e{i}",
                entity_type="Person",
                properties={"index": i}
            )
            await store.add_entity(entity)
        
        yield store
        await store.close()
    
    @pytest.fixture
    def loader(self, store):
        """Create EntityBatchLoader instance"""
        return EntityBatchLoader(store, batch_size=10)
    
    @pytest.mark.asyncio
    async def test_batch_loader_load_single(self, loader):
        """Test loading single entity"""
        # Load queues the entity
        await loader.load("e1")
        
        # Dispatch to actually load it
        await loader.dispatch()
        
        # Now it should be in cache
        entity = loader._cache.get("e1")
        assert entity is not None
        assert entity.id == "e1"
    
    @pytest.mark.asyncio
    async def test_batch_loader_load_multiple(self, loader):
        """Test loading multiple entities"""
        # Load entities (they're queued, not loaded yet)
        await loader.load("e1")
        await loader.load("e2")
        await loader.load("e3")
        
        # Dispatch to load all
        await loader.dispatch()
        
        # Now they should be in cache
        assert loader._cache.get("e1") is not None
        assert loader._cache.get("e2") is not None
        assert loader._cache.get("e3") is not None
    
    @pytest.mark.asyncio
    async def test_batch_loader_auto_dispatch(self, loader):
        """Test automatic dispatch when batch is full"""
        # Load up to batch_size (triggers auto-dispatch)
        for i in range(10):  # Load exactly batch_size
            await loader.load(f"e{i}")
        
        # First 10 should be loaded after auto-dispatch
        assert loader._cache.get("e0") is not None
        assert loader._cache.get("e9") is not None
        
        # Load one more - should trigger another dispatch
        await loader.load("e10")
        await loader.dispatch()  # Ensure e10 is loaded
        
        assert loader._cache.get("e10") is not None
    
    @pytest.mark.asyncio
    async def test_batch_loader_cache(self, loader):
        """Test batch loader caching"""
        # First load - queues and dispatches
        await loader.load("e1")
        await loader.dispatch()
        
        # Second load should use cache
        entity2 = await loader.load("e1")
        
        # Should return cached entity
        assert entity2 is not None
        assert entity2.id == "e1"
        assert loader._cache.get("e1") is not None
    
    @pytest.mark.asyncio
    async def test_batch_loader_dispatch_empty(self, loader):
        """Test dispatching with empty queue"""
        await loader.dispatch()  # Should not raise error
    
    def test_batch_loader_clear_cache(self, loader):
        """Test clearing cache"""
        loader._cache["e1"] = Entity(id="e1", entity_type="Person", properties={})
        
        loader.clear_cache()
        
        assert "e1" not in loader._cache


class TestLazyTraverse:
    """Test lazy_traverse function"""
    
    @pytest.fixture
    async def store(self):
        """Create and initialize in-memory graph store"""
        store = InMemoryGraphStore()
        await store.initialize()
        
        # Create a simple graph: e0 -> e1 -> e2
        for i in range(3):
            entity = Entity(id=f"e{i}", entity_type="Person", properties={})
            await store.add_entity(entity)
        
        r1 = Relation(id="r1", relation_type="KNOWS", source_id="e0", target_id="e1")
        r2 = Relation(id="r2", relation_type="KNOWS", source_id="e1", target_id="e2")
        await store.add_relation(r1)
        await store.add_relation(r2)
        
        yield store
        await store.close()
    
    @pytest.mark.asyncio
    async def test_lazy_traverse(self, store):
        """Test lazy traversal"""
        entities = []
        async for lazy_entity in lazy_traverse(store, "e0", max_depth=2):
            entities.append(lazy_entity.id)
        
        assert "e0" in entities
        assert "e1" in entities
        assert "e2" in entities
    
    @pytest.mark.asyncio
    async def test_lazy_traverse_max_depth(self, store):
        """Test lazy traversal respects max depth"""
        # Add more depth
        e3 = Entity(id="e3", entity_type="Person", properties={})
        await store.add_entity(e3)
        r3 = Relation(id="r3", relation_type="KNOWS", source_id="e2", target_id="e3")
        await store.add_relation(r3)
        
        entities = []
        async for lazy_entity in lazy_traverse(store, "e0", max_depth=1):
            entities.append(lazy_entity.id)
        
        # Should only include e0 and e1 (depth 1)
        assert "e0" in entities
        assert "e1" in entities
        assert "e2" not in entities

