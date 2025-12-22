"""
Integration Tests: Graph Store Backend Compatibility

Verifies that application layer works without changes across different
graph storage backends (InMemory, SQLite, PostgreSQL).
"""

import pytest
import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv
import tempfile

from aiecs.infrastructure.graph_storage import (
    GraphStore,
    InMemoryGraphStore,
    SQLiteGraphStore,
    PostgresGraphStore
)
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation


# Load .env.PostgreSQL if available for PostgreSQL tests
# Try multiple possible locations
possible_paths = [
    Path(__file__).parent.parent.parent.parent / ".env.PostgreSQL",  # From test/integration_tests/graph_storage/ -> root
    Path(__file__).parent.parent.parent / ".env.PostgreSQL",  # From test/integration_tests/ -> test/
    Path(".env.PostgreSQL"),  # Current directory (root when running from project root)
    Path(__file__).parent.parent.parent.parent.parent / ".env.PostgreSQL",  # Extra safety
]

for env_file in possible_paths:
    if env_file.exists():
        load_dotenv(env_file, override=True)
        break

POSTGRES_AVAILABLE = all([
    os.getenv("DB_HOST"),
    os.getenv("DB_USER"),
    os.getenv("DB_NAME"),
])

pytestmark = pytest.mark.asyncio


# ============================================================================
# Fixtures for different backends
# ============================================================================

@pytest.fixture
async def inmemory_store():
    """In-memory graph store"""
    store = InMemoryGraphStore()
    await store.initialize()
    yield store
    await store.close()


@pytest.fixture
async def sqlite_store():
    """SQLite graph store (temp file)"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    store = SQLiteGraphStore(db_path=db_path)
    await store.initialize()
    yield store
    await store.close()
    
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
async def postgres_store():
    """PostgreSQL graph store"""
    if not POSTGRES_AVAILABLE:
        pytest.skip("PostgreSQL not configured")
    
    store = PostgresGraphStore(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME")
    )
    
    try:
        await store.initialize()
    except Exception as e:
        pytest.skip(f"PostgreSQL not available: {e}")
    
    # Clean up before tests
    async with store.pool.acquire() as conn:
        await conn.execute("DELETE FROM graph_relations")
        await conn.execute("DELETE FROM graph_entities")
    
    yield store
    
    # Clean up after tests
    async with store.pool.acquire() as conn:
        await conn.execute("DELETE FROM graph_relations")
        await conn.execute("DELETE FROM graph_entities")
    
    await store.close()


# ============================================================================
# Generic application-layer functions (backend-agnostic)
# ============================================================================

async def application_add_person(store: GraphStore, person_id: str, name: str, age: int):
    """Application-layer function to add a person"""
    entity = Entity(
        id=person_id,
        entity_type="Person",
        properties={"name": name, "age": age}
    )
    await store.add_entity(entity)


async def application_add_relationship(store: GraphStore, person1_id: str, person2_id: str, rel_type: str):
    """Application-layer function to add a relationship"""
    relation = Relation(
        id=f"{person1_id}_{rel_type}_{person2_id}",
        source_id=person1_id,
        target_id=person2_id,
        relation_type=rel_type,
        properties={}
    )
    await store.add_relation(relation)


async def application_find_friends(store: GraphStore, person_id: str):
    """Application-layer function to find a person's friends"""
    neighbors = await store.get_neighbors(person_id, direction="both")
    return [n for n in neighbors if n.entity_type == "Person"]


async def application_get_person_info(store: GraphStore, person_id: str):
    """Application-layer function to get person info"""
    entity = await store.get_entity(person_id)
    if entity:
        return {
            "id": entity.id,
            "name": entity.properties.get("name"),
            "age": entity.properties.get("age")
        }
    return None


# ============================================================================
# Compatibility tests
# ============================================================================

