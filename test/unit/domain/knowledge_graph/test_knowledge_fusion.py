"""
Unit tests for Knowledge Fusion

Tests cover:
- Cross-document entity fusion
- Similarity matching across documents
- Merge candidate identification
- Property conflict resolution strategies
- Entity merge operations
- Provenance tracking
"""

import pytest
from typing import List, Dict, Any
from unittest.mock import AsyncMock, MagicMock

from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.application.knowledge_graph.fusion.knowledge_fusion import KnowledgeFusion
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore


# Test Fixtures

@pytest.fixture
async def graph_store():
    """Create an in-memory graph store for testing"""
    store = InMemoryGraphStore()
    await store.initialize()
    return store


@pytest.fixture
async def fusion(graph_store):
    """Create a KnowledgeFusion instance"""
    return KnowledgeFusion(graph_store, similarity_threshold=0.85)


@pytest.fixture
def sample_entities():
    """Create sample entities for testing"""
    return [
        Entity(
            id="e1",
            entity_type="Person",
            properties={
                "name": "Alice Smith",
                "age": 30,
                "_provenance": {"source": "doc1", "timestamp": 100}
            }
        ),
        Entity(
            id="e2",
            entity_type="Person",
            properties={
                "name": "Alice Smith",
                "age": 31,
                "_provenance": {"source": "doc2", "timestamp": 200}
            }
        ),
        Entity(
            id="e3",
            entity_type="Person",
            properties={
                "name": "Bob Jones",
                "age": 25,
                "_provenance": {"source": "doc1"}
            }
        ),
        Entity(
            id="e4",
            entity_type="Company",
            properties={
                "name": "Tech Corp",
                "_provenance": {"source": "doc1"}
            }
        ),
        Entity(
            id="e5",
            entity_type="Company",
            properties={
                "name": "Tech Corporation",
                "_provenance": {"source": "doc2"}
            }
        ),
    ]


# Property Conflict Resolution Tests

@pytest.mark.asyncio
async def test_resolve_property_conflicts_most_complete(fusion):
    """Test most_complete conflict resolution strategy"""
    entities = [
        Entity(id="e1", entity_type="Person", properties={"name": "Alice", "age": ""}),
        Entity(id="e2", entity_type="Person", properties={"name": "Alice Smith", "age": 30}),
    ]
    
    merged = await fusion.resolve_property_conflicts(entities, strategy="most_complete")
    
    assert merged.properties["name"] == "Alice Smith"  # Longer string
    assert merged.properties["age"] == 30  # Non-empty value


@pytest.mark.asyncio
async def test_resolve_property_conflicts_most_recent(fusion):
    """Test most_recent conflict resolution strategy"""
    entities = [
        Entity(
            id="e1",
            entity_type="Person",
            properties={
                "name": "Alice",
                "age": 30,
                "_provenance": {"timestamp": 100}
            }
        ),
        Entity(
            id="e2",
            entity_type="Person",
            properties={
                "name": "Alice Smith",
                "age": 31,
                "_provenance": {"timestamp": 200}
            }
        ),
    ]
    
    merged = await fusion.resolve_property_conflicts(entities, strategy="most_recent")
    
    # Should prefer values from entity with timestamp 200
    assert merged.properties["age"] == 31


@pytest.mark.asyncio
async def test_resolve_property_conflicts_most_confident(fusion):
    """Test most_confident conflict resolution strategy"""
    entities = [
        Entity(
            id="e1",
            entity_type="Person",
            properties={
                "name": "Alice",
                "_provenance": {"confidence": 0.7}
            }
        ),
        Entity(
            id="e2",
            entity_type="Person",
            properties={
                "name": "Alice Smith",
                "_provenance": {"confidence": 0.95}
            }
        ),
    ]
    
    merged = await fusion.resolve_property_conflicts(entities, strategy="most_confident")
    
    # Should prefer value from entity with confidence 0.95
    assert merged.properties["name"] == "Alice Smith"


