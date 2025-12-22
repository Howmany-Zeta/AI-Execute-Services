"""
Unit tests for vector search functionality

Tests vector search across different graph storage backends.
"""

import pytest
import numpy as np
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore
from aiecs.infrastructure.graph_storage.sqlite import SQLiteGraphStore


@pytest.fixture
async def inmemory_store_with_embeddings():
    """Fixture with in-memory store containing entities with embeddings"""
    store = InMemoryGraphStore()
    await store.initialize()
    
    # Add entities with embeddings representing different concepts
    # Entity 1: [1, 0, 0] - represents "concept A"
    e1 = Entity(
        id="e1",
        entity_type="Document",
        properties={"title": "Document A"},
        embedding=[1.0, 0.0, 0.0]
    )
    
    # Entity 2: [0.9, 0.1, 0.0] - similar to "concept A"
    e2 = Entity(
        id="e2",
        entity_type="Document",
        properties={"title": "Document A2"},
        embedding=[0.9, 0.1, 0.0]
    )
    
    # Entity 3: [0, 1, 0] - represents "concept B"
    e3 = Entity(
        id="e3",
        entity_type="Document",
        properties={"title": "Document B"},
        embedding=[0.0, 1.0, 0.0]
    )
    
    # Entity 4: [0, 0, 1] - represents "concept C"
    e4 = Entity(
        id="e4",
        entity_type="Article",
        properties={"title": "Article C"},
        embedding=[0.0, 0.0, 1.0]
    )
    
    # Entity 5: no embedding
    e5 = Entity(
        id="e5",
        entity_type="Document",
        properties={"title": "Document No Embedding"}
    )
    
    await store.add_entity(e1)
    await store.add_entity(e2)
    await store.add_entity(e3)
    await store.add_entity(e4)
    await store.add_entity(e5)
    
    yield store
    await store.close()


@pytest.fixture
async def sqlite_store_with_embeddings():
    """Fixture with SQLite store containing entities with embeddings"""
    store = SQLiteGraphStore(":memory:")
    await store.initialize()
    
    # Add same entities as inmemory store
    e1 = Entity(id="e1", entity_type="Document", properties={"title": "Document A"}, embedding=[1.0, 0.0, 0.0])
    e2 = Entity(id="e2", entity_type="Document", properties={"title": "Document A2"}, embedding=[0.9, 0.1, 0.0])
    e3 = Entity(id="e3", entity_type="Document", properties={"title": "Document B"}, embedding=[0.0, 1.0, 0.0])
    e4 = Entity(id="e4", entity_type="Article", properties={"title": "Article C"}, embedding=[0.0, 0.0, 1.0])
    e5 = Entity(id="e5", entity_type="Document", properties={"title": "Document No Embedding"})
    
    await store.add_entity(e1)
    await store.add_entity(e2)
    await store.add_entity(e3)
    await store.add_entity(e4)
    await store.add_entity(e5)
    
    yield store
    await store.close()


class TestVectorSearchInMemory:
    """Test vector search on in-memory store"""
    
    @pytest.mark.asyncio
    async def test_basic_vector_search(self, inmemory_store_with_embeddings):
        """Test basic vector search returns relevant results"""
        # Search for entities similar to [1, 0, 0]
        query_embedding = [1.0, 0.0, 0.0]
        
        results = await inmemory_store_with_embeddings.vector_search(
            query_embedding=query_embedding,
            max_results=5
        )
        
        # Should return results
        assert len(results) > 0
        
        # First result should be e1 (exact match)
        assert results[0][0].id == "e1"
        assert results[0][1] > 0.99  # Very high similarity
        
        # Second result should be e2 (similar)
        assert results[1][0].id == "e2"
        assert results[1][1] > 0.9  # High similarity
    
    @pytest.mark.asyncio
    async def test_vector_search_with_threshold(self, inmemory_store_with_embeddings):
        """Test vector search with similarity threshold"""
        query_embedding = [1.0, 0.0, 0.0]
        
        # High threshold should only return very similar entities
        results = await inmemory_store_with_embeddings.vector_search(
            query_embedding=query_embedding,
            score_threshold=0.95,
            max_results=10
        )
        
        # Should only return e1 (and possibly e2 if similarity > 0.95)
        assert len(results) <= 2
        assert results[0][0].id == "e1"
        
        # All results should have similarity >= 0.95
        for entity, score in results:
            assert score >= 0.95
    
    @pytest.mark.asyncio
    async def test_vector_search_with_entity_type_filter(self, inmemory_store_with_embeddings):
        """Test vector search with entity type filtering"""
        query_embedding = [0.0, 0.0, 1.0]
        
        # Search only in "Article" type
        results = await inmemory_store_with_embeddings.vector_search(
            query_embedding=query_embedding,
            entity_type="Article",
            max_results=10
        )
        
        # Should only return e4 (Article type)
        assert len(results) == 1
        assert results[0][0].id == "e4"
        assert results[0][0].entity_type == "Article"
    
    @pytest.mark.asyncio
    async def test_vector_search_max_results(self, inmemory_store_with_embeddings):
        """Test that max_results parameter is respected"""
        query_embedding = [0.5, 0.5, 0.5]
        
        # Request only 2 results
        results = await inmemory_store_with_embeddings.vector_search(
            query_embedding=query_embedding,
            max_results=2
        )
        
        # Should return exactly 2 results (we have 4 entities with embeddings)
        assert len(results) == 2
    
    @pytest.mark.asyncio
    async def test_vector_search_sorted_by_similarity(self, inmemory_store_with_embeddings):
        """Test that results are sorted by similarity descending"""
        query_embedding = [1.0, 0.0, 0.0]
        
        results = await inmemory_store_with_embeddings.vector_search(
            query_embedding=query_embedding,
            max_results=10
        )
        
        # Scores should be in descending order
        scores = [score for _, score in results]
        assert scores == sorted(scores, reverse=True)
    
    @pytest.mark.asyncio
    async def test_vector_search_empty_query(self, inmemory_store_with_embeddings):
        """Test that empty query embedding raises error"""
        with pytest.raises(ValueError, match="cannot be empty"):
            await inmemory_store_with_embeddings.vector_search(
                query_embedding=[],
                max_results=10
            )
    
    @pytest.mark.asyncio
    async def test_vector_search_no_embeddings(self):
        """Test vector search when no entities have embeddings"""
        store = InMemoryGraphStore()
        await store.initialize()
        
        # Add entity without embedding
        e1 = Entity(id="e1", entity_type="Test", properties={})
        await store.add_entity(e1)
        
        results = await store.vector_search(
            query_embedding=[1.0, 0.0, 0.0],
            max_results=10
        )
        
        # Should return empty list
        assert len(results) == 0
        
        await store.close()


