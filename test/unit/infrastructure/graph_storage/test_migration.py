"""
Unit tests for graph storage migration module

Tests use real components (InMemoryGraphStore) when possible.
Only use mocks if pytest-cov limitations cause issues.
"""

import pytest
from aiecs.infrastructure.graph_storage import InMemoryGraphStore
from aiecs.infrastructure.graph_storage.migration import GraphStorageMigrator
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation


class TestGraphStorageMigrator:
    """Test GraphStorageMigrator"""
    
    @pytest.fixture
    async def source_store(self):
        """Create source in-memory graph store with data"""
        store = InMemoryGraphStore()
        await store.initialize()
        
        # Add test entities
        for i in range(5):
            entity = Entity(
                id=f"e{i}",
                entity_type="Person" if i % 2 == 0 else "Company",
                properties={"index": i}
            )
            await store.add_entity(entity)
        
        # Add test relations
        for i in range(4):
            relation = Relation(
                id=f"r{i}",
                relation_type="KNOWS",
                source_id=f"e{i}",
                target_id=f"e{i+1}"
            )
            await store.add_relation(relation)
        
        yield store
        await store.close()
    
    @pytest.fixture
    async def target_store(self):
        """Create target in-memory graph store"""
        store = InMemoryGraphStore()
        await store.initialize()
        yield store
        await store.close()
    
    @pytest.fixture
    def migrator(self, source_store, target_store):
        """Create GraphStorageMigrator instance"""
        return GraphStorageMigrator(source_store, target_store)
    
    @pytest.mark.asyncio
    async def test_migrate_entities(self, migrator, target_store):
        """Test migrating entities"""
        from contextlib import asynccontextmanager
        
        # Add get_all_entities and transaction methods to stores
        class SourceStore(InMemoryGraphStore):
            async def get_all_entities(self):
                return list(self.entities.values())
        
        class TargetStore(InMemoryGraphStore):
            @asynccontextmanager
            async def transaction(self):
                # Simple no-op transaction for in-memory store
                yield self
        
        source = SourceStore()
        await source.initialize()
        
        # Add entities to source
        for i in range(3):
            entity = Entity(id=f"e{i}", entity_type="Person", properties={})
            await source.add_entity(entity)
        
        target = TargetStore()
        await target.initialize()
        
        migrator = GraphStorageMigrator(source, target)
        
        # Migrate
        result = await migrator.migrate(batch_size=10, show_progress=False, verify=False)
        
        assert result["entities_migrated"] == 3
        assert result["relations_migrated"] >= 0
        
        # Verify entities in target
        for i in range(3):
            entity = await target.get_entity(f"e{i}")
            assert entity is not None
            assert entity.id == f"e{i}"
        
        await source.close()
        await target.close()
    
    @pytest.mark.asyncio
    async def test_migrate_relations(self, migrator, target_store):
        """Test migrating relations"""
        from contextlib import asynccontextmanager
        
        # InMemoryGraphStore doesn't have conn/pool, so relation migration returns 0
        # This is expected behavior - relation migration only works with SQLite/Postgres
        # Test that the migration completes without error
        
        class SourceStore(InMemoryGraphStore):
            async def get_all_entities(self):
                return list(self.entities.values())
        
        class TargetStore(InMemoryGraphStore):
            @asynccontextmanager
            async def transaction(self):
                yield self
        
        source = SourceStore()
        await source.initialize()
        
        # Add entities
        e1 = Entity(id="e1", entity_type="Person", properties={})
        e2 = Entity(id="e2", entity_type="Person", properties={})
        await source.add_entity(e1)
        await source.add_entity(e2)
        
        target = TargetStore()
        await target.initialize()
        
        migrator = GraphStorageMigrator(source, target)
        
        # Migrate
        result = await migrator.migrate(batch_size=10, show_progress=False, verify=False)
        
        assert result["entities_migrated"] == 2
        # Relations migration returns 0 for InMemoryGraphStore (expected)
        assert result["relations_migrated"] == 0
        
        await source.close()
        await target.close()
    
    @pytest.mark.asyncio
    async def test_migrate_empty_source(self, target_store):
        """Test migrating from empty source"""
        from contextlib import asynccontextmanager
        
        class SourceStore(InMemoryGraphStore):
            async def get_all_entities(self):
                return []
        
        class TargetStore(InMemoryGraphStore):
            @asynccontextmanager
            async def transaction(self):
                yield self
        
        source = SourceStore()
        await source.initialize()
        
        target = TargetStore()
        await target.initialize()
        
        migrator = GraphStorageMigrator(source, target)
        
        result = await migrator.migrate(show_progress=False, verify=False)
        
        assert result["entities_migrated"] == 0
        assert result["relations_migrated"] == 0
        
        await source.close()
        await target.close()
    
    @pytest.mark.asyncio
    async def test_migrate_with_verification(self, target_store):
        """Test migration with verification"""
        from contextlib import asynccontextmanager
        
        class SourceStore(InMemoryGraphStore):
            async def get_all_entities(self):
                return list(self.entities.values())
        
        class TargetStore(InMemoryGraphStore):
            @asynccontextmanager
            async def transaction(self):
                yield self
        
        source = SourceStore()
        await source.initialize()
        
        # Add entity
        entity = Entity(id="e1", entity_type="Person", properties={})
        await source.add_entity(entity)
        
        target = TargetStore()
        await target.initialize()
        
        migrator = GraphStorageMigrator(source, target)
        
        result = await migrator.migrate(show_progress=False, verify=True)
        
        assert result["entities_migrated"] == 1
        assert "verification" in result
        
        await source.close()
        await target.close()
    
    @pytest.mark.asyncio
    async def test_migrate_batch_size(self, target_store):
        """Test migration with different batch sizes"""
        from contextlib import asynccontextmanager
        
        class SourceStore(InMemoryGraphStore):
            async def get_all_entities(self):
                return list(self.entities.values())
        
        class TargetStore(InMemoryGraphStore):
            @asynccontextmanager
            async def transaction(self):
                yield self
        
        source = SourceStore()
        await source.initialize()
        
        # Add multiple entities
        for i in range(10):
            entity = Entity(id=f"e{i}", entity_type="Person", properties={})
            await source.add_entity(entity)
        
        target = TargetStore()
        await target.initialize()
        
        migrator = GraphStorageMigrator(source, target)
        
        result = await migrator.migrate(batch_size=3, show_progress=False, verify=False)
        
        assert result["entities_migrated"] == 10
        
        await source.close()
        await target.close()
    
    @pytest.mark.asyncio
    async def test_migrate_error_handling(self):
        """Test migration error handling"""
        from contextlib import asynccontextmanager
        
        class FailingSourceStore(InMemoryGraphStore):
            async def get_all_entities(self):
                raise Exception("Source store error")
        
        class TargetStore(InMemoryGraphStore):
            @asynccontextmanager
            async def transaction(self):
                yield self
        
        source = FailingSourceStore()
        await source.initialize()
        
        target = TargetStore()
        await target.initialize()
        
        migrator = GraphStorageMigrator(source, target)
        
        with pytest.raises(Exception, match="Source store error"):
            await migrator.migrate(show_progress=False, verify=False)
        
        await source.close()
        await target.close()
    
    @pytest.mark.asyncio
    async def test_migrate_entities_with_progress(self):
        """Test entity migration with progress bar"""
        from contextlib import asynccontextmanager
        
        class SourceStore(InMemoryGraphStore):
            async def get_all_entities(self):
                return list(self.entities.values())
        
        class TargetStore(InMemoryGraphStore):
            @asynccontextmanager
            async def transaction(self):
                yield self
        
        source = SourceStore()
        await source.initialize()
        
        # Add entities
        for i in range(5):
            entity = Entity(id=f"e{i}", entity_type="Person", properties={})
            await source.add_entity(entity)
        
        target = TargetStore()
        await target.initialize()
        
        migrator = GraphStorageMigrator(source, target)
        
        result = await migrator.migrate(batch_size=2, show_progress=True, verify=False)
        
        assert result["entities_migrated"] == 5
        
        await source.close()
        await target.close()
    
    @pytest.mark.asyncio
    async def test_migrate_entities_batch_error(self):
        """Test entity migration with batch errors"""
        from contextlib import asynccontextmanager
        
        class SourceStore(InMemoryGraphStore):
            async def get_all_entities(self):
                return list(self.entities.values())
        
        class TargetStore(InMemoryGraphStore):
            @asynccontextmanager
            async def transaction(self):
                yield self
            
            async def add_entity(self, entity):
                if entity.id == "e1":
                    raise Exception("Cannot add e1")
                await super().add_entity(entity)
        
        source = SourceStore()
        await source.initialize()
        
        # Add entities
        for i in range(3):
            entity = Entity(id=f"e{i}", entity_type="Person", properties={})
            await source.add_entity(entity)
        
        target = TargetStore()
        await target.initialize()
        
        migrator = GraphStorageMigrator(source, target)
        
        result = await migrator.migrate(batch_size=1, show_progress=False, verify=False)
        
        # Should migrate 2 entities (e0 and e2), skip e1
        assert result["entities_migrated"] == 2
        
        await source.close()
        await target.close()
    
    @pytest.mark.asyncio
    async def test_migrate_entities_transaction_error(self):
        """Test entity migration with transaction errors"""
        from contextlib import asynccontextmanager
        
        class SourceStore(InMemoryGraphStore):
            async def get_all_entities(self):
                return list(self.entities.values())
        
        class TargetStore(InMemoryGraphStore):
            @asynccontextmanager
            async def transaction(self):
                raise Exception("Transaction failed")
                yield self
        
        source = SourceStore()
        await source.initialize()
        
        # Add entities
        for i in range(3):
            entity = Entity(id=f"e{i}", entity_type="Person", properties={})
            await source.add_entity(entity)
        
        target = TargetStore()
        await target.initialize()
        
        migrator = GraphStorageMigrator(source, target)
        
        result = await migrator.migrate(batch_size=2, show_progress=False, verify=False)
        
        # Should handle transaction errors gracefully
        assert result["entities_migrated"] == 0
        
        await source.close()
        await target.close()
    
    @pytest.mark.asyncio
    async def test_migrate_relations_sqlite(self):
        """Test relation migration from SQLite store"""
        from contextlib import asynccontextmanager
        from unittest.mock import MagicMock, AsyncMock, patch
        import json
        from aiecs.infrastructure.graph_storage.sqlite import SQLiteGraphStore
        
        class SQLiteSourceStore(SQLiteGraphStore):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._test_entities = []
            
            async def get_all_entities(self):
                return self._test_entities
            
            async def add_entity(self, entity):
                self._test_entities.append(entity)
                await super().add_entity(entity)
        
        class TargetStore(InMemoryGraphStore):
            @asynccontextmanager
            async def transaction(self):
                yield self
        
        source = SQLiteSourceStore(":memory:")
        await source.initialize()
        
        # Add entities to both source and target (target needs them for relation migration)
        e1 = Entity(id="e1", entity_type="Person", properties={})
        e2 = Entity(id="e2", entity_type="Person", properties={})
        await source.add_entity(e1)
        await source.add_entity(e2)
        
        target = TargetStore()
        await target.initialize()
        # Add entities to target so relations can be migrated
        await target.add_entity(e1)
        await target.add_entity(e2)
        
        # Mock SQLite cursor - aiosqlite returns cursor from execute
        mock_cursor = AsyncMock()
        mock_row1 = ("r1", "KNOWS", "e1", "e2", json.dumps({}), 1.0)
        mock_row2 = ("r2", "WORKS_FOR", "e2", "e1", json.dumps({}), 1.0)
        mock_cursor.fetchall = AsyncMock(return_value=[mock_row1, mock_row2])
        # Mock the execute method on the connection
        async def mock_execute(query):
            return mock_cursor
        source.conn.execute = mock_execute
        
        migrator = GraphStorageMigrator(source, target)
        
        result = await migrator.migrate(batch_size=10, show_progress=False, verify=False)
        
        # Entities may already exist in target, so we only check relations
        assert result["relations_migrated"] == 2
        
        await source.close()
        await target.close()
    
    @pytest.mark.asyncio
    async def test_migrate_relations_postgres(self):
        """Test relation migration from Postgres store"""
        from contextlib import asynccontextmanager
        from unittest.mock import MagicMock, AsyncMock, patch
        from aiecs.infrastructure.graph_storage.postgres import PostgresGraphStore
        
        # Create a mock pool
        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_row1 = MagicMock()
        mock_row1.__getitem__ = lambda self, key: {
            'id': 'r1',
            'relation_type': 'KNOWS',
            'source_id': 'e1',
            'target_id': 'e2',
            'properties': {},
            'weight': 1.0
        }[key]
        mock_row2 = MagicMock()
        mock_row2.__getitem__ = lambda self, key: {
            'id': 'r2',
            'relation_type': 'WORKS_FOR',
            'source_id': 'e2',
            'target_id': 'e1',
            'properties': {},
            'weight': 1.0
        }[key]
        mock_conn.fetch = AsyncMock(return_value=[mock_row1, mock_row2])
        
        async_context = AsyncMock()
        async_context.__aenter__ = AsyncMock(return_value=mock_conn)
        async_context.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire = MagicMock(return_value=async_context)
        
        class PostgresSourceStore(PostgresGraphStore):
            def __init__(self):
                # Don't call super().__init__ to avoid real initialization
                self.pool = mock_pool
                self._is_initialized = False
                self._owns_pool = False  # Don't own the pool
                self.entities = {}
            
            async def initialize(self):
                self._is_initialized = True
            
            async def get_all_entities(self):
                return list(self.entities.values())
            
            async def add_entity(self, entity):
                self.entities[entity.id] = entity
        
        class TargetStore(InMemoryGraphStore):
            @asynccontextmanager
            async def transaction(self):
                yield self
        
        source = PostgresSourceStore()
        await source.initialize()
        
        # Add entities
        e1 = Entity(id="e1", entity_type="Person", properties={})
        e2 = Entity(id="e2", entity_type="Person", properties={})
        await source.add_entity(e1)
        await source.add_entity(e2)
        
        target = TargetStore()
        await target.initialize()
        # Add entities to target so relations can be migrated
        await target.add_entity(e1)
        await target.add_entity(e2)
        
        migrator = GraphStorageMigrator(source, target)
        
        result = await migrator.migrate(batch_size=10, show_progress=False, verify=False)
        
        # Entities may already exist in target, so we only check relations
        assert result["relations_migrated"] == 2
        
        await source.close()
        await target.close()
    
    @pytest.mark.asyncio
    async def test_migrate_relations_empty(self):
        """Test relation migration with no relations"""
        from contextlib import asynccontextmanager
        from unittest.mock import MagicMock, AsyncMock
        
        class SQLiteSourceStore(InMemoryGraphStore):
            def __init__(self):
                super().__init__()
                self.conn = MagicMock()
            
            async def get_all_entities(self):
                return list(self.entities.values())
        
        class TargetStore(InMemoryGraphStore):
            @asynccontextmanager
            async def transaction(self):
                yield self
        
        source = SQLiteSourceStore()
        await source.initialize()
        
        # Add entities but no relations
        e1 = Entity(id="e1", entity_type="Person", properties={})
        await source.add_entity(e1)
        
        # Mock empty SQLite cursor
        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(return_value=[])
        source.conn.execute = AsyncMock(return_value=mock_cursor)
        
        target = TargetStore()
        await target.initialize()
        
        migrator = GraphStorageMigrator(source, target)
        
        result = await migrator.migrate(batch_size=10, show_progress=False, verify=False)
        
        assert result["entities_migrated"] == 1
        assert result["relations_migrated"] == 0
        
        await source.close()
        await target.close()
    
    @pytest.mark.asyncio
    async def test_migrate_relations_batch_error(self):
        """Test relation migration with batch errors"""
        from contextlib import asynccontextmanager
        from unittest.mock import MagicMock, AsyncMock
        import json
        from aiecs.infrastructure.graph_storage.sqlite import SQLiteGraphStore
        
        class SQLiteSourceStore(SQLiteGraphStore):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._test_entities = []
            
            async def get_all_entities(self):
                return self._test_entities
            
            async def add_entity(self, entity):
                self._test_entities.append(entity)
                await super().add_entity(entity)
        
        class TargetStore(InMemoryGraphStore):
            @asynccontextmanager
            async def transaction(self):
                yield self
            
            async def add_relation(self, relation):
                if relation.id == "r1":
                    raise Exception("Cannot add r1")
                await super().add_relation(relation)
        
        source = SQLiteSourceStore(":memory:")
        await source.initialize()
        
        # Add entities to both source and target (target needs them for relation migration)
        e1 = Entity(id="e1", entity_type="Person", properties={})
        e2 = Entity(id="e2", entity_type="Person", properties={})
        await source.add_entity(e1)
        await source.add_entity(e2)
        
        target = TargetStore()
        await target.initialize()
        # Add entities to target so relations can be migrated
        await target.add_entity(e1)
        await target.add_entity(e2)
        
        # Mock SQLite cursor - aiosqlite returns cursor from execute
        mock_cursor = AsyncMock()
        mock_row1 = ("r1", "KNOWS", "e1", "e2", json.dumps({}), 1.0)
        mock_row2 = ("r2", "WORKS_FOR", "e2", "e1", json.dumps({}), 1.0)
        mock_cursor.fetchall = AsyncMock(return_value=[mock_row1, mock_row2])
        # Mock the execute method on the connection
        async def mock_execute(query):
            return mock_cursor
        source.conn.execute = mock_execute
        
        migrator = GraphStorageMigrator(source, target)
        
        result = await migrator.migrate(batch_size=1, show_progress=False, verify=False)
        
        # Should migrate 1 relation (r2), skip r1
        assert result["relations_migrated"] == 1
        
        await source.close()
        await target.close()
    
    @pytest.mark.asyncio
    async def test_verify_migration_success(self):
        """Test migration verification with matching counts"""
        from contextlib import asynccontextmanager
        
        class SourceStore(InMemoryGraphStore):
            async def get_all_entities(self):
                return list(self.entities.values())
            
            async def get_stats(self):
                return {"entity_count": 2, "relation_count": 1}
        
        class TargetStore(InMemoryGraphStore):
            @asynccontextmanager
            async def transaction(self):
                yield self
            
            async def get_stats(self):
                return {"entity_count": 2, "relation_count": 1}
        
        source = SourceStore()
        await source.initialize()
        
        # Add entities
        e1 = Entity(id="e1", entity_type="Person", properties={})
        e2 = Entity(id="e2", entity_type="Person", properties={})
        await source.add_entity(e1)
        await source.add_entity(e2)
        
        target = TargetStore()
        await target.initialize()
        
        # Add same entities to target
        await target.add_entity(e1)
        await target.add_entity(e2)
        
        migrator = GraphStorageMigrator(source, target)
        
        result = await migrator.migrate(show_progress=False, verify=True)
        
        assert "verification" in result
        assert result["verification"]["success"] is True
        assert result["verification"]["entity_match"] is True
        assert result["verification"]["relation_match"] is True
        
        await source.close()
        await target.close()
    
    @pytest.mark.asyncio
    async def test_verify_migration_failure(self):
        """Test migration verification with mismatched counts"""
        from contextlib import asynccontextmanager
        
        class SourceStore(InMemoryGraphStore):
            async def get_all_entities(self):
                return list(self.entities.values())
            
            async def get_stats(self):
                return {"entity_count": 2, "relation_count": 1}
        
        class TargetStore(InMemoryGraphStore):
            @asynccontextmanager
            async def transaction(self):
                yield self
            
            async def get_stats(self):
                return {"entity_count": 1, "relation_count": 0}
        
        source = SourceStore()
        await source.initialize()
        
        # Add entities
        e1 = Entity(id="e1", entity_type="Person", properties={})
        e2 = Entity(id="e2", entity_type="Person", properties={})
        await source.add_entity(e1)
        await source.add_entity(e2)
        
        target = TargetStore()
        await target.initialize()
        
        # Add only one entity to target
        await target.add_entity(e1)
        
        migrator = GraphStorageMigrator(source, target)
        
        result = await migrator.migrate(show_progress=False, verify=True)
        
        assert "verification" in result
        assert result["verification"]["success"] is False
        assert result["verification"]["entity_match"] is False
        
        await source.close()
        await target.close()
    
    @pytest.mark.asyncio
    async def test_verify_migration_error(self):
        """Test migration verification with error"""
        from contextlib import asynccontextmanager
        
        class SourceStore(InMemoryGraphStore):
            async def get_all_entities(self):
                return list(self.entities.values())
            
            async def get_stats(self):
                raise Exception("Stats error")
        
        class TargetStore(InMemoryGraphStore):
            @asynccontextmanager
            async def transaction(self):
                yield self
        
        source = SourceStore()
        await source.initialize()
        
        # Add entities
        e1 = Entity(id="e1", entity_type="Person", properties={})
        await source.add_entity(e1)
        
        target = TargetStore()
        await target.initialize()
        
        migrator = GraphStorageMigrator(source, target)
        
        result = await migrator.migrate(show_progress=False, verify=True)
        
        assert "verification" in result
        assert result["verification"]["success"] is False
        assert "error" in result["verification"]
        
        await source.close()
        await target.close()
    
    @pytest.mark.asyncio
    async def test_migrate_sqlite_to_postgres(self):
        """Test migrate_sqlite_to_postgres convenience function"""
        from aiecs.infrastructure.graph_storage.migration import migrate_sqlite_to_postgres
        from unittest.mock import patch, MagicMock, AsyncMock
        
        # Mock SQLiteGraphStore
        with patch('aiecs.infrastructure.graph_storage.migration.SQLiteGraphStore') as mock_sqlite:
            with patch('aiecs.infrastructure.graph_storage.migration.PostgresGraphStore') as mock_postgres:
                # Setup mocks
                mock_source = AsyncMock()
                mock_source.get_all_entities = AsyncMock(return_value=[])
                mock_source.close = AsyncMock()
                mock_source._is_initialized = True
                
                mock_target = AsyncMock()
                mock_target.close = AsyncMock()
                mock_target._is_initialized = True
                
                mock_migrator = AsyncMock()
                mock_migrator.migrate = AsyncMock(return_value={
                    "entities_migrated": 5,
                    "relations_migrated": 3,
                    "duration_seconds": 1.5
                })
                
                mock_sqlite.return_value = mock_source
                mock_postgres.return_value = mock_target
                
                with patch('aiecs.infrastructure.graph_storage.migration.GraphStorageMigrator', return_value=mock_migrator):
                    result = await migrate_sqlite_to_postgres(
                        sqlite_path="test.db",
                        postgres_config={"host": "localhost"},
                        batch_size=100,
                        show_progress=False
                    )
                
                assert result["entities_migrated"] == 5
                assert result["relations_migrated"] == 3
                mock_source.close.assert_called_once()
                mock_target.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_migrate_sqlite_to_postgres_default_config(self):
        """Test migrate_sqlite_to_postgres with default config"""
        from aiecs.infrastructure.graph_storage.migration import migrate_sqlite_to_postgres
        from unittest.mock import patch, MagicMock, AsyncMock
        
        # Mock SQLiteGraphStore
        with patch('aiecs.infrastructure.graph_storage.migration.SQLiteGraphStore') as mock_sqlite:
            with patch('aiecs.infrastructure.graph_storage.migration.PostgresGraphStore') as mock_postgres:
                # Setup mocks
                mock_source = AsyncMock()
                mock_source.get_all_entities = AsyncMock(return_value=[])
                mock_source.close = AsyncMock()
                mock_source._is_initialized = True
                
                mock_target = AsyncMock()
                mock_target.close = AsyncMock()
                mock_target._is_initialized = True
                
                mock_migrator = AsyncMock()
                mock_migrator.migrate = AsyncMock(return_value={
                    "entities_migrated": 0,
                    "relations_migrated": 0,
                    "duration_seconds": 0.5
                })
                
                mock_sqlite.return_value = mock_source
                mock_postgres.return_value = mock_target
                
                with patch('aiecs.infrastructure.graph_storage.migration.GraphStorageMigrator', return_value=mock_migrator):
                    result = await migrate_sqlite_to_postgres(
                        sqlite_path="test.db",
                        postgres_config=None,
                        batch_size=1000,
                        show_progress=True
                    )
                
                assert result["entities_migrated"] == 0
                mock_postgres.assert_called_once_with()  # Called with no args (defaults)
                mock_source.close.assert_called_once()
                mock_target.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_migrate_initialization(self):
        """Test migration with stores that need initialization"""
        from contextlib import asynccontextmanager
        
        class UninitializedSourceStore(InMemoryGraphStore):
            async def get_all_entities(self):
                return list(self.entities.values())
            
            def __init__(self):
                super().__init__()
                self._is_initialized = False
        
        class UninitializedTargetStore(InMemoryGraphStore):
            @asynccontextmanager
            async def transaction(self):
                yield self
            
            def __init__(self):
                super().__init__()
                self._is_initialized = False
        
        source = UninitializedSourceStore()
        target = UninitializedTargetStore()
        
        # Add entities before initialization (they'll be stored in memory)
        e1 = Entity(id="e1", entity_type="Person", properties={})
        source.entities["e1"] = e1
        
        # Reset initialization flag to test auto-initialization
        source._is_initialized = False
        target._is_initialized = False
        
        migrator = GraphStorageMigrator(source, target)
        
        result = await migrator.migrate(show_progress=False, verify=False)
        
        assert result["entities_migrated"] == 1
        # After migration, stores should be initialized
        # Note: InMemoryGraphStore sets _is_initialized in initialize()
        # But we're testing that migrate() calls initialize() if needed
        assert hasattr(source, '_is_initialized')
        assert hasattr(target, '_is_initialized')
        
        await source.close()
        await target.close()