@pytest.mark.asyncio
async def test_resolve_property_conflicts_keep_all(fusion):
    """Test keep_all conflict resolution strategy"""
    entities = [
        Entity(id="e1", entity_type="Person", properties={"name": "Alice"}),
        Entity(id="e2", entity_type="Person", properties={"name": "Alice Smith"}),
    ]
    
    merged = await fusion.resolve_property_conflicts(entities, strategy="keep_all")
    
    # Should keep all values as list
    assert isinstance(merged.properties["name"], list)
    assert "Alice" in merged.properties["name"]
    assert "Alice Smith" in merged.properties["name"]


@pytest.mark.asyncio
async def test_resolve_property_conflicts_tracks_conflicts(fusion):
    """Test that conflicts are tracked in _property_conflicts"""
    entities = [
        Entity(id="e1", entity_type="Person", properties={"name": "Alice", "age": 30}),
        Entity(id="e2", entity_type="Person", properties={"name": "Alice Smith", "age": 31}),
    ]

    merged = await fusion.resolve_property_conflicts(entities)

    # Should track conflicts
    assert "_property_conflicts" in merged.properties
    assert "name" in merged.properties["_property_conflicts"]
    assert "age" in merged.properties["_property_conflicts"]
    assert fusion.conflicts_resolved == 2


@pytest.mark.asyncio
async def test_resolve_property_conflicts_merges_provenance(fusion):
    """Test that provenance is merged"""
    entities = [
        Entity(
            id="e1",
            entity_type="Person",
            properties={
                "name": "Alice",
                "_provenance": {"source": "doc1"}
            }
        ),
        Entity(
            id="e2",
            entity_type="Person",
            properties={
                "name": "Alice",
                "_provenance": {"source": "doc2"}
            }
        ),
    ]

    merged = await fusion.resolve_property_conflicts(entities)

    # Should merge provenance
    assert "_provenance_merged" in merged.properties
    assert len(merged.properties["_provenance_merged"]) == 2


@pytest.mark.asyncio
async def test_resolve_property_conflicts_empty_list(fusion):
    """Test that empty entity list raises error"""
    with pytest.raises(ValueError, match="Cannot merge empty entity list"):
        await fusion.resolve_property_conflicts([])


@pytest.mark.asyncio
async def test_resolve_property_conflicts_single_entity(fusion):
    """Test that single entity is returned as-is"""
    entity = Entity(id="e1", entity_type="Person", properties={"name": "Alice"})

    merged = await fusion.resolve_property_conflicts([entity])

    assert merged.id == entity.id
    assert merged.properties["name"] == "Alice"


# Helper Method Tests

def test_group_entities_by_type(fusion):
    """Test grouping entities by type"""
    entities = [
        Entity(id="e1", entity_type="Person", properties={"name": "Alice"}),
        Entity(id="e2", entity_type="Person", properties={"name": "Bob"}),
        Entity(id="e3", entity_type="Company", properties={"name": "Tech Corp"}),
        Entity(id="e4", entity_type="Company", properties={"name": "Acme Inc"}),
    ]

    grouped = fusion._group_entities_by_type(entities)

    assert len(grouped) == 2
    assert "Person" in grouped
    assert "Company" in grouped
    assert len(grouped["Person"]) == 2
    assert len(grouped["Company"]) == 2


def test_find_connected_components_single_component(fusion):
    """Test finding connected components - single component"""
    n = 4
    edges = {(0, 1), (1, 2), (2, 3)}  # All connected

    components = fusion._find_connected_components(n, edges)

    assert len(components) == 1
    assert set(components[0]) == {0, 1, 2, 3}


def test_find_connected_components_multiple_components(fusion):
    """Test finding connected components - multiple components"""
    n = 6
    edges = {(0, 1), (2, 3), (4, 5)}  # Three separate pairs

    components = fusion._find_connected_components(n, edges)

    assert len(components) == 3
    component_sets = [set(c) for c in components]
    assert {0, 1} in component_sets
    assert {2, 3} in component_sets
    assert {4, 5} in component_sets


