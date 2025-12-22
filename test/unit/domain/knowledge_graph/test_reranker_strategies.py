"""
Unit tests for reranking strategy implementations
"""

import pytest
import numpy as np
from aiecs.application.knowledge_graph.search.reranker_strategies import (
    TextSimilarityReranker,
    SemanticReranker,
    StructuralReranker,
    HybridReranker,
    CrossEncoderReranker,
)
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore


class TestTextSimilarityReranker:
    """Test TextSimilarityReranker"""
    
    @pytest.mark.asyncio
    async def test_text_similarity_basic(self):
        """Test basic text similarity scoring"""
        reranker = TextSimilarityReranker()
        
        entities = [
            Entity(id="e1", entity_type="Test", properties={"name": "machine learning", "desc": "AI research"}),
            Entity(id="e2", entity_type="Test", properties={"name": "deep learning", "desc": "neural networks"}),
            Entity(id="e3", entity_type="Test", properties={"name": "database", "desc": "SQL queries"}),
        ]
        
        scores = await reranker.score("machine learning", entities)
        
        assert len(scores) == 3
        assert all(0.0 <= s <= 1.0 for s in scores)
        # e1 should have highest score (exact match)
        assert scores[0] >= scores[1]
        assert scores[1] >= scores[2]
    
    @pytest.mark.asyncio
    async def test_text_similarity_empty_query(self):
        """Test with empty query"""
        reranker = TextSimilarityReranker()
        entities = [
            Entity(id="e1", entity_type="Test", properties={"name": "test"})
        ]
        
        scores = await reranker.score("", entities)
        
        assert scores == [0.0]
    
    @pytest.mark.asyncio
    async def test_text_similarity_empty_entities(self):
        """Test with empty entity list"""
        reranker = TextSimilarityReranker()
        scores = await reranker.score("query", [])
        
        assert scores == []
    
    @pytest.mark.asyncio
    async def test_text_similarity_custom_properties(self):
        """Test with custom property keys"""
        reranker = TextSimilarityReranker(property_keys=["name"])
        
        entities = [
            Entity(id="e1", entity_type="Test", properties={"name": "machine learning", "desc": "unrelated"}),
            Entity(id="e2", entity_type="Test", properties={"name": "database", "desc": "machine learning"}),
        ]
        
        scores = await reranker.score("machine learning", entities)
        
        # e1 should score higher (match in "name" property)
        assert scores[0] > scores[1]
    
    def test_text_similarity_weight_validation(self):
        """Test weight validation"""
        with pytest.raises(ValueError, match="must equal 1.0"):
            TextSimilarityReranker(bm25_weight=0.8, jaccard_weight=0.3)


