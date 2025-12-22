"""
Integration tests for reranked search in GraphSearchTool
"""

import pytest
from aiecs.tools.knowledge_graph.graph_search_tool import GraphSearchTool
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation


@pytest.fixture
async def populated_tool():
    """Create a graph search tool with populated data"""
    tool = GraphSearchTool()
    await tool._initialize()
    
    # Add entities (use 128-dim embeddings to match query embedding generation)
    entities = [
        Entity(
            id="e1",
            entity_type="Paper",
            properties={
                "title": "Machine Learning Fundamentals",
                "abstract": "An introduction to machine learning concepts",
                "year": 2020
            },
            embedding=[0.1] * 128
        ),
        Entity(
            id="e2",
            entity_type="Paper",
            properties={
                "title": "Deep Learning for Computer Vision",
                "abstract": "Using neural networks for image recognition",
                "year": 2021
            },
            embedding=[0.2] * 128
        ),
        Entity(
            id="e3",
            entity_type="Paper",
            properties={
                "title": "Database Systems Design",
                "abstract": "Principles of relational database design",
                "year": 2019
            },
            embedding=[-0.1] * 128
        ),
        Entity(
            id="e4",
            entity_type="Author",
            properties={
                "name": "Alice Smith",
                "affiliation": "MIT"
            },
            embedding=[0.15] * 128
        ),
        Entity(
            id="e5",
            entity_type="Author",
            properties={
                "name": "Bob Johnson",
                "affiliation": "Stanford"
            },
            embedding=[0.12] * 128
        ),
    ]
    
    for entity in entities:
        await tool.graph_store.add_entity(entity)
    
    # Add relations
    relations = [
        Relation(id="r1", relation_type="AUTHORED", source_id="e4", target_id="e1"),
        Relation(id="r2", relation_type="AUTHORED", source_id="e4", target_id="e2"),
        Relation(id="r3", relation_type="AUTHORED", source_id="e5", target_id="e3"),
        Relation(id="r4", relation_type="CITES", source_id="e2", target_id="e1"),
    ]
    
    for relation in relations:
        await tool.graph_store.add_relation(relation)
    
    yield tool
    
    await tool.graph_store.close()


class TestVectorSearchReranking:
    """Test reranking for vector search"""
    
    @pytest.mark.asyncio
    async def test_vector_search_with_text_reranking(self, populated_tool):
        """Test vector search with text similarity reranking"""
        result = await populated_tool._execute(
            mode="vector",
            query="machine learning",
            max_results=3,
            enable_reranking=True,
            rerank_strategy="text",
            rerank_top_k=5
        )
        
        assert result["success"] is True
        assert result["reranked"] is True
        assert len(result["results"]) <= 3
        
        # Results should have rerank_score
        for res in result["results"]:
            assert "rerank_score" in res
            assert "original_score" in res
    
    @pytest.mark.asyncio
    async def test_vector_search_with_semantic_reranking(self, populated_tool):
        """Test vector search with semantic reranking"""
        query_embedding = [0.1] * 128
        
        result = await populated_tool._execute(
            mode="vector",
            query="machine learning",
            query_embedding=query_embedding,
            max_results=2,
            enable_reranking=True,
            rerank_strategy="semantic"
        )
        
        assert result["success"] is True
        assert result["reranked"] is True
        assert len(result["results"]) <= 2
    
    @pytest.mark.asyncio
    async def test_vector_search_without_reranking(self, populated_tool):
        """Test vector search without reranking (baseline)"""
        result = await populated_tool._execute(
            mode="vector",
            query="machine learning",
            max_results=3,
            enable_reranking=False
        )
        
        assert result["success"] is True
        assert result["reranked"] is False
        
        # Results should not have rerank_score
        for res in result["results"]:
            assert "rerank_score" not in res


class TestHybridSearchReranking:
    """Test reranking for hybrid search"""
    
    @pytest.mark.asyncio
    async def test_hybrid_search_with_hybrid_reranking(self, populated_tool):
        """Test hybrid search with hybrid reranking strategy"""
        query_embedding = [0.1] * 128
        
        result = await populated_tool._execute(
            mode="hybrid",
            query="machine learning",
            query_embedding=query_embedding,
            seed_entity_ids=["e1"],
            max_results=3,
            enable_reranking=True,
            rerank_strategy="hybrid"
        )
        
        assert result["success"] is True
        assert result["reranked"] is True
        assert len(result["results"]) <= 3
        
        # Verify reranking scores
        for res in result["results"]:
            assert "rerank_score" in res
            assert 0.0 <= res["rerank_score"] <= 1.0
    
    @pytest.mark.asyncio
    async def test_hybrid_search_with_structural_reranking(self, populated_tool):
        """Test hybrid search with structural reranking"""
        result = await populated_tool._execute(
            mode="hybrid",
            query="machine learning",
            seed_entity_ids=["e1"],
            max_results=2,
            enable_reranking=True,
            rerank_strategy="structural"
        )
        
        assert result["success"] is True
        assert result["reranked"] is True


