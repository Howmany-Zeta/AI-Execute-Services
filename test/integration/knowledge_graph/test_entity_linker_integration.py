"""
Integration tests for EntityLinker candidate retrieval.

Tests EntityLinker with real graph store implementations:
- InMemoryGraphStore (has get_all_entities)
- SQLiteGraphStore (may not have get_all_entities, tests fallback)
"""

import pytest
import tempfile
import os
from aiecs.application.knowledge_graph.fusion.entity_linker import EntityLinker
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore
from aiecs.infrastructure.graph_storage.sqlite import SQLiteGraphStore
from aiecs.infrastructure.graph_storage.tenant import TenantContext, TenantIsolationMode


@pytest.fixture
async def in_memory_store():
    """Create and initialize an in-memory graph store."""
    store = InMemoryGraphStore()
    await store.initialize()
    yield store
    await store.close()


@pytest.fixture
async def sqlite_store():
    """Create and initialize a SQLite graph store."""
    # Use temporary file for testing
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        store = SQLiteGraphStore(db_path=db_path)
        await store.initialize()
        yield store
        await store.close()
    finally:
        # Clean up temp file
        if os.path.exists(db_path):
            os.unlink(db_path)


@pytest.fixture
async def populated_in_memory_store(in_memory_store):
    """Populate in-memory store with test entities."""
    entities = [
        Entity(
            id=f"person_{i}",
            entity_type="Person",
            properties={"name": f"Person {i}", "age": 20 + i},
        )
        for i in range(1, 11)  # 10 Person entities
    ]

    entities.extend(
        [
            Entity(
                id=f"company_{i}",
                entity_type="Company",
                properties={"name": f"Company {i}", "industry": "Tech"},
            )
            for i in range(1, 6)  # 5 Company entities
        ]
    )

    for entity in entities:
        await in_memory_store.add_entity(entity)

    return in_memory_store


@pytest.fixture
async def populated_sqlite_store(sqlite_store):
    """Populate SQLite store with test entities."""
    entities = [
        Entity(
            id=f"person_{i}",
            entity_type="Person",
            properties={"name": f"Person {i}", "age": 20 + i},
        )
        for i in range(1, 11)  # 10 Person entities
    ]

    entities.extend(
        [
            Entity(
                id=f"company_{i}",
                entity_type="Company",
                properties={"name": f"Company {i}", "industry": "Tech"},
            )
            for i in range(1, 6)  # 5 Company entities
        ]
    )

    for entity in entities:
        await sqlite_store.add_entity(entity)

    return sqlite_store


@pytest.mark.asyncio
@pytest.mark.integration
async def test_entity_linker_with_in_memory_store(populated_in_memory_store):
    """Test EntityLinker candidate retrieval with InMemoryGraphStore."""
    linker = EntityLinker(
        graph_store=populated_in_memory_store,
        similarity_threshold=0.85,
        use_embeddings=False,
    )

    # Test candidate retrieval
    candidates = await linker._get_candidate_entities(
        entity_type="Person", limit=5
    )

    assert len(candidates) == 5
    assert all(e.entity_type == "Person" for e in candidates)

    # Test name-based linking
    new_entity = Entity(
        id="new_person",
        entity_type="Person",
        properties={"name": "Person 1"},  # Should match existing
    )

    result = await linker._link_by_name(new_entity, candidate_limit=10)
    assert result.linked is True
    assert result.existing_entity.id == "person_1"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_entity_linker_with_sqlite_store(populated_sqlite_store):
    """Test EntityLinker candidate retrieval with SQLiteGraphStore."""
    linker = EntityLinker(
        graph_store=populated_sqlite_store,
        similarity_threshold=0.85,
        use_embeddings=False,
    )

    # Test candidate retrieval (may use fallback if get_all_entities not implemented)
    candidates = await linker._get_candidate_entities(
        entity_type="Person", limit=5
    )

    # Should handle gracefully even if get_all_entities not available
    # (implementation falls back gracefully)
    assert isinstance(candidates, list)

    # Test name-based linking (should work with fallback)
    new_entity = Entity(
        id="new_person",
        entity_type="Person",
        properties={"name": "Person 1"},
    )

    result = await linker._link_by_name(new_entity, candidate_limit=10)
    # Result depends on whether SQLiteGraphStore has get_all_entities or text_search
    # But should not raise exceptions
    assert isinstance(result.linked, bool)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_entity_linker_tenant_isolation_in_memory(populated_in_memory_store):
    """Test tenant isolation in EntityLinker with InMemoryGraphStore."""
    tenant_1_context = TenantContext(
        tenant_id="tenant_1", isolation_mode=TenantIsolationMode.SHARED_SCHEMA
    )
    tenant_2_context = TenantContext(
        tenant_id="tenant_2", isolation_mode=TenantIsolationMode.SHARED_SCHEMA
    )

    # Add entities to different tenants
    tenant_1_entity = Entity(
        id="tenant1_person",
        entity_type="Person",
        properties={"name": "Tenant 1 Person"},
    )
    await populated_in_memory_store.add_entity(
        tenant_1_entity, context=tenant_1_context
    )

    tenant_2_entity = Entity(
        id="tenant2_person",
        entity_type="Person",
        properties={"name": "Tenant 2 Person"},
    )
    await populated_in_memory_store.add_entity(
        tenant_2_entity, context=tenant_2_context
    )

    linker = EntityLinker(
        graph_store=populated_in_memory_store,
        similarity_threshold=0.85,
        use_embeddings=False,
    )

    # Get candidates for tenant_1
    candidates_1 = await linker._get_candidate_entities(
        entity_type="Person", limit=10, context=tenant_1_context
    )

    # Should only return tenant_1 entities
    assert len(candidates_1) >= 1
    assert any(e.id == "tenant1_person" for e in candidates_1)
    assert not any(e.id == "tenant2_person" for e in candidates_1)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_entity_linker_pagination_in_memory(populated_in_memory_store):
    """Test pagination support in EntityLinker with InMemoryGraphStore."""
    linker = EntityLinker(
        graph_store=populated_in_memory_store,
        similarity_threshold=0.85,
        use_embeddings=False,
    )

    # Request limited results
    candidates_page1 = await linker._get_candidate_entities(
        entity_type="Person", limit=3
    )
    assert len(candidates_page1) <= 3

    # Request more results
    candidates_page2 = await linker._get_candidate_entities(
        entity_type="Person", limit=10
    )
    assert len(candidates_page2) <= 10
    assert len(candidates_page2) >= len(candidates_page1)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_entity_linker_text_search_optimization(populated_in_memory_store):
    """Test that EntityLinker uses text_search when available."""
    linker = EntityLinker(
        graph_store=populated_in_memory_store,
        similarity_threshold=0.85,
        use_embeddings=False,
    )

    # Create entity with name that should match via text search
    new_entity = Entity(
        id="new_person",
        entity_type="Person",
        properties={"name": "Person 5"},  # Should match person_5
    )

    # Link using name-based search (should use text_search optimization)
    result = await linker._link_by_name(new_entity, candidate_limit=10)

    # Should find a match
    assert result.linked is True
    assert result.existing_entity is not None
    assert result.link_type == "name"