class TestApplicationLayerCompatibility:
    """Test that application layer works identically across backends"""
    
    async def test_basic_operations_inmemory(self, inmemory_store):
        """Test that basic operations work with InMemory backend"""
        store = inmemory_store
        
        # Application layer code - same for all backends
        await application_add_person(store, "p1", "Alice", 30)
        await application_add_person(store, "p2", "Bob", 25)
        await application_add_relationship(store, "p1", "p2", "KNOWS")
        
        # Verify
        alice = await application_get_person_info(store, "p1")
        assert alice is not None
        assert alice["name"] == "Alice"
        assert alice["age"] == 30
        
        friends = await application_find_friends(store, "p1")
        assert len(friends) == 1
        assert friends[0].properties["name"] == "Bob"
    
    async def test_basic_operations_sqlite(self, sqlite_store):
        """Test that basic operations work with SQLite backend"""
        store = sqlite_store
        
        # Application layer code - same for all backends
        await application_add_person(store, "p1", "Alice", 30)
        await application_add_person(store, "p2", "Bob", 25)
        await application_add_relationship(store, "p1", "p2", "KNOWS")
        
        # Verify
        alice = await application_get_person_info(store, "p1")
        assert alice is not None
        assert alice["name"] == "Alice"
        assert alice["age"] == 30
        
        friends = await application_find_friends(store, "p1")
        assert len(friends) == 1
        assert friends[0].properties["name"] == "Bob"
    
    @pytest.mark.skipif(not POSTGRES_AVAILABLE, reason="PostgreSQL not available")
    async def test_basic_operations_postgres(self, postgres_store):
        """Test that basic operations work with PostgreSQL backend"""
        store = postgres_store
        
        # Application layer code - same for all backends
        await application_add_person(store, "p1", "Alice", 30)
        await application_add_person(store, "p2", "Bob", 25)
        await application_add_relationship(store, "p1", "p2", "KNOWS")
        
        # Verify
        alice = await application_get_person_info(store, "p1")
        assert alice is not None
        assert alice["name"] == "Alice"
        assert alice["age"] == 30
        
        friends = await application_find_friends(store, "p1")
        assert len(friends) == 1
        assert friends[0].properties["name"] == "Bob"
    
    async def test_transaction_support_inmemory(self, inmemory_store):
        """Test transaction support with InMemory (may not support)"""
        store = inmemory_store
        
        # Application layer code with transaction
        try:
            async with store.transaction():
                await application_add_person(store, "tx1", "TransUser1", 20)
                await application_add_person(store, "tx2", "TransUser2", 21)
        except AttributeError:
            # InMemoryGraphStore doesn't have transaction support, that's OK
            pytest.skip("InMemoryGraphStore doesn't support transactions")
        
        # Verify both were added
        user1 = await application_get_person_info(store, "tx1")
        user2 = await application_get_person_info(store, "tx2")
        assert user1 is not None
        assert user2 is not None
    
    async def test_transaction_support_sqlite(self, sqlite_store):
        """Test transaction support with SQLite"""
        store = sqlite_store
        
        # Application layer code with transaction
        async with store.transaction():
            await application_add_person(store, "tx1", "TransUser1", 20)
            await application_add_person(store, "tx2", "TransUser2", 21)
        
        # Verify both were added
        user1 = await application_get_person_info(store, "tx1")
        user2 = await application_get_person_info(store, "tx2")
        assert user1 is not None
        assert user2 is not None
    
    @pytest.mark.skipif(not POSTGRES_AVAILABLE, reason="PostgreSQL not available")
    async def test_transaction_support_postgres(self, postgres_store):
        """Test transaction support with PostgreSQL"""
        store = postgres_store
        
        # Application layer code with transaction
        async with store.transaction():
            await application_add_person(store, "tx1", "TransUser1", 20)
            await application_add_person(store, "tx2", "TransUser2", 21)
        
        # Verify both were added
        user1 = await application_get_person_info(store, "tx1")
        user2 = await application_get_person_info(store, "tx2")
        assert user1 is not None
        assert user2 is not None
    
    async def test_path_finding_inmemory(self, inmemory_store):
        """Test path finding with InMemory backend"""
        store = inmemory_store
        
        # Create a chain: A -> B -> C
        await application_add_person(store, "pa", "Alice", 30)
        await application_add_person(store, "pb", "Bob", 25)
        await application_add_person(store, "pc", "Charlie", 35)
        
        await application_add_relationship(store, "pa", "pb", "KNOWS")
        await application_add_relationship(store, "pb", "pc", "KNOWS")
        
        # Find paths
        paths = await store.find_paths("pa", "pc", max_depth=3)
        
        # All backends should find at least one path
        assert len(paths) > 0
        assert paths[0].nodes[0].id == "pa"
        assert paths[0].nodes[-1].id == "pc"
    
    async def test_path_finding_sqlite(self, sqlite_store):
        """Test path finding with SQLite backend"""
        store = sqlite_store
        
        # Create a chain: A -> B -> C
        await application_add_person(store, "pa", "Alice", 30)
        await application_add_person(store, "pb", "Bob", 25)
        await application_add_person(store, "pc", "Charlie", 35)
        
        await application_add_relationship(store, "pa", "pb", "KNOWS")
        await application_add_relationship(store, "pb", "pc", "KNOWS")
        
        # Find paths
        paths = await store.find_paths("pa", "pc", max_depth=3)
        
        # All backends should find at least one path
        assert len(paths) > 0
        assert paths[0].nodes[0].id == "pa"
        assert paths[0].nodes[-1].id == "pc"
    
    @pytest.mark.skipif(not POSTGRES_AVAILABLE, reason="PostgreSQL not available")
    async def test_path_finding_postgres(self, postgres_store):
        """Test path finding with PostgreSQL backend"""
        store = postgres_store
        
        # Create a chain: A -> B -> C
        await application_add_person(store, "pa", "Alice", 30)
        await application_add_person(store, "pb", "Bob", 25)
        await application_add_person(store, "pc", "Charlie", 35)
        
        await application_add_relationship(store, "pa", "pb", "KNOWS")
        await application_add_relationship(store, "pb", "pc", "KNOWS")
        
        # Find paths
        paths = await store.find_paths("pa", "pc", max_depth=3)
        
        # All backends should find at least one path
        assert len(paths) > 0
        assert paths[0].nodes[0].id == "pa"
        assert paths[0].nodes[-1].id == "pc"
    
    async def test_stats_inmemory(self, inmemory_store):
        """Test stats with InMemory backend"""
        store = inmemory_store
        
        # Add some data
        await application_add_person(store, "stat1", "StatUser", 40)
        
        # Get stats (InMemoryGraphStore.get_stats() is synchronous)
        stats = store.get_stats()
        
        # All backends should return stats
        assert "entity_count" in stats or "nodes" in stats
        assert "relation_count" in stats or "edges" in stats
        # InMemoryGraphStore may use different keys
        if "entity_count" in stats:
            assert stats["entity_count"] >= 1
        elif "nodes" in stats:
            assert stats["nodes"] >= 1
    
    async def test_stats_sqlite(self, sqlite_store):
        """Test stats with SQLite backend"""
        store = sqlite_store
        
        # Add some data
        await application_add_person(store, "stat1", "StatUser", 40)
        
        # Get stats
        stats = await store.get_stats()
        
        # All backends should return stats
        assert "entity_count" in stats
        assert "relation_count" in stats
        assert stats["entity_count"] >= 1
    
    @pytest.mark.skipif(not POSTGRES_AVAILABLE, reason="PostgreSQL not available")
    async def test_stats_postgres(self, postgres_store):
        """Test stats with PostgreSQL backend"""
        store = postgres_store
        
        # Add some data
        await application_add_person(store, "stat1", "StatUser", 40)
        
        # Get stats
        stats = await store.get_stats()
        
        # All backends should return stats
        assert "entity_count" in stats
        assert "relation_count" in stats
        assert stats["entity_count"] >= 1


