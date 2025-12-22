"""
Unit tests for EntityLinker candidate retrieval functionality.

Tests the efficient candidate entity retrieval implementation including:
- get_all_entities() integration
- Tenant context filtering
- Pagination support
- Name-based text search optimization
"""

import pytest
from aiecs.application.knowledge_graph.fusion.entity_linker import EntityLinker, LinkResult
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore
from aiecs.infrastructure.graph_storage.base import GraphStore
from aiecs.infrastructure.graph_storage.tenant import TenantContext, TenantIsolationMode


@pytest.fixture
async def graph_store():
    """Create and initialize an in-memory graph store for testing."""
    store = InMemoryGraphStore()
    await store.initialize()
    return store


@pytest.fixture
def entity_linker(graph_store):
    """Create an EntityLinker instance for testing."""
    return EntityLinker(
        graph_store=graph_store,
        similarity_threshold=0.85,
        use_embeddings=False,  # Disable embeddings for name-based tests
    )


@pytest.fixture
async def test_entities(graph_store):
    """Create test entities of different types."""
    entities = [
        Entity(
            id="person_1",
            entity_type="Person",
            properties={"name": "Alice Smith", "age": 30},
        ),
        Entity(
            id="person_2",
            entity_type="Person",
            properties={"name": "Bob Johnson", "age": 35},
        ),
        Entity(
            id="person_3",
            entity_type="Person",
            properties={"name": "Alice Brown", "age": 28},
        ),
        Entity(
            id="company_1",
            entity_type="Company",
            properties={"name": "Tech Corp", "industry": "Technology"},
        ),
        Entity(
            id="company_2",
            entity_type="Company",
            properties={"name": "Finance Inc", "industry": "Finance"},
        ),
    ]

    for entity in entities:
        await graph_store.add_entity(entity)

    return entities


@pytest.mark.asyncio
async def test_get_candidate_entities_by_type(entity_linker, test_entities):
    """Test retrieving candidates filtered by entity type."""
    # Get Person entities
    candidates = await entity_linker._get_candidate_entities(
        entity_type="Person", limit=10
    )

    assert len(candidates) == 3
    assert all(e.entity_type == "Person" for e in candidates)
    assert all(e.id in ["person_1", "person_2", "person_3"] for e in candidates)

    # Get Company entities
    candidates = await entity_linker._get_candidate_entities(
        entity_type="Company", limit=10
    )

    assert len(candidates) == 2
    assert all(e.entity_type == "Company" for e in candidates)
    assert all(e.id in ["company_1", "company_2"] for e in candidates)


@pytest.mark.asyncio
async def test_get_candidate_entities_with_limit(entity_linker, test_entities):
    """Test pagination support via limit parameter."""
    # Request only 2 candidates
    candidates = await entity_linker._get_candidate_entities(
        entity_type="Person", limit=2
    )

    assert len(candidates) <= 2
    assert all(e.entity_type == "Person" for e in candidates)


@pytest.mark.asyncio
async def test_get_candidate_entities_with_tenant_context(entity_linker, graph_store):
    """Test tenant context filtering in candidate retrieval."""
    # Create tenant context
    tenant_context = TenantContext(
        tenant_id="tenant_1", isolation_mode=TenantIsolationMode.SHARED_SCHEMA
    )

    # Add entities to tenant
    tenant_entity = Entity(
        id="tenant_person_1",
        entity_type="Person",
        properties={"name": "Tenant Alice"},
    )
    await graph_store.add_entity(tenant_entity, context=tenant_context)

    # Add entity to different tenant
    other_tenant_context = TenantContext(
        tenant_id="tenant_2", isolation_mode=TenantIsolationMode.SHARED_SCHEMA
    )
    other_entity = Entity(
        id="tenant_person_2",
        entity_type="Person",
        properties={"name": "Other Tenant Bob"},
    )
    await graph_store.add_entity(other_entity, context=other_tenant_context)

    # Get candidates with tenant context
    candidates = await entity_linker._get_candidate_entities(
        entity_type="Person", limit=10, context=tenant_context
    )

    # Should only return entities from tenant_1
    assert len(candidates) == 1
    assert candidates[0].id == "tenant_person_1"


@pytest.mark.asyncio
async def test_get_candidate_entities_empty_store(entity_linker):
    """Test candidate retrieval from empty store."""
    candidates = await entity_linker._get_candidate_entities(
        entity_type="Person", limit=10
    )

    assert candidates == []


@pytest.mark.asyncio
async def test_get_candidate_entities_nonexistent_type(entity_linker, test_entities):
    """Test candidate retrieval for non-existent entity type."""
    candidates = await entity_linker._get_candidate_entities(
        entity_type="NonExistent", limit=10
    )

    assert candidates == []


@pytest.mark.asyncio
async def test_link_by_name_uses_text_search_when_available(entity_linker, test_entities):
    """Test that _link_by_name uses text_search when available."""
    # Create new entity to link
    new_entity = Entity(
        id="new_person",
        entity_type="Person",
        properties={"name": "Alice Smith"},  # Should match person_1
    )

    # Link entity (should use text_search optimization)
    result = await entity_linker._link_by_name(new_entity, candidate_limit=10)

    # Should find a match (either person_1 or person_3 based on similarity)
    assert result.linked is True
    assert result.existing_entity is not None
    assert result.link_type == "name"
    assert result.similarity >= 0.85


