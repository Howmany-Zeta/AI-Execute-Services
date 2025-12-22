"""
Unit tests for hybrid search strategy

Tests HybridSearchStrategy, HybridSearchConfig, and different search modes.
"""

import pytest
import numpy as np
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.application.knowledge_graph.search.hybrid_search import (
    HybridSearchStrategy,
    HybridSearchConfig,
    SearchMode
)
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore


@pytest.fixture
async def rich_graph_store():
    """Fixture with a rich graph for testing hybrid search"""
    store = InMemoryGraphStore()
    await store.initialize()
    
    # Create entities with embeddings
    # Topic: AI and Machine Learning
    # Cluster 1: Deep Learning
    e1 = Entity(
        id="dl_basics",
        entity_type="Article",
        properties={"title": "Deep Learning Basics", "topic": "AI"},
        embedding=[1.0, 0.9, 0.1, 0.1]  # Close to DL topics
    )
    e2 = Entity(
        id="neural_nets",
        entity_type="Article",
        properties={"title": "Neural Networks", "topic": "AI"},
        embedding=[0.95, 0.85, 0.15, 0.12]  # Similar to e1
    )
    e3 = Entity(
        id="cnn",
        entity_type="Article",
        properties={"title": "CNNs", "topic": "AI"},
        embedding=[0.9, 0.8, 0.2, 0.15]  # Similar cluster
    )
    
    # Cluster 2: Machine Learning (different vector space)
    e4 = Entity(
        id="ml_intro",
        entity_type="Article",
        properties={"title": "ML Introduction", "topic": "AI"},
        embedding=[0.2, 0.3, 0.9, 0.8]  # Different cluster
    )
    e5 = Entity(
        id="supervised",
        entity_type="Article",
        properties={"title": "Supervised Learning", "topic": "AI"},
        embedding=[0.25, 0.35, 0.85, 0.75]  # Similar to e4
    )
    
    # Cluster 3: Related but distant
    e6 = Entity(
        id="stats",
        entity_type="Book",
        properties={"title": "Statistics", "topic": "Math"},
        embedding=[0.3, 0.4, 0.7, 0.6]  # Somewhat related
    )
    
    # Add entities
    for entity in [e1, e2, e3, e4, e5, e6]:
        await store.add_entity(entity)
    
    # Create graph structure
    # Deep Learning chain: dl_basics -> neural_nets -> cnn
    await store.add_relation(Relation(
        id="r1",
        relation_type="RELATED_TO",
        source_id="dl_basics",
        target_id="neural_nets",
        weight=0.9
    ))
    await store.add_relation(Relation(
        id="r2",
        relation_type="RELATED_TO",
        source_id="neural_nets",
        target_id="cnn",
        weight=0.85
    ))
    
    # ML chain: ml_intro -> supervised
    await store.add_relation(Relation(
        id="r3",
        relation_type="RELATED_TO",
        source_id="ml_intro",
        target_id="supervised",
        weight=0.8
    ))
    
    # Cross-cluster connections
    await store.add_relation(Relation(
        id="r4",
        relation_type="PREREQUISITE",
        source_id="ml_intro",
        target_id="dl_basics",
        weight=0.7
    ))
    await store.add_relation(Relation(
        id="r5",
        relation_type="USES",
        source_id="supervised",
        target_id="stats",
        weight=0.6
    ))
    
    yield store
    await store.close()