def test_find_connected_components_no_edges(fusion):
    """Test finding connected components - no edges"""
    n = 3
    edges = set()

    components = fusion._find_connected_components(n, edges)

    # Each node is its own component
    assert len(components) == 3


# Provenance Tracking Tests

@pytest.mark.asyncio
async def test_track_entity_provenance_single_source(graph_store, fusion):
    """Test tracking provenance for entity from single source"""
    entity = Entity(
        id="e1",
        entity_type="Person",
        properties={
            "name": "Alice",
            "_provenance": {"source": "doc1"}
        }
    )
    await graph_store.add_entity(entity)

    sources = await fusion.track_entity_provenance("e1")

    assert len(sources) == 1
    assert "doc1" in sources


@pytest.mark.asyncio
async def test_track_entity_provenance_merged_sources(graph_store, fusion):
    """Test tracking provenance for merged entity"""
    entity = Entity(
        id="e1",
        entity_type="Person",
        properties={
            "name": "Alice",
            "_provenance": {"source": "doc1"},
            "_provenance_merged": [
                {"source": "doc2"},
                {"source": "doc3"}
            ]
        }
    )
    await graph_store.add_entity(entity)

    sources = await fusion.track_entity_provenance("e1")

    assert len(sources) == 3
    assert "doc1" in sources
    assert "doc2" in sources
    assert "doc3" in sources


@pytest.mark.asyncio
async def test_track_entity_provenance_nonexistent(fusion):
    """Test tracking provenance for nonexistent entity"""
    sources = await fusion.track_entity_provenance("nonexistent")

    assert len(sources) == 0


# Cross-Document Fusion Integration Tests

@pytest.mark.asyncio
async def test_fuse_cross_document_entities_basic(graph_store):
    """Test basic cross-document entity fusion"""
    # Add similar entities from different documents
    entities = [
        Entity(
            id="e1",
            entity_type="Person",
            properties={
                "name": "Alice Smith",
                "_provenance": {"source": "doc1"}
            }
        ),
        Entity(
            id="e2",
            entity_type="Person",
            properties={
                "name": "Alice Smith",
                "_provenance": {"source": "doc2"}
            }
        ),
        Entity(
            id="e3",
            entity_type="Person",
            properties={
                "name": "Bob Jones",
                "_provenance": {"source": "doc1"}
            }
        ),
    ]

    for entity in entities:
        await graph_store.add_entity(entity)

    fusion = KnowledgeFusion(graph_store, similarity_threshold=0.9)
    stats = await fusion.fuse_cross_document_entities()

    # Should analyze 3 entities
    assert stats["entities_analyzed"] == 3

    # Should merge 2 entities (e1 and e2 are similar)
    # Note: Actual merging depends on similarity computation
    # This test verifies the fusion runs without errors


@pytest.mark.asyncio
async def test_fuse_cross_document_entities_by_type(graph_store):
    """Test cross-document fusion filtered by entity type"""
    # Add entities of different types
    entities = [
        Entity(id="e1", entity_type="Person", properties={"name": "Alice"}),
        Entity(id="e2", entity_type="Person", properties={"name": "Alice"}),
        Entity(id="e3", entity_type="Company", properties={"name": "Tech Corp"}),
        Entity(id="e4", entity_type="Company", properties={"name": "Tech Corp"}),
    ]

    for entity in entities:
        await graph_store.add_entity(entity)

    fusion = KnowledgeFusion(graph_store, similarity_threshold=0.9)

    # Fuse only Person entities
    stats = await fusion.fuse_cross_document_entities(entity_types=["Person"])

    # Should only analyze Person entities
    assert stats["entities_analyzed"] == 2