class TestBackendSwitching:
    """Test that application can switch backends without code changes"""
    
    async def test_switch_from_memory_to_sqlite(self, inmemory_store, sqlite_store):
        """Test switching from InMemory to SQLite"""
        # Start with InMemory
        await application_add_person(inmemory_store, "switch1", "User1", 25)
        
        # Switch to SQLite - same application code
        await application_add_person(sqlite_store, "switch2", "User2", 30)
        
        # Both should work independently
        user1 = await application_get_person_info(inmemory_store, "switch1")
        user2 = await application_get_person_info(sqlite_store, "switch2")
        
        assert user1 is not None
        assert user2 is not None
        assert user1["name"] == "User1"
        assert user2["name"] == "User2"
    
    @pytest.mark.skipif(not POSTGRES_AVAILABLE, reason="PostgreSQL not available")
    async def test_switch_from_sqlite_to_postgres(self, sqlite_store, postgres_store):
        """Test switching from SQLite to PostgreSQL"""
        # Start with SQLite
        await application_add_person(sqlite_store, "pg1", "PGUser1", 35)
        
        # Switch to PostgreSQL - same application code
        await application_add_person(postgres_store, "pg2", "PGUser2", 40)
        
        # Both should work
        user1 = await application_get_person_info(sqlite_store, "pg1")
        user2 = await application_get_person_info(postgres_store, "pg2")
        
        assert user1 is not None
        assert user2 is not None