class TestSemanticReranker:
    """Test SemanticReranker"""
    
    @pytest.mark.asyncio
    async def test_semantic_basic(self):
        """Test basic semantic scoring"""
        reranker = SemanticReranker()
        
        # Create query embedding
        query_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        
        # Create entities with embeddings
        entity1_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]  # Identical to query
        entity2_embedding = [0.2, 0.3, 0.4, 0.5, 0.6]  # Similar
        entity3_embedding = [-0.1, -0.2, -0.3, -0.4, -0.5]  # Opposite
        
        entities = [
            Entity(id="e1", entity_type="Test", properties={}, embedding=entity1_embedding),
            Entity(id="e2", entity_type="Test", properties={}, embedding=entity2_embedding),
            Entity(id="e3", entity_type="Test", properties={}, embedding=entity3_embedding),
        ]
        
        scores = await reranker.score("query", entities, query_embedding=query_embedding)
        
        assert len(scores) == 3
        assert all(0.0 <= s <= 1.0 for s in scores)
        # e1 should have highest score (identical embedding)
        assert scores[0] >= scores[1]
        assert scores[1] >= scores[2]
    
    @pytest.mark.asyncio
    async def test_semantic_no_embedding(self):
        """Test without query embedding"""
        reranker = SemanticReranker()
        entities = [
            Entity(id="e1", entity_type="Test", properties={}, embedding=[0.1, 0.2])
        ]
        
        scores = await reranker.score("query", entities)
        
        assert scores == [0.0]
    
    @pytest.mark.asyncio
    async def test_semantic_no_entity_embedding(self):
        """Test with entities without embeddings"""
        reranker = SemanticReranker()
        query_embedding = [0.1, 0.2, 0.3]
        
        entities = [
            Entity(id="e1", entity_type="Test", properties={}, embedding=None),
            Entity(id="e2", entity_type="Test", properties={}, embedding=[0.1, 0.2, 0.3]),
        ]
        
        scores = await reranker.score("query", entities, query_embedding=query_embedding)
        
        assert scores[0] == 0.0  # No embedding
        assert scores[1] > 0.0  # Has embedding
    
    @pytest.mark.asyncio
    async def test_semantic_zero_embedding(self):
        """Test with zero query embedding"""
        reranker = SemanticReranker()
        query_embedding = [0.0, 0.0, 0.0]
        
        entities = [
            Entity(id="e1", entity_type="Test", properties={}, embedding=[0.1, 0.2, 0.3])
        ]
        
        scores = await reranker.score("query", entities, query_embedding=query_embedding)
        
        assert scores == [0.0]


class TestStructuralReranker:
    """Test StructuralReranker"""
    
    @pytest.mark.asyncio
    async def test_structural_basic(self):
        """Test basic structural scoring"""
        store = InMemoryGraphStore()
        await store.initialize()
        
        # Create entities
        e1 = Entity(id="e1", entity_type="Test", properties={"name": "Entity 1"})
        e2 = Entity(id="e2", entity_type="Test", properties={"name": "Entity 2"})
        e3 = Entity(id="e3", entity_type="Test", properties={"name": "Entity 3"})
        
        await store.add_entity(e1)
        await store.add_entity(e2)
        await store.add_entity(e3)
        
        # Create relations (e1 -> e2 -> e3)
        from aiecs.domain.knowledge_graph.models.relation import Relation
        r1 = Relation(id="r1", relation_type="RELATES", source_id="e1", target_id="e2")
        r2 = Relation(id="r2", relation_type="RELATES", source_id="e2", target_id="e3")
        
        await store.add_relation(r1)
        await store.add_relation(r2)
        
        reranker = StructuralReranker(store, use_cached_scores=False)
        entities = [e1, e2, e3]
        
        scores = await reranker.score("query", entities)
        
        assert len(scores) == 3
        assert all(0.0 <= s <= 1.0 for s in scores)
        
        await store.close()
    
    @pytest.mark.asyncio
    async def test_structural_empty_graph(self):
        """Test with empty graph"""
        store = InMemoryGraphStore()
        await store.initialize()
        
        entities = [
            Entity(id="e1", entity_type="Test", properties={})
        ]
        
        reranker = StructuralReranker(store)
        scores = await reranker.score("query", entities)
        
        assert len(scores) == 1
        assert scores[0] >= 0.0
        
        await store.close()
    
    def test_structural_weight_validation(self):
        """Test weight validation"""
        store = InMemoryGraphStore()
        with pytest.raises(ValueError, match="must equal 1.0"):
            StructuralReranker(store, pagerank_weight=0.8, degree_weight=0.3)