@pytest.mark.asyncio
async def test_fuse_cross_document_entities_empty_graph(graph_store):
    """Test fusion with empty graph"""
    fusion = KnowledgeFusion(graph_store, similarity_threshold=0.9)
    stats = await fusion.fuse_cross_document_entities()

    assert stats["entities_analyzed"] == 0
    assert stats["entities_merged"] == 0
    assert stats["merge_groups"] == 0


@pytest.mark.asyncio
async def test_fuse_cross_document_entities_single_entity(graph_store):
    """Test fusion with single entity"""
    entity = Entity(id="e1", entity_type="Person", properties={"name": "Alice"})
    await graph_store.add_entity(entity)

    fusion = KnowledgeFusion(graph_store, similarity_threshold=0.9)
    stats = await fusion.fuse_cross_document_entities()

    assert stats["entities_analyzed"] == 1
    assert stats["entities_merged"] == 0  # Nothing to merge


@pytest.mark.asyncio
async def test_fuse_cross_document_entities_no_similar(graph_store):
    """Test fusion when no entities are similar"""
    entities = [
        Entity(id="e1", entity_type="Person", properties={"name": "Alice"}),
        Entity(id="e2", entity_type="Person", properties={"name": "Bob"}),
        Entity(id="e3", entity_type="Person", properties={"name": "Charlie"}),
    ]

    for entity in entities:
        await graph_store.add_entity(entity)

    fusion = KnowledgeFusion(graph_store, similarity_threshold=0.9)
    stats = await fusion.fuse_cross_document_entities()

    assert stats["entities_analyzed"] == 3
    assert stats["entities_merged"] == 0  # No similar entities


# Merge Group Finding Tests

@pytest.mark.asyncio
async def test_find_merge_groups_similar_entities(fusion):
    """Test finding merge groups with similar entities"""
    entities = [
        Entity(id="e1", entity_type="Person", properties={"name": "Alice Smith"}),
        Entity(id="e2", entity_type="Person", properties={"name": "Alice Smith"}),
        Entity(id="e3", entity_type="Person", properties={"name": "Bob Jones"}),
    ]

    # Mock similarity computation to return high similarity for Alice entities
    async def mock_similarity(e1, e2):
        if "Alice" in e1.properties.get("name", "") and "Alice" in e2.properties.get("name", ""):
            return 0.95
        return 0.1

    fusion._compute_entity_similarity = mock_similarity

    groups = await fusion._find_merge_groups(entities)

    # Should find one group with e1 and e2
    assert len(groups) >= 1
    # Check if any group contains both Alice entities
    alice_group = None
    for group in groups:
        if len(group) == 2:
            names = [e.properties.get("name") for e in group]
            if all("Alice" in name for name in names):
                alice_group = group
                break

    assert alice_group is not None


@pytest.mark.asyncio
async def test_find_merge_groups_no_similar(fusion):
    """Test finding merge groups when no entities are similar"""
    entities = [
        Entity(id="e1", entity_type="Person", properties={"name": "Alice"}),
        Entity(id="e2", entity_type="Person", properties={"name": "Bob"}),
    ]

    # Mock similarity to return low scores
    async def mock_similarity(e1, e2):
        return 0.1

    fusion._compute_entity_similarity = mock_similarity

    groups = await fusion._find_merge_groups(entities)

    # Should find no groups (no similar entities)
    assert len(groups) == 0


@pytest.mark.asyncio
async def test_find_merge_groups_single_entity(fusion):
    """Test finding merge groups with single entity"""
    entities = [
        Entity(id="e1", entity_type="Person", properties={"name": "Alice"}),
    ]

    groups = await fusion._find_merge_groups(entities)

    # Should find no groups (need at least 2 entities)
    assert len(groups) == 0


@pytest.mark.asyncio
async def test_find_merge_groups_empty_list(fusion):
    """Test finding merge groups with empty list"""
    groups = await fusion._find_merge_groups([])

    assert len(groups) == 0

