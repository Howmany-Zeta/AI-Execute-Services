"""
Tests for embedding configuration in knowledge graph builder
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import List

from aiecs.application.knowledge_graph.builder.graph_builder import GraphBuilder
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.llm.protocols import LLMClientProtocol


class MockEmbeddingClient:
    """Mock LLM client that implements embedding generation"""

    def __init__(self):
        self.provider_name = "mock_embedder"
        self.get_embeddings_called = False
        self.texts_embedded = []

    async def get_embeddings(
        self, texts: List[str], model: str = None, **kwargs
    ) -> List[List[float]]:
        """Generate mock embeddings"""
        self.get_embeddings_called = True
        self.texts_embedded = texts
        # Return simple mock embeddings (3-dimensional for testing)
        return [[0.1 * i, 0.2 * i, 0.3 * i] for i in range(len(texts))]

    async def generate_text(self, messages, model, **kwargs):
        """Mock text generation (not used in these tests)"""
        return MagicMock(content="mock response")

    async def close(self):
        """Mock close"""
        pass


class MockEntityExtractor:
    """Mock entity extractor"""

    async def extract_entities(self, text: str, entity_types=None):
        """Return mock entities"""
        return [
            Entity(
                id="person_1",
                entity_type="Person",
                properties={"name": "Alice"},
            ),
            Entity(
                id="company_1",
                entity_type="Company",
                properties={"name": "TechCorp"},
            ),
        ]


class MockRelationExtractor:
    """Mock relation extractor"""

    async def extract_relations(self, text: str, entities):
        """Return mock relations"""
        if len(entities) >= 2:
            return [
                Relation(
                    id="rel_1",
                    source_id=entities[0].id,
                    target_id=entities[1].id,
                    relation_type="WORKS_AT",
                    properties={},
                )
            ]
        return []


@pytest.mark.asyncio
async def test_graph_builder_with_embedding_client():
    """Test that GraphBuilder generates embeddings when embedding client is provided"""
    # Setup
    graph_store = InMemoryGraphStore()
    await graph_store.initialize()

    entity_extractor = MockEntityExtractor()
    relation_extractor = MockRelationExtractor()
    embedding_client = MockEmbeddingClient()

    # Create builder with embedding client
    builder = GraphBuilder(
        graph_store=graph_store,
        entity_extractor=entity_extractor,
        relation_extractor=relation_extractor,
        embedding_client=embedding_client,
    )

    # Build graph from text
    result = await builder.build_from_text(
        text="Alice works at TechCorp",
        source="test_doc",
    )

    # Verify embeddings were generated
    assert embedding_client.get_embeddings_called
    assert len(embedding_client.texts_embedded) == 2  # 2 entities
    assert "Person: Alice" in embedding_client.texts_embedded
    assert "Company: TechCorp" in embedding_client.texts_embedded

    # Verify entities were stored with embeddings
    alice = await graph_store.get_entity("person_1")
    assert alice is not None
    assert alice.embedding is not None
    assert len(alice.embedding) == 3  # 3-dimensional mock embedding
    assert alice.embedding == [0.0, 0.0, 0.0]  # First entity gets [0.0, 0.0, 0.0]

    techcorp = await graph_store.get_entity("company_1")
    assert techcorp is not None
    assert techcorp.embedding is not None
    assert len(techcorp.embedding) == 3
    assert techcorp.embedding == [0.1, 0.2, 0.3]  # Second entity gets [0.1, 0.2, 0.3]

    # Verify build result
    assert result.entities_added == 2
    assert result.relations_added == 1

    await graph_store.close()


@pytest.mark.asyncio
async def test_graph_builder_without_embedding_client():
    """Test that GraphBuilder works without embedding client (backward compatibility)"""
    # Setup
    graph_store = InMemoryGraphStore()
    await graph_store.initialize()

    entity_extractor = MockEntityExtractor()
    relation_extractor = MockRelationExtractor()

    # Create builder WITHOUT embedding client
    builder = GraphBuilder(
        graph_store=graph_store,
        entity_extractor=entity_extractor,
        relation_extractor=relation_extractor,
    )

    # Build graph from text
    result = await builder.build_from_text(
        text="Alice works at TechCorp",
        source="test_doc",
    )

    # Verify entities were stored WITHOUT embeddings
    alice = await graph_store.get_entity("person_1")
    assert alice is not None
    assert alice.embedding is None  # No embedding client, so no embeddings

    # Verify build result
    assert result.entities_added == 2
    assert result.relations_added == 1

    await graph_store.close()