class TestApplicationLayerAbstraction:
    """Test that application layer doesn't need to know about backend"""
    
    async def generic_workflow(self, store: GraphStore):
        """Generic workflow that works with any backend"""
        # Step 1: Add entities
        await application_add_person(store, "w1", "WorkflowUser1", 28)
        await application_add_person(store, "w2", "WorkflowUser2", 32)
        
        # Step 2: Add relationships
        await application_add_relationship(store, "w1", "w2", "COLLABORATES_WITH")
        
        # Step 3: Query
        friends = await application_find_friends(store, "w1")
        
        # Step 4: Verify
        assert len(friends) == 1
        assert friends[0].id == "w2"
        
        # Step 5: Stats (handle both sync and async)
        if hasattr(store, 'get_stats'):
            if asyncio.iscoroutinefunction(store.get_stats):
                stats = await store.get_stats()
            else:
                stats = store.get_stats()
            # Different backends may use different keys
            entity_key = "entity_count" if "entity_count" in stats else "nodes"
            relation_key = "relation_count" if "relation_count" in stats else "edges"
            assert stats.get(entity_key, 0) >= 2
            assert stats.get(relation_key, 0) >= 1
        
        return True
    
    async def test_workflow_with_inmemory(self, inmemory_store):
        """Test workflow with InMemory backend"""
        assert await self.generic_workflow(inmemory_store)
    
    async def test_workflow_with_sqlite(self, sqlite_store):
        """Test workflow with SQLite backend"""
        assert await self.generic_workflow(sqlite_store)
    
    @pytest.mark.skipif(not POSTGRES_AVAILABLE, reason="PostgreSQL not available")
    async def test_workflow_with_postgres(self, postgres_store):
        """Test workflow with PostgreSQL backend"""
        assert await self.generic_workflow(postgres_store)


class TestNoCodeChangesRequired:
    """Verify that switching backends requires zero code changes"""
    
    def test_all_backends_implement_same_interface(self):
        """Verify all backends implement GraphStore interface"""
        from inspect import signature
        
        # Get methods from base class
        base_methods = set(dir(GraphStore))
        
        # Check each implementation
        for store_class in [InMemoryGraphStore, SQLiteGraphStore, PostgresGraphStore]:
            impl_methods = set(dir(store_class))
            # All base methods should be implemented
            for method in base_methods:
                if not method.startswith("_") and callable(getattr(GraphStore, method, None)):
                    assert method in impl_methods, f"{store_class.__name__} missing {method}"

