"""
Integration tests for graph store migration utilities

Tests migration between different storage backends and JSON import/export.
"""

import pytest
import tempfile
import os
import json
from pathlib import Path

from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore
from aiecs.infrastructure.graph_storage.sqlite import SQLiteGraphStore
from aiecs.infrastructure.graph_storage.migration import (
    migrate_graph_store,
    export_to_json,
    import_from_json
)


@pytest.fixture
async def populated_inmemory_store():
    """Fixture with populated in-memory store"""
    store = InMemoryGraphStore()
    await store.initialize()
    
    # Add entities
    alice = Entity(id="alice", entity_type="Person", properties={"name": "Alice"})
    bob = Entity(id="bob", entity_type="Person", properties={"name": "Bob"})
    
    await store.add_entity(alice)
    await store.add_entity(bob)
    
    # Add relation
    await store.add_relation(Relation(
        id="r1", relation_type="KNOWS", source_id="alice", target_id="bob"
    ))
    
    yield store
    await store.close()


@pytest.fixture
async def empty_sqlite_store():
    """Fixture with empty SQLite store"""
    store = SQLiteGraphStore(":memory:")
    await store.initialize()
    yield store
    await store.close()


class TestMigration:
    """Test migration between storage backends"""
    
    @pytest.mark.asyncio
    async def test_migrate_inmemory_to_sqlite(self, populated_inmemory_store, empty_sqlite_store):
        """Test migrating from InMemory to SQLite"""
        # Verify source has data
        alice = await populated_inmemory_store.get_entity("alice")
        assert alice is not None
        
        # Verify target is empty
        stats_before = await empty_sqlite_store.get_stats()
        assert stats_before["entity_count"] == 0
        
        # Migrate
        result = await migrate_graph_store(populated_inmemory_store, empty_sqlite_store)
        
        # Verify migration stats
        assert result["entities_migrated"] == 2
        assert result["relations_migrated"] == 1
        assert len(result["errors"]) == 0
        
        # Verify data in target
        alice_migrated = await empty_sqlite_store.get_entity("alice")
        assert alice_migrated is not None
        assert alice_migrated.properties["name"] == "Alice"
        
        bob_migrated = await empty_sqlite_store.get_entity("bob")
        assert bob_migrated is not None
        
        relation_migrated = await empty_sqlite_store.get_relation("r1")
        assert relation_migrated is not None
        assert relation_migrated.relation_type == "KNOWS"
    
    @pytest.mark.asyncio
    async def test_migrate_sqlite_to_inmemory(self):
        """Test migrating from SQLite to InMemory"""
        # Create and populate SQLite store
        source_store = SQLiteGraphStore(":memory:")
        await source_store.initialize()
        
        await source_store.add_entity(Entity(id="e1", entity_type="Test"))
        await source_store.add_entity(Entity(id="e2", entity_type="Test"))
        await source_store.add_relation(Relation(
            id="r1", relation_type="TEST", source_id="e1", target_id="e2"
        ))
        
        # Create empty InMemory store
        target_store = InMemoryGraphStore()
        await target_store.initialize()
        
        # Migrate
        result = await migrate_graph_store(source_store, target_store)
        
        # Verify
        assert result["entities_migrated"] == 2
        assert result["relations_migrated"] == 1
        
        # Verify data in target
        assert await target_store.get_entity("e1") is not None
        assert await target_store.get_entity("e2") is not None
        assert await target_store.get_relation("r1") is not None
        
        await source_store.close()
        await target_store.close()
    
    @pytest.mark.asyncio
    async def test_migrate_with_embeddings(self):
        """Test migration preserves embeddings"""
        # Create source with embeddings
        source = InMemoryGraphStore()
        await source.initialize()
        
        entity = Entity(
            id="e1",
            entity_type="Document",
            properties={"title": "Test"},
            embedding=[0.1, 0.2, 0.3]
        )
        await source.add_entity(entity)
        
        # Migrate to SQLite
        target = SQLiteGraphStore(":memory:")
        await target.initialize()
        
        result = await migrate_graph_store(source, target)
        
        assert result["entities_migrated"] == 1
        
        # Verify embedding preserved
        migrated = await target.get_entity("e1")
        assert migrated.embedding is not None
        assert len(migrated.embedding) == 3
        assert abs(migrated.embedding[0] - 0.1) < 0.001
        
        await source.close()
        await target.close()
    
    @pytest.mark.asyncio
    async def test_migrate_handles_duplicates(self, populated_inmemory_store, empty_sqlite_store):
        """Test migration handles existing entities gracefully"""
        # Add one entity to target before migration
        await empty_sqlite_store.add_entity(Entity(id="alice", entity_type="Person"))
        
        # Migrate (should skip duplicate)
        result = await migrate_graph_store(populated_inmemory_store, empty_sqlite_store)
        
        # Should have errors for duplicate
        assert result["entities_migrated"] == 1  # Only bob
        assert len(result["errors"]) > 0
        assert any("alice" in error for error in result["errors"])