class TestHybridReranker:
    """Test HybridReranker"""
    
    @pytest.mark.asyncio
    async def test_hybrid_basic(self):
        """Test basic hybrid scoring"""
        store = InMemoryGraphStore()
        await store.initialize()
        
        entities = [
            Entity(
                id="e1",
                entity_type="Test",
                properties={"name": "machine learning"},
                embedding=[0.1, 0.2, 0.3]
            ),
            Entity(
                id="e2",
                entity_type="Test",
                properties={"name": "database"},
                embedding=[0.4, 0.5, 0.6]
            ),
        ]
        
        await store.add_entity(entities[0])
        await store.add_entity(entities[1])
        
        query_embedding = [0.1, 0.2, 0.3]
        
        reranker = HybridReranker(store)
        scores = await reranker.score(
            "machine learning",
            entities,
            query_embedding=query_embedding
        )
        
        assert len(scores) == 2
        assert all(0.0 <= s <= 1.0 for s in scores)
        
        await store.close()
    
    @pytest.mark.asyncio
    async def test_hybrid_empty_entities(self):
        """Test with empty entity list"""
        store = InMemoryGraphStore()
        await store.initialize()
        
        reranker = HybridReranker(store)
        scores = await reranker.score("query", [])
        
        assert scores == []
        
        await store.close()
    
    def test_hybrid_weight_validation(self):
        """Test weight validation"""
        store = InMemoryGraphStore()
        with pytest.raises(ValueError, match="must sum to 1.0"):
            HybridReranker(store, text_weight=0.5, semantic_weight=0.5, structural_weight=0.3)


class TestCrossEncoderReranker:
    """Test CrossEncoderReranker"""
    
    @pytest.mark.asyncio
    async def test_cross_encoder_basic(self):
        """Test basic cross-encoder scoring (placeholder)"""
        reranker = CrossEncoderReranker()
        
        entities = [
            Entity(id="e1", entity_type="Test", properties={"name": "machine learning"}),
            Entity(id="e2", entity_type="Test", properties={"name": "database"}),
        ]
        
        scores = await reranker.score("machine learning", entities)
        
        assert len(scores) == 2
        assert all(0.0 <= s <= 1.0 for s in scores)
        # e1 should score higher (text match)
        assert scores[0] >= scores[1]
    
    @pytest.mark.asyncio
    async def test_cross_encoder_empty_query(self):
        """Test with empty query"""
        reranker = CrossEncoderReranker()
        entities = [
            Entity(id="e1", entity_type="Test", properties={"name": "test"})
        ]
        
        scores = await reranker.score("", entities)
        
        assert scores == [0.0]
    
    @pytest.mark.asyncio
    async def test_cross_encoder_empty_entities(self):
        """Test with empty entity list"""
        reranker = CrossEncoderReranker()
        scores = await reranker.score("query", [])
        
        assert scores == []


class TestRerankerIntegration:
    """Integration tests for reranking strategies"""
    
    @pytest.mark.asyncio
    async def test_multiple_strategies_together(self):
        """Test using multiple strategies with ResultReranker"""
        from aiecs.application.knowledge_graph.search.reranker import ResultReranker
        
        store = InMemoryGraphStore()
        await store.initialize()
        
        entities = [
            Entity(
                id="e1",
                entity_type="Test",
                properties={"name": "machine learning research"},
                embedding=[0.1, 0.2, 0.3]
            ),
            Entity(
                id="e2",
                entity_type="Test",
                properties={"name": "deep learning"},
                embedding=[0.2, 0.3, 0.4]
            ),
        ]
        
        await store.add_entity(entities[0])
        await store.add_entity(entities[1])
        
        # Create reranker with multiple strategies
        text_reranker = TextSimilarityReranker()
        semantic_reranker = SemanticReranker()
        
        reranker = ResultReranker(
            strategies=[text_reranker, semantic_reranker],
            weights={"strategy_0": 0.6, "strategy_1": 0.4}
        )
        
        query_embedding = [0.1, 0.2, 0.3]
        reranked = await reranker.rerank(
            "machine learning",
            entities,
            query_embedding=query_embedding
        )
        
        assert len(reranked) == 2
        assert all(isinstance(item, tuple) and len(item) == 2 for item in reranked)
        assert reranked[0][1] >= reranked[1][1]  # Sorted by score
        
        await store.close()