class TestVectorSearchSQLite:
    """Test vector search on SQLite store"""
    
    @pytest.mark.asyncio
    async def test_basic_vector_search(self, sqlite_store_with_embeddings):
        """Test basic vector search returns relevant results"""
        query_embedding = [1.0, 0.0, 0.0]
        
        results = await sqlite_store_with_embeddings.vector_search(
            query_embedding=query_embedding,
            max_results=5
        )
        
        # Should return results
        assert len(results) > 0
        
        # First result should be e1 (exact match)
        assert results[0][0].id == "e1"
        assert results[0][1] > 0.99  # Very high similarity
    
    @pytest.mark.asyncio
    async def test_vector_search_with_threshold(self, sqlite_store_with_embeddings):
        """Test vector search with similarity threshold"""
        query_embedding = [1.0, 0.0, 0.0]
        
        results = await sqlite_store_with_embeddings.vector_search(
            query_embedding=query_embedding,
            score_threshold=0.95,
            max_results=10
        )
        
        # All results should have similarity >= 0.95
        for entity, score in results:
            assert score >= 0.95
    
    @pytest.mark.asyncio
    async def test_vector_search_with_entity_type_filter(self, sqlite_store_with_embeddings):
        """Test vector search with entity type filtering"""
        query_embedding = [0.0, 0.0, 1.0]
        
        results = await sqlite_store_with_embeddings.vector_search(
            query_embedding=query_embedding,
            entity_type="Article",
            max_results=10
        )
        
        # Should only return e4
        assert len(results) == 1
        assert results[0][0].id == "e4"
    
    @pytest.mark.asyncio
    async def test_vector_search_persistence(self):
        """Test that embeddings persist across sessions"""
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db') as f:
            db_path = f.name
        
        try:
            # Session 1: Add entity with embedding
            store1 = SQLiteGraphStore(db_path)
            await store1.initialize()
            
            e1 = Entity(id="e1", entity_type="Doc", properties={}, embedding=[1.0, 0.0, 0.0])
            await store1.add_entity(e1)
            await store1.close()
            
            # Session 2: Search using embedding
            store2 = SQLiteGraphStore(db_path)
            await store2.initialize()
            
            results = await store2.vector_search(
                query_embedding=[1.0, 0.0, 0.0],
                max_results=10
            )
            
            # Should find the entity
            assert len(results) == 1
            assert results[0][0].id == "e1"
            
            await store2.close()
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)


class TestVectorSearchConsistency:
    """Test that vector search behaves consistently across backends"""
    
    @pytest.mark.asyncio
    async def test_inmemory_and_sqlite_produce_similar_results(
        self, inmemory_store_with_embeddings, sqlite_store_with_embeddings
    ):
        """Test that both backends return similar results for same query"""
        query_embedding = [1.0, 0.0, 0.0]
        
        inmemory_results = await inmemory_store_with_embeddings.vector_search(
            query_embedding=query_embedding,
            max_results=3
        )
        
        sqlite_results = await sqlite_store_with_embeddings.vector_search(
            query_embedding=query_embedding,
            max_results=3
        )
        
        # Should return same number of results
        assert len(inmemory_results) == len(sqlite_results)
        
        # Should have same entity IDs (order might differ slightly due to floating point)
        inmemory_ids = {entity.id for entity, _ in inmemory_results}
        sqlite_ids = {entity.id for entity, _ in sqlite_results}
        assert inmemory_ids == sqlite_ids
        
        # Similarity scores should be very close (within 0.01)
        for i in range(len(inmemory_results)):
            inmemory_score = inmemory_results[i][1]
            sqlite_score = sqlite_results[i][1]
            assert abs(inmemory_score - sqlite_score) < 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