class TestHybridSearchConfig:
    """Test hybrid search configuration"""
    
    def test_default_config(self):
        """Test default configuration"""
        config = HybridSearchConfig()
        
        assert config.mode == SearchMode.HYBRID
        assert config.vector_weight == 0.6
        assert config.graph_weight == 0.4
        assert config.max_results == 10
        assert config.expand_results is True
    
    def test_custom_config(self):
        """Test custom configuration"""
        config = HybridSearchConfig(
            mode=SearchMode.VECTOR_ONLY,
            vector_weight=0.8,
            graph_weight=0.2,
            max_results=5,
            vector_threshold=0.5,
            max_graph_depth=3
        )
        
        assert config.mode == SearchMode.VECTOR_ONLY
        assert config.vector_weight == 0.8
        assert config.graph_weight == 0.2
        assert config.max_results == 5
        assert config.vector_threshold == 0.5
        assert config.max_graph_depth == 3
    
    def test_config_validation(self):
        """Test configuration validation"""
        # Valid range
        config = HybridSearchConfig(vector_weight=0.5, graph_weight=0.5)
        assert config.vector_weight == 0.5
        
        # Invalid range should raise validation error
        with pytest.raises(Exception):  # Pydantic validation error
            HybridSearchConfig(vector_weight=1.5)


class TestVectorOnlySearch:
    """Test vector-only search mode"""
    
    @pytest.mark.asyncio
    async def test_vector_only_search(self, rich_graph_store):
        """Test pure vector similarity search"""
        strategy = HybridSearchStrategy(rich_graph_store)
        
        # Query similar to Deep Learning cluster
        query = [1.0, 0.9, 0.1, 0.1]
        
        config = HybridSearchConfig(
            mode=SearchMode.VECTOR_ONLY,
            max_results=3
        )
        
        results = await strategy.search(query, config)
        
        # Should find entities similar to query
        assert len(results) > 0
        assert len(results) <= 3
        
        # Results should be sorted by similarity
        for i in range(len(results) - 1):
            assert results[i][1] >= results[i + 1][1]
        
        # Top result should be most similar (dl_basics)
        assert results[0][0].id == "dl_basics"
    
    @pytest.mark.asyncio
    async def test_vector_only_with_threshold(self, rich_graph_store):
        """Test vector search with similarity threshold"""
        strategy = HybridSearchStrategy(rich_graph_store)
        
        query = [1.0, 0.9, 0.1, 0.1]
        
        config = HybridSearchConfig(
            mode=SearchMode.VECTOR_ONLY,
            vector_threshold=0.95,
            max_results=10
        )
        
        results = await strategy.search(query, config)
        
        # Only very similar entities should be returned
        for entity, score in results:
            assert score >= 0.95
    
    @pytest.mark.asyncio
    async def test_vector_only_with_entity_type_filter(self, rich_graph_store):
        """Test vector search with entity type filter"""
        strategy = HybridSearchStrategy(rich_graph_store)
        
        query = [0.5, 0.5, 0.5, 0.5]  # Neutral query
        
        config = HybridSearchConfig(
            mode=SearchMode.VECTOR_ONLY,
            entity_type_filter="Book",
            max_results=10
        )
        
        results = await strategy.search(query, config)
        
        # Only Book entities should be returned
        for entity, score in results:
            assert entity.entity_type == "Book"