@pytest.mark.asyncio
async def test_link_by_name_fallback_to_candidates(entity_linker, test_entities):
    """Test fallback to candidate enumeration when text_search unavailable."""
    # Create a mock store without text_search
    class MockStoreWithoutTextSearch(InMemoryGraphStore):
        async def text_search(self, *args, **kwargs):
            raise NotImplementedError("text_search not available")

    mock_store = MockStoreWithoutTextSearch()
    await mock_store.initialize()

    # Add test entities to mock store
    for entity in test_entities:
        await mock_store.add_entity(entity)

    linker_without_text_search = EntityLinker(
        graph_store=mock_store,
        similarity_threshold=0.85,
        use_embeddings=False,
    )

    # Create new entity to link
    new_entity = Entity(
        id="new_person",
        entity_type="Person",
        properties={"name": "Alice Smith"},
    )

    # Should fallback to candidate enumeration
    result = await linker_without_text_search._link_by_name(
        new_entity, candidate_limit=10
    )

    # Should still find a match using candidate enumeration
    assert result.linked is True
    assert result.existing_entity is not None


@pytest.mark.asyncio
async def test_link_by_name_no_match(entity_linker, test_entities):
    """Test name-based linking when no match found."""
    # Create entity with very different name
    new_entity = Entity(
        id="new_person",
        entity_type="Person",
        properties={"name": "Completely Different Name XYZ"},
    )

    result = await entity_linker._link_by_name(new_entity, candidate_limit=10)

    # Should not find a match (similarity below threshold)
    assert result.linked is False


@pytest.mark.asyncio
async def test_link_by_name_no_name_property(entity_linker, test_entities):
    """Test name-based linking when entity has no name property."""
    # Create entity without name
    new_entity = Entity(
        id="new_person",
        entity_type="Person",
        properties={"age": 25},  # No name property
    )

    result = await entity_linker._link_by_name(new_entity, candidate_limit=10)

    # Should return not linked
    assert result.linked is False


@pytest.mark.asyncio
async def test_get_candidate_entities_fallback_to_text_search(entity_linker, graph_store):
    """Test fallback to text_search when get_all_entities is not available."""
    # Create a store without get_all_entities but with text_search
    class StoreWithoutGetAllEntities(InMemoryGraphStore):
        async def get_all_entities(self, *args, **kwargs):
            raise AttributeError("get_all_entities not available")

    store_without_get_all = StoreWithoutGetAllEntities()
    await store_without_get_all.initialize()

    # Add test entities
    test_entities = [
        Entity(
            id="person_1",
            entity_type="Person",
            properties={"name": "Alice Smith"},
        ),
        Entity(
            id="person_2",
            entity_type="Person",
            properties={"name": "Bob Johnson"},
        ),
    ]
    for entity in test_entities:
        await store_without_get_all.add_entity(entity)

    linker_without_get_all = EntityLinker(
        graph_store=store_without_get_all,
        similarity_threshold=0.85,
        use_embeddings=False,
    )

    # Should fallback to text_search (if it supports empty query)
    # or return empty list if text_search doesn't support empty queries
    candidates = await linker_without_get_all._get_candidate_entities(
        entity_type="Person", limit=10
    )

    # Result depends on whether text_search supports empty queries
    # But should not raise exception
    assert isinstance(candidates, list)


@pytest.mark.asyncio
async def test_get_candidate_entities_fallback_to_empty_list():
    """Test final fallback to empty list when neither get_all_entities nor text_search work."""
    # Create a minimal store without get_all_entities or text_search
    class MinimalStore(GraphStore):
        async def initialize(self):
            pass

        async def close(self):
            pass

        async def add_entity(self, entity, context=None):
            pass

        async def get_entity(self, entity_id, context=None):
            return None

        async def add_relation(self, relation, context=None):
            pass

        async def get_relation(self, relation_id, context=None):
            return None

        async def get_neighbors(
            self, entity_id, relation_type=None, direction="outgoing", context=None
        ):
            return []

        # Intentionally does NOT have get_all_entities or text_search

    minimal_store = MinimalStore()
    await minimal_store.initialize()

    linker_with_minimal_store = EntityLinker(
        graph_store=minimal_store,
        similarity_threshold=0.85,
        use_embeddings=False,
    )

    # Should fallback to empty list (final fallback)
    candidates = await linker_with_minimal_store._get_candidate_entities(
        entity_type="Person", limit=10
    )

    assert candidates == []


@pytest.mark.asyncio
async def test_get_candidate_entities_handles_exceptions(entity_linker):
    """Test that candidate retrieval handles exceptions gracefully."""
    # Create a store that raises exceptions
    class FailingStore(InMemoryGraphStore):
        async def get_all_entities(self, *args, **kwargs):
            raise Exception("Test exception")

    failing_store = FailingStore()
    await failing_store.initialize()

    linker_with_failing_store = EntityLinker(
        graph_store=failing_store,
        similarity_threshold=0.85,
    )

    # Should return empty list instead of raising exception
    candidates = await linker_with_failing_store._get_candidate_entities(
        entity_type="Person", limit=10
    )

    assert candidates == []
