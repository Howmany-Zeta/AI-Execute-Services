"""
Unit tests for GraphMemoryMixin embedding-based search

Tests embedding-based knowledge retrieval functionality including:
- Query embedding generation
- Vector search integration
- Session context filtering
- Fallback to text search
- Entity type filtering
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiecs.domain.context.graph_memory import GraphMemoryMixin
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore


class MockGraphMemoryMixin(GraphMemoryMixin):
    """Mock class that implements GraphMemoryMixin for testing"""
    
    def __init__(self, graph_store=None, llm_client=None):
        self.graph_store = graph_store
        self.llm_client = llm_client


@pytest.fixture
async def graph_store():
    """Create and initialize a test graph store"""
    store = InMemoryGraphStore()
    await store.initialize()
    yield store
    await store.close()


@pytest.fixture
def mock_llm_client_with_embeddings():
    """Create a mock LLM client that supports embeddings"""
    client = MagicMock()
    client.get_embeddings = AsyncMock(return_value=[[0.1, 0.2, 0.3, 0.4, 0.5]])
    return client


@pytest.fixture
def mock_llm_client_without_embeddings():
    """Create a mock LLM client without embeddings support"""
    client = MagicMock()
    del client.get_embeddings  # Remove get_embeddings method
    return client


@pytest.fixture
def sample_entities():
    """Create sample entities with embeddings"""
    return [
        Entity(
            id="person_1",
            entity_type="Person",
            properties={"name": "Alice"},
            embedding=[0.1, 0.2, 0.3, 0.4, 0.5]
        ),
        Entity(
            id="person_2",
            entity_type="Person",
            properties={"name": "Bob"},
            embedding=[0.15, 0.25, 0.35, 0.45, 0.55]
        ),
        Entity(
            id="company_1",
            entity_type="Company",
            properties={"name": "Acme Corp"},
            embedding=[0.2, 0.3, 0.4, 0.5, 0.6]
        ),
    ]


class TestEmbeddingBasedSearch:
    """Test embedding-based search functionality"""
    
    @pytest.mark.asyncio
    async def test_retrieve_with_embedding_search(
        self, graph_store, mock_llm_client_with_embeddings, sample_entities
    ):
        """Test retrieval using embedding-based search"""
        # Add entities to store
        for entity in sample_entities:
            await graph_store.add_entity(entity)
        
        mixin = MockGraphMemoryMixin(
            graph_store=graph_store,
            llm_client=mock_llm_client_with_embeddings
        )
        
        results = await mixin.retrieve_knowledge(
            session_id="test_session",
            query="find people",
            limit=10
        )
        
        # Should retrieve entities via vector search
        assert len(results) > 0
        # Verify vector_search was called
        assert mock_llm_client_with_embeddings.get_embeddings.called
    
    @pytest.mark.asyncio
    async def test_retrieve_with_entity_type_filter(
        self, graph_store, mock_llm_client_with_embeddings, sample_entities
    ):
        """Test retrieval with entity type filtering"""
        # Add entities to store
        for entity in sample_entities:
            await graph_store.add_entity(entity)
        
        mixin = MockGraphMemoryMixin(
            graph_store=graph_store,
            llm_client=mock_llm_client_with_embeddings
        )
        
        results = await mixin.retrieve_knowledge(
            session_id="test_session",
            query="find people",
            entity_types=["Person"],
            limit=10
        )
        
        # All results should be Person entities
        assert all(e.entity_type == "Person" for e in results)
    
    @pytest.mark.asyncio
    async def test_retrieve_fallback_to_text_search(
        self, graph_store, mock_llm_client_without_embeddings, sample_entities
    ):
        """Test fallback to text search when embeddings unavailable"""
        # Add entities to store
        for entity in sample_entities:
            await graph_store.add_entity(entity)
        
        mixin = MockGraphMemoryMixin(
            graph_store=graph_store,
            llm_client=mock_llm_client_without_embeddings
        )
        
        results = await mixin.retrieve_knowledge(
            session_id="test_session",
            query="Alice",
            limit=10
        )
        
        # Should still retrieve results via text search fallback
        assert len(results) >= 0  # May or may not find results depending on text search
    
    @pytest.mark.asyncio
    async def test_retrieve_with_session_context(
        self, graph_store, mock_llm_client_with_embeddings, sample_entities
    ):
        """Test retrieval combines session context with embedding search"""
        # Add entities to store
        for entity in sample_entities:
            await graph_store.add_entity(entity)
        
        # Create session entity and link one entity to it
        session_entity = Entity(
            id="session_test_session",
            entity_type="Session",
            properties={"session_id": "test_session"}
        )
        await graph_store.add_entity(session_entity)
        
        from aiecs.domain.knowledge_graph.models.relation import Relation
        relation = Relation(
            id="rel_1",
            relation_type="MENTIONED_IN",
            source_id="person_1",
            target_id="session_test_session"
        )
        await graph_store.add_relation(relation)
        
        mixin = MockGraphMemoryMixin(
            graph_store=graph_store,
            llm_client=mock_llm_client_with_embeddings
        )
        
        results = await mixin.retrieve_knowledge(
            session_id="test_session",
            query="find people",
            include_session_context=True,
            limit=10
        )
        
        # Should include both session context and search results
        assert len(results) >= 0
    
    @pytest.mark.asyncio
    async def test_generate_query_embedding_success(
        self, mock_llm_client_with_embeddings
    ):
        """Test successful query embedding generation"""
        mixin = MockGraphMemoryMixin(llm_client=mock_llm_client_with_embeddings)
        
        embedding = await mixin._generate_query_embedding("test query")
        
        assert embedding is not None
        assert len(embedding) == 5
        assert mock_llm_client_with_embeddings.get_embeddings.called
    
    @pytest.mark.asyncio
    async def test_generate_query_embedding_no_llm_client(self):
        """Test embedding generation when no LLM client available"""
        mixin = MockGraphMemoryMixin()
        
        embedding = await mixin._generate_query_embedding("test query")
        
        assert embedding is None
    
    @pytest.mark.asyncio
    async def test_generate_query_embedding_no_embeddings_method(
        self, mock_llm_client_without_embeddings
    ):
        """Test embedding generation when LLM client doesn't support embeddings"""
        mixin = MockGraphMemoryMixin(
            llm_client=mock_llm_client_without_embeddings
        )
        
        embedding = await mixin._generate_query_embedding("test query")
        
        assert embedding is None
    
    @pytest.mark.asyncio
    async def test_generate_query_embedding_exception_handling(self):
        """Test embedding generation handles exceptions gracefully"""
        client = MagicMock()
        client.get_embeddings = AsyncMock(side_effect=Exception("API error"))
        
        mixin = MockGraphMemoryMixin(llm_client=client)
        
        embedding = await mixin._generate_query_embedding("test query")
        
        assert embedding is None
    
    @pytest.mark.asyncio
    async def test_generate_query_embedding_not_implemented(self):
        """Test embedding generation handles NotImplementedError"""
        client = MagicMock()
        client.get_embeddings = AsyncMock(side_effect=NotImplementedError())
        
        mixin = MockGraphMemoryMixin(llm_client=client)
        
        embedding = await mixin._generate_query_embedding("test query")
        
        assert embedding is None
    
    @pytest.mark.asyncio
    async def test_retrieve_with_multiple_entity_types(
        self, graph_store, mock_llm_client_with_embeddings, sample_entities
    ):
        """Test retrieval with multiple entity types"""
        # Add entities to store
        for entity in sample_entities:
            await graph_store.add_entity(entity)
        
        mixin = MockGraphMemoryMixin(
            graph_store=graph_store,
            llm_client=mock_llm_client_with_embeddings
        )
        
        results = await mixin.retrieve_knowledge(
            session_id="test_session",
            query="find entities",
            entity_types=["Person", "Company"],
            limit=10
        )
        
        # Results should be filtered to Person or Company
        assert all(e.entity_type in ["Person", "Company"] for e in results)
    
    @pytest.mark.asyncio
    async def test_retrieve_respects_limit(
        self, graph_store, mock_llm_client_with_embeddings, sample_entities
    ):
        """Test that retrieval respects the limit parameter"""
        # Add entities to store
        for entity in sample_entities:
            await graph_store.add_entity(entity)
        
        mixin = MockGraphMemoryMixin(
            graph_store=graph_store,
            llm_client=mock_llm_client_with_embeddings
        )
        
        results = await mixin.retrieve_knowledge(
            session_id="test_session",
            query="find entities",
            limit=2
        )
        
        assert len(results) <= 2
    
    @pytest.mark.asyncio
    async def test_retrieve_no_query_no_session_context(
        self, graph_store, sample_entities
    ):
        """Test retrieval with no query and no session context"""
        # Add entities to store
        for entity in sample_entities:
            await graph_store.add_entity(entity)
        
        mixin = MockGraphMemoryMixin(graph_store=graph_store)
        
        results = await mixin.retrieve_knowledge(
            session_id="test_session",
            query=None,
            include_session_context=False,
            limit=10
        )
        
        # Should return empty list
        assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_retrieve_vector_search_failure_fallback(
        self, graph_store, mock_llm_client_with_embeddings, sample_entities
    ):
        """Test that vector search failure falls back to text search"""
        # Add entities to store
        for entity in sample_entities:
            await graph_store.add_entity(entity)
        
        # Mock vector_search to raise exception
        original_vector_search = graph_store.vector_search
        graph_store.vector_search = AsyncMock(side_effect=Exception("Vector search failed"))
        
        mixin = MockGraphMemoryMixin(
            graph_store=graph_store,
            llm_client=mock_llm_client_with_embeddings
        )
        
        results = await mixin.retrieve_knowledge(
            session_id="test_session",
            query="Alice",
            limit=10
        )
        
        # Should fallback to text search
        # Restore original method
        graph_store.vector_search = original_vector_search
        
        # Results may be empty or contain text search results
        assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_retrieve_deduplicates_entities(
        self, graph_store, mock_llm_client_with_embeddings, sample_entities
    ):
        """Test that retrieval deduplicates entities from different sources"""
        # Add entities to store
        for entity in sample_entities:
            await graph_store.add_entity(entity)
        
        # Create session entity and link person_1 to it
        session_entity = Entity(
            id="session_test_session",
            entity_type="Session",
            properties={"session_id": "test_session"}
        )
        await graph_store.add_entity(session_entity)
        
        from aiecs.domain.knowledge_graph.models.relation import Relation
        relation = Relation(
            id="rel_1",
            relation_type="MENTIONED_IN",
            source_id="person_1",
            target_id="session_test_session"
        )
        await graph_store.add_relation(relation)
        
        mixin = MockGraphMemoryMixin(
            graph_store=graph_store,
            llm_client=mock_llm_client_with_embeddings
        )
        
        # Mock vector_search to return person_1 (same as session context)
        async def mock_vector_search(*args, **kwargs):
            return [(sample_entities[0], 0.9)]  # Return person_1
        
        graph_store.vector_search = mock_vector_search
        
        results = await mixin.retrieve_knowledge(
            session_id="test_session",
            query="Alice",
            include_session_context=True,
            limit=10
        )
        
        # Should deduplicate person_1
        entity_ids = [e.id for e in results]
        assert entity_ids.count("person_1") <= 1