class TestGraphOnlySearch:
    """Test graph-only search mode"""
    
    @pytest.mark.asyncio
    async def test_graph_only_search(self, rich_graph_store):
        """Test pure graph structure search"""
        strategy = HybridSearchStrategy(rich_graph_store)
        
        query = [1.0, 0.9, 0.1, 0.1]
        
        config = HybridSearchConfig(
            mode=SearchMode.GRAPH_ONLY,
            max_graph_depth=2,
            max_results=5
        )
        
        # Provide seed entities
        seed_ids = ["dl_basics"]
        
        results = await strategy.search(query, config, seed_entity_ids=seed_ids)
        
        # Should find entities connected to seed
        assert len(results) > 0
        
        # Should include the seed and neighbors
        entity_ids = {entity.id for entity, _ in results}
        assert "dl_basics" in entity_ids
        assert "neural_nets" in entity_ids  # Direct neighbor
    
    @pytest.mark.asyncio
    async def test_graph_only_depth_scoring(self, rich_graph_store):
        """Test that graph search scores decrease with depth"""
        strategy = HybridSearchStrategy(rich_graph_store)
        
        query = [1.0, 0.9, 0.1, 0.1]
        
        config = HybridSearchConfig(
            mode=SearchMode.GRAPH_ONLY,
            max_graph_depth=2,
            max_results=10
        )
        
        seed_ids = ["dl_basics"]
        results = await strategy.search(query, config, seed_entity_ids=seed_ids)
        
        # Build entity to score mapping
        scores = {entity.id: score for entity, score in results}
        
        # Seed should have highest score (depth 0)
        assert scores["dl_basics"] == 1.0
        
        # Direct neighbor should have lower score (depth 1)
        if "neural_nets" in scores:
            assert scores["neural_nets"] <= 1.0
        
        # 2-hop neighbor should have even lower score (depth 2)
        if "cnn" in scores:
            assert scores["cnn"] <= scores.get("neural_nets", 1.0)
    
    @pytest.mark.asyncio
    async def test_graph_only_without_seeds_uses_vector(self, rich_graph_store):
        """Test that graph search without seeds uses vector to find seeds"""
        strategy = HybridSearchStrategy(rich_graph_store)
        
        # Query similar to Deep Learning
        query = [1.0, 0.9, 0.1, 0.1]
        
        config = HybridSearchConfig(
            mode=SearchMode.GRAPH_ONLY,
            max_graph_depth=1,
            max_results=5
        )
        
        # No seeds provided - should use vector search to find seeds
        results = await strategy.search(query, config)
        
        # Should still return results
        assert len(results) > 0


class TestHybridSearch:
    """Test hybrid search mode"""
    
    @pytest.mark.asyncio
    async def test_hybrid_search_combines_both(self, rich_graph_store):
        """Test that hybrid search combines vector and graph"""
        strategy = HybridSearchStrategy(rich_graph_store)
        
        # Query similar to Deep Learning
        query = [1.0, 0.9, 0.1, 0.1]
        
        config = HybridSearchConfig(
            mode=SearchMode.HYBRID,
            vector_weight=0.6,
            graph_weight=0.4,
            max_results=5,
            expand_results=True
        )
        
        results = await strategy.search(query, config)
        
        # Should find results
        assert len(results) > 0
        assert len(results) <= 5
        
        # Should include vector-similar entities
        entity_ids = {entity.id for entity, _ in results}
        assert "dl_basics" in entity_ids  # Top vector match
    
    @pytest.mark.asyncio
    async def test_hybrid_search_weight_balance(self, rich_graph_store):
        """Test different weight configurations"""
        strategy = HybridSearchStrategy(rich_graph_store)
        
        query = [1.0, 0.9, 0.1, 0.1]
        
        # Heavy vector weight
        config_vector_heavy = HybridSearchConfig(
            mode=SearchMode.HYBRID,
            vector_weight=0.9,
            graph_weight=0.1,
            max_results=3
        )
        
        results_vector_heavy = await strategy.search(query, config_vector_heavy)
        
        # Heavy graph weight
        config_graph_heavy = HybridSearchConfig(
            mode=SearchMode.HYBRID,
            vector_weight=0.1,
            graph_weight=0.9,
            max_results=3
        )
        
        results_graph_heavy = await strategy.search(query, config_graph_heavy)
        
        # Both should return results
        assert len(results_vector_heavy) > 0
        assert len(results_graph_heavy) > 0
        
        # Results may differ due to different weighting
        # (exact comparison depends on the data)
    
    @pytest.mark.asyncio
    async def test_hybrid_search_with_min_score(self, rich_graph_store):
        """Test hybrid search with minimum combined score"""
        strategy = HybridSearchStrategy(rich_graph_store)
        
        query = [1.0, 0.9, 0.1, 0.1]
        
        config = HybridSearchConfig(
            mode=SearchMode.HYBRID,
            min_combined_score=0.5,
            max_results=10
        )
        
        results = await strategy.search(query, config)
        
        # All results should meet minimum score
        for entity, score in results:
            assert score >= 0.5
    
    @pytest.mark.asyncio
    async def test_hybrid_search_expansion(self, rich_graph_store):
        """Test hybrid search with result expansion"""
        strategy = HybridSearchStrategy(rich_graph_store)
        
        query = [1.0, 0.9, 0.1, 0.1]
        
        # With expansion
        config_with_expansion = HybridSearchConfig(
            mode=SearchMode.HYBRID,
            expand_results=True,
            max_results=5
        )
        
        results_with = await strategy.search(query, config_with_expansion)
        
        # Without expansion
        config_no_expansion = HybridSearchConfig(
            mode=SearchMode.HYBRID,
            expand_results=False,
            max_results=5
        )
        
        results_without = await strategy.search(query, config_no_expansion)
        
        # With expansion should potentially find more diverse results
        assert len(results_with) > 0
        assert len(results_without) > 0