class TestJSONExport:
    """Test JSON export functionality"""
    
    @pytest.mark.asyncio
    async def test_export_inmemory_to_json(self, populated_inmemory_store):
        """Test exporting InMemory store to JSON"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json_path = f.name
        
        try:
            # Export
            result = await export_to_json(populated_inmemory_store, json_path)
            
            # Verify export stats
            assert result["entities_exported"] == 2
            assert result["relations_exported"] == 1
            assert len(result["errors"]) == 0
            
            # Verify JSON file exists and has correct structure
            assert os.path.exists(json_path)
            
            with open(json_path, 'r') as f:
                data = json.load(f)
            
            assert "entities" in data
            assert "relations" in data
            assert "metadata" in data
            assert len(data["entities"]) == 2
            assert len(data["relations"]) == 1
            assert data["metadata"]["entity_count"] == 2
            assert data["metadata"]["relation_count"] == 1
        finally:
            if os.path.exists(json_path):
                os.unlink(json_path)
    
    @pytest.mark.asyncio
    async def test_export_sqlite_to_json(self):
        """Test exporting SQLite store to JSON"""
        # Create and populate SQLite store
        store = SQLiteGraphStore(":memory:")
        await store.initialize()
        
        await store.add_entity(Entity(id="e1", entity_type="Test", properties={"value": 42}))
        await store.add_entity(Entity(id="e2", entity_type="Test"))
        await store.add_relation(Relation(
            id="r1", relation_type="TEST", source_id="e1", target_id="e2"
        ))
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json_path = f.name
        
        try:
            # Export
            result = await export_to_json(store, json_path)
            
            # Verify
            assert result["entities_exported"] == 2
            assert result["relations_exported"] == 1
            
            # Verify JSON content
            with open(json_path, 'r') as f:
                data = json.load(f)
            
            # Find e1 and verify properties
            e1_data = next(e for e in data["entities"] if e["id"] == "e1")
            assert e1_data["properties"]["value"] == 42
        finally:
            if os.path.exists(json_path):
                os.unlink(json_path)
            await store.close()
    
    @pytest.mark.asyncio
    async def test_export_with_embeddings(self):
        """Test export preserves embeddings"""
        store = InMemoryGraphStore()
        await store.initialize()
        
        entity = Entity(
            id="e1",
            entity_type="Document",
            embedding=[0.1, 0.2, 0.3]
        )
        await store.add_entity(entity)
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json_path = f.name
        
        try:
            await export_to_json(store, json_path)
            
            with open(json_path, 'r') as f:
                data = json.load(f)
            
            # Verify embedding in JSON
            assert data["entities"][0]["embedding"] is not None
            assert len(data["entities"][0]["embedding"]) == 3
        finally:
            if os.path.exists(json_path):
                os.unlink(json_path)
            await store.close()


class TestJSONImport:
    """Test JSON import functionality"""
    
    @pytest.mark.asyncio
    async def test_import_json_to_inmemory(self):
        """Test importing JSON to InMemory store"""
        # Create JSON file
        json_data = {
            "entities": [
                {"id": "e1", "entity_type": "Test", "properties": {"value": 42}, "embedding": None, "source": None, "created_at": "2024-01-01T00:00:00", "updated_at": "2024-01-01T00:00:00"},
                {"id": "e2", "entity_type": "Test", "properties": {}, "embedding": None, "source": None, "created_at": "2024-01-01T00:00:00", "updated_at": "2024-01-01T00:00:00"}
            ],
            "relations": [
                {
                    "id": "r1",
                    "relation_type": "TEST",
                    "source_id": "e1",
                    "target_id": "e2",
                    "properties": {},
                    "weight": 1.0,
                    "source": None,
                    "created_at": "2024-01-01T00:00:00"
                }
            ],
            "metadata": {"entity_count": 2, "relation_count": 1}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(json_data, f)
            json_path = f.name
        
        try:
            # Create empty store
            store = InMemoryGraphStore()
            await store.initialize()
            
            # Import
            result = await import_from_json(store, json_path)
            
            # Verify import stats
            assert result["entities_imported"] == 2
            assert result["relations_imported"] == 1
            assert len(result["errors"]) == 0
            
            # Verify data in store
            e1 = await store.get_entity("e1")
            assert e1 is not None
            assert e1.properties["value"] == 42
            
            r1 = await store.get_relation("r1")
            assert r1 is not None
            
            await store.close()
        finally:
            if os.path.exists(json_path):
                os.unlink(json_path)
    
    @pytest.mark.asyncio
    async def test_import_json_to_sqlite(self):
        """Test importing JSON to SQLite store"""
        # Create JSON file
        json_data = {
            "entities": [
                {"id": "e1", "entity_type": "Test", "properties": {}, "embedding": None, "source": None, "created_at": "2024-01-01T00:00:00", "updated_at": "2024-01-01T00:00:00"}
            ],
            "relations": [],
            "metadata": {"entity_count": 1, "relation_count": 0}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(json_data, f)
            json_path = f.name
        
        try:
            store = SQLiteGraphStore(":memory:")
            await store.initialize()
            
            result = await import_from_json(store, json_path)
            
            assert result["entities_imported"] == 1
            assert await store.get_entity("e1") is not None
            
            await store.close()
        finally:
            if os.path.exists(json_path):
                os.unlink(json_path)
    
    @pytest.mark.asyncio
    async def test_import_handles_duplicates(self):
        """Test import handles existing entities gracefully"""
        store = InMemoryGraphStore()
        await store.initialize()
        
        # Add entity to store
        await store.add_entity(Entity(id="e1", entity_type="Test"))
        
        # Create JSON with same entity
        json_data = {
            "entities": [
                {"id": "e1", "entity_type": "Test", "properties": {}, "embedding": None, "source": None, "created_at": "2024-01-01T00:00:00", "updated_at": "2024-01-01T00:00:00"},
                {"id": "e2", "entity_type": "Test", "properties": {}, "embedding": None, "source": None, "created_at": "2024-01-01T00:00:00", "updated_at": "2024-01-01T00:00:00"}
            ],
            "relations": [],
            "metadata": {}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(json_data, f)
            json_path = f.name
        
        try:
            result = await import_from_json(store, json_path)
            
            # Should have imported only e2
            assert result["entities_imported"] == 1
            assert len(result["errors"]) > 0
            assert any("e1" in error for error in result["errors"])
        finally:
            if os.path.exists(json_path):
                os.unlink(json_path)
            await store.close()


class TestRoundTrip:
    """Test round-trip export and import"""
    
    @pytest.mark.asyncio
    async def test_export_import_roundtrip(self):
        """Test that export followed by import preserves all data"""
        # Create source store with data
        source = InMemoryGraphStore()
        await source.initialize()
        
        alice = Entity(id="alice", entity_type="Person", properties={"name": "Alice", "age": 30})
        bob = Entity(id="bob", entity_type="Person", properties={"name": "Bob"}, embedding=[0.1, 0.2])
        
        await source.add_entity(alice)
        await source.add_entity(bob)
        await source.add_relation(Relation(
            id="r1", relation_type="KNOWS", source_id="alice", target_id="bob",
            properties={"since": 2020}
        ))
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json_path = f.name
        
        try:
            # Export
            await export_to_json(source, json_path)
            
            # Create target store and import
            target = SQLiteGraphStore(":memory:")
            await target.initialize()
            
            await import_from_json(target, json_path)
            
            # Verify all data preserved
            alice_imported = await target.get_entity("alice")
            assert alice_imported is not None
            assert alice_imported.properties["name"] == "Alice"
            assert alice_imported.properties["age"] == 30
            
            bob_imported = await target.get_entity("bob")
            assert bob_imported is not None
            assert bob_imported.embedding is not None
            assert len(bob_imported.embedding) == 2
            
            r1_imported = await target.get_relation("r1")
            assert r1_imported is not None
            assert r1_imported.properties["since"] == 2020
            
            await target.close()
        finally:
            if os.path.exists(json_path):
                os.unlink(json_path)
            await source.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