class TestTopKLimiting:
    """Test top-K limiting before reranking for performance"""
    
    @pytest.mark.asyncio
    async def test_rerank_top_k_fetches_more_results(self, populated_tool):
        """Test that rerank_top_k fetches more results before reranking"""
        # Request 2 final results, but fetch 5 for reranking
        result = await populated_tool._execute(
            mode="vector",
            query="machine learning",
            max_results=2,
            enable_reranking=True,
            rerank_strategy="text",
            rerank_top_k=5
        )
        
        assert result["success"] is True
        assert result["reranked"] is True
        # Should return exactly max_results after reranking
        assert len(result["results"]) <= 2
    
    @pytest.mark.asyncio
    async def test_rerank_top_k_none_uses_max_results(self, populated_tool):
        """Test that None rerank_top_k uses max_results"""
        result = await populated_tool._execute(
            mode="vector",
            query="machine learning",
            max_results=3,
            enable_reranking=True,
            rerank_strategy="text",
            rerank_top_k=None
        )
        
        assert result["success"] is True
        assert result["reranked"] is True
        assert len(result["results"]) <= 3


class TestRerankingStrategies:
    """Test different reranking strategies"""
    
    @pytest.mark.asyncio
    async def test_text_reranking_strategy(self, populated_tool):
        """Test text similarity reranking strategy"""
        result = await populated_tool._execute(
            mode="filtered",
            entity_type="Paper",
            max_results=3,
            enable_reranking=True,
            rerank_strategy="text"
        )
        
        assert result["success"] is True
        assert result["reranked"] is True
    
    @pytest.mark.asyncio
    async def test_invalid_strategy_falls_back_to_text(self, populated_tool):
        """Test that invalid strategy falls back to text similarity"""
        result = await populated_tool._execute(
            mode="filtered",
            entity_type="Paper",
            max_results=3,
            enable_reranking=True,
            rerank_strategy="nonexistent_strategy"
        )
        
        assert result["success"] is True
        assert result["reranked"] is True
        # Should still work with fallback strategy


class TestPageRankReranking:
    """Test reranking for PageRank search"""
    
    @pytest.mark.asyncio
    async def test_pagerank_with_reranking(self, populated_tool):
        """Test PageRank search with reranking"""
        result = await populated_tool._execute(
            mode="pagerank",
            seed_entity_ids=["e1"],
            max_results=3,
            enable_reranking=True,
            rerank_strategy="structural"
        )
        
        assert result["success"] is True
        assert result["reranked"] is True


class TestMultiHopReranking:
    """Test reranking for multi-hop search"""
    
    @pytest.mark.asyncio
    async def test_multihop_with_reranking(self, populated_tool):
        """Test multi-hop search with reranking"""
        result = await populated_tool._execute(
            mode="multihop",
            seed_entity_ids=["e1"],
            max_depth=2,
            max_results=3,
            enable_reranking=True,
            rerank_strategy="text"
        )
        
        assert result["success"] is True
        assert result["reranked"] is True


class TestFilteredSearchReranking:
    """Test reranking for filtered search"""
    
    @pytest.mark.asyncio
    async def test_filtered_with_reranking(self, populated_tool):
        """Test filtered search with reranking"""
        result = await populated_tool._execute(
            mode="filtered",
            entity_type="Paper",
            max_results=3,
            enable_reranking=True,
            rerank_strategy="text"
        )
        
        assert result["success"] is True
        assert result["reranked"] is True


class TestEmptyResults:
    """Test reranking with empty results"""
    
    @pytest.mark.asyncio
    async def test_reranking_with_no_results(self, populated_tool):
        """Test that reranking handles empty results gracefully"""
        result = await populated_tool._execute(
            mode="filtered",
            entity_type="NonexistentType",
            max_results=10,
            enable_reranking=True,
            rerank_strategy="text"
        )
        
        assert result["success"] is True
        assert result["reranked"] is True
        assert len(result["results"]) == 0


class TestRerankingScorePreservation:
    """Test that original scores are preserved during reranking"""
    
    @pytest.mark.asyncio
    async def test_original_scores_preserved(self, populated_tool):
        """Test that original scores are preserved in reranked results"""
        result = await populated_tool._execute(
            mode="vector",
            query="machine learning",
            max_results=3,
            enable_reranking=True,
            rerank_strategy="text"
        )
        
        assert result["success"] is True
        
        for res in result["results"]:
            # Both scores should be present
            assert "original_score" in res
            assert "rerank_score" in res
            assert "score" in res
            # Current score should match rerank_score
            assert res["score"] == res["rerank_score"]