class TestSearchWithExpansion:
    """Test search with expansion and path tracking"""
    
    @pytest.mark.asyncio
    async def test_search_with_path_tracking(self, rich_graph_store):
        """Test search with path tracking enabled"""
        strategy = HybridSearchStrategy(rich_graph_store)
        
        query = [1.0, 0.9, 0.1, 0.1]
        
        config = HybridSearchConfig(
            mode=SearchMode.HYBRID,
            expand_results=True,
            max_graph_depth=2,
            max_results=5
        )
        
        results, paths = await strategy.search_with_expansion(
            query,
            config,
            include_paths=True
        )
        
        # Should have results
        assert len(results) > 0
        
        # Should have paths if expansion enabled
        assert paths is not None
    
    @pytest.mark.asyncio
    async def test_search_without_path_tracking(self, rich_graph_store):
        """Test search without path tracking"""
        strategy = HybridSearchStrategy(rich_graph_store)
        
        query = [1.0, 0.9, 0.1, 0.1]
        
        config = HybridSearchConfig(
            mode=SearchMode.HYBRID,
            max_results=3
        )
        
        results, paths = await strategy.search_with_expansion(
            query,
            config,
            include_paths=False
        )
        
        # Should have results
        assert len(results) > 0
        
        # Should not have paths
        assert paths is None


class TestScoreCombination:
    """Test score combination logic"""
    
    @pytest.mark.asyncio
    async def test_score_combination_equal_weights(self, rich_graph_store):
        """Test score combination with equal weights"""
        strategy = HybridSearchStrategy(rich_graph_store)
        
        vector_scores = {"e1": 0.8, "e2": 0.6}
        graph_scores = {"e1": 0.4, "e3": 0.7}
        
        config = HybridSearchConfig(
            vector_weight=0.5,
            graph_weight=0.5
        )
        
        combined = await strategy._combine_scores(
            vector_scores,
            graph_scores,
            config
        )
        
        # e1: (0.8 * 0.5 + 0.4 * 0.5) = 0.6
        # e2: (0.6 * 0.5 + 0.0 * 0.5) = 0.3
        # e3: (0.0 * 0.5 + 0.7 * 0.5) = 0.35
        assert abs(combined["e1"] - 0.6) < 0.01
        assert abs(combined["e2"] - 0.3) < 0.01
        assert abs(combined["e3"] - 0.35) < 0.01
    
    @pytest.mark.asyncio
    async def test_score_combination_different_weights(self, rich_graph_store):
        """Test score combination with different weights"""
        strategy = HybridSearchStrategy(rich_graph_store)
        
        vector_scores = {"e1": 0.9}
        graph_scores = {"e1": 0.3}
        
        config = HybridSearchConfig(
            vector_weight=0.8,
            graph_weight=0.2
        )
        
        combined = await strategy._combine_scores(
            vector_scores,
            graph_scores,
            config
        )
        
        # e1: (0.9 * 0.8 + 0.3 * 0.2) = 0.78
        assert abs(combined["e1"] - 0.78) < 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

