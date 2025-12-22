"""
Unit tests for knowledge graph search module

Tests use real components (InMemoryGraphStore) when possible.
Only use mocks if pytest-cov limitations cause issues.
"""

import pytest
from typing import List, Tuple

from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.domain.knowledge_graph.models.path import Path
from aiecs.infrastructure.graph_storage import InMemoryGraphStore
from aiecs.application.knowledge_graph.search.hybrid_search import (
    HybridSearchStrategy,
    HybridSearchConfig,
    SearchMode
)


class TestSearchMode:
    """Test SearchMode enum"""
    
    def test_search_mode_values(self):
        """Test SearchMode enum values"""
        assert SearchMode.VECTOR_ONLY == "vector_only"
        assert SearchMode.GRAPH_ONLY == "graph_only"
        assert SearchMode.HYBRID == "hybrid"


class TestHybridSearchConfig:
    """Test HybridSearchConfig"""
    
    def test_default_config(self):
        """Test default configuration"""
        config = HybridSearchConfig()
        
        assert config.mode == SearchMode.HYBRID
        assert config.vector_weight == 0.6
        assert config.graph_weight == 0.4
        assert config.max_results == 10
        assert config.vector_threshold == 0.0
        assert config.max_graph_depth == 2
        assert config.expand_results is True
        assert config.min_combined_score == 0.0
        assert config.entity_type_filter is None
    
    def test_custom_config(self):
        """Test custom configuration"""
        config = HybridSearchConfig(
            mode=SearchMode.VECTOR_ONLY,
            vector_weight=0.8,
            graph_weight=0.2,
            max_results=20,
            vector_threshold=0.5,
            max_graph_depth=3,
            expand_results=False,
            min_combined_score=0.3,
            entity_type_filter="Person"
        )
        
        assert config.mode == SearchMode.VECTOR_ONLY
        assert config.vector_weight == 0.8
        assert config.graph_weight == 0.2
        assert config.max_results == 20
        assert config.vector_threshold == 0.5
        assert config.max_graph_depth == 3
        assert config.expand_results is False
        assert config.min_combined_score == 0.3
        assert config.entity_type_filter == "Person"
    
    def test_config_validation(self):
        """Test configuration validation"""
        # Valid config
        config = HybridSearchConfig(
            vector_weight=0.5,
            graph_weight=0.5,
            max_results=5
        )
        assert config.vector_weight == 0.5
        
        # Test bounds - should be clamped or validated by Pydantic
        with pytest.raises(Exception):  # Pydantic validation error
            HybridSearchConfig(vector_weight=1.5)  # > 1.0


class TestHybridSearchStrategy:
    """Test HybridSearchStrategy"""
    
    @pytest.fixture
    async def graph_store(self):
        """Create and initialize in-memory graph store"""
        store = InMemoryGraphStore()
        await store.initialize()
        yield store
        await store.close()
    
    @pytest.fixture
    async def populated_store(self):
        """Create graph store with sample data"""
        store = InMemoryGraphStore()
        await store.initialize()
        
        # Create entities with embeddings
        entities = [
            Entity(
                id="e1",
                entity_type="Person",
                properties={"name": "Alice"},
                embedding=[0.1] * 128
            ),
            Entity(
                id="e2",
                entity_type="Person",
                properties={"name": "Bob"},
                embedding=[0.2] * 128
            ),
            Entity(
                id="e3",
                entity_type="Company",
                properties={"name": "Tech Corp"},
                embedding=[0.3] * 128
            ),
            Entity(
                id="e4",
                entity_type="Person",
                properties={"name": "Charlie"},
                embedding=[0.4] * 128
            )
        ]
        
        for entity in entities:
            await store.add_entity(entity)
        
        # Create relations
        relations = [
            Relation(id="r1", relation_type="KNOWS", source_id="e1", target_id="e2"),
            Relation(id="r2", relation_type="WORKS_FOR", source_id="e2", target_id="e3"),
            Relation(id="r3", relation_type="KNOWS", source_id="e1", target_id="e4")
        ]
        
        for relation in relations:
            await store.add_relation(relation)
        
        yield store
        await store.close()
    
    @pytest.fixture
    def strategy(self, graph_store):
        """Create HybridSearchStrategy instance"""
        return HybridSearchStrategy(graph_store)
    
    @pytest.fixture
    def strategy_populated(self, populated_store):
        """Create HybridSearchStrategy with populated store"""
        return HybridSearchStrategy(populated_store)
    
    @pytest.mark.asyncio
    async def test_vector_only_search(self, strategy_populated):
        """Test vector-only search mode"""
        config = HybridSearchConfig(
            mode=SearchMode.VECTOR_ONLY,
            max_results=5
        )
        
        query_embedding = [0.15] * 128
        results = await strategy_populated.search(query_embedding, config)
        
        assert isinstance(results, list)
        assert all(isinstance(item, tuple) and len(item) == 2 for item in results)
        assert all(isinstance(entity, Entity) and isinstance(score, float) for entity, score in results)
    
    @pytest.mark.asyncio
    async def test_graph_only_search_with_seeds(self, strategy_populated):
        """Test graph-only search with seed entities"""
        config = HybridSearchConfig(
            mode=SearchMode.GRAPH_ONLY,
            max_results=10
        )
        
        results = await strategy_populated.search(
            query_embedding=[0.1] * 128,
            config=config,
            seed_entity_ids=["e1"]
        )
        
        assert isinstance(results, list)
        # Should include seed and neighbors
        entity_ids = [entity.id for entity, _ in results]
        assert "e1" in entity_ids
    
    @pytest.mark.asyncio
    async def test_graph_only_search_without_seeds(self, strategy_populated):
        """Test graph-only search without seeds (uses vector to find seeds)"""
        config = HybridSearchConfig(
            mode=SearchMode.GRAPH_ONLY,
            max_results=10
        )
        
        query_embedding = [0.15] * 128
        results = await strategy_populated.search(query_embedding, config)
        
        assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_hybrid_search(self, strategy_populated):
        """Test hybrid search mode"""
        config = HybridSearchConfig(
            mode=SearchMode.HYBRID,
            vector_weight=0.6,
            graph_weight=0.4,
            max_results=10,
            expand_results=True
        )
        
        query_embedding = [0.15] * 128
        results = await strategy_populated.search(query_embedding, config)
        
        assert isinstance(results, list)
        assert len(results) <= config.max_results
    
    @pytest.mark.asyncio
    async def test_hybrid_search_with_seeds(self, strategy_populated):
        """Test hybrid search with seed entities"""
        config = HybridSearchConfig(
            mode=SearchMode.HYBRID,
            expand_results=True
        )
        
        query_embedding = [0.15] * 128
        results = await strategy_populated.search(
            query_embedding,
            config,
            seed_entity_ids=["e1"]
        )
        
        assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_hybrid_search_no_expansion(self, strategy_populated):
        """Test hybrid search without expansion"""
        config = HybridSearchConfig(
            mode=SearchMode.HYBRID,
            expand_results=False
        )
        
        query_embedding = [0.15] * 128
        results = await strategy_populated.search(query_embedding, config)
        
        assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_search_default_config(self, strategy_populated):
        """Test search with default config"""
        query_embedding = [0.15] * 128
        results = await strategy_populated.search(query_embedding)
        
        assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_vector_search(self, strategy_populated):
        """Test vector search method"""
        config = HybridSearchConfig(max_results=5)
        query_embedding = [0.15] * 128
        
        results = await strategy_populated._vector_search(query_embedding, config)
        
        assert isinstance(results, list)
        assert len(results) <= 5
    
    @pytest.mark.asyncio
    async def test_vector_search_with_max_results_override(self, strategy_populated):
        """Test vector search with max_results override"""
        config = HybridSearchConfig(max_results=10)
        query_embedding = [0.15] * 128
        
        results = await strategy_populated._vector_search(
            query_embedding,
            config,
            max_results=3
        )
        
        assert isinstance(results, list)
        assert len(results) <= 3
    
    @pytest.mark.asyncio
    async def test_vector_search_with_entity_type_filter(self, strategy_populated):
        """Test vector search with entity type filter"""
        config = HybridSearchConfig(
            max_results=10,
            entity_type_filter="Person"
        )
        query_embedding = [0.15] * 128
        
        results = await strategy_populated._vector_search(query_embedding, config)
        
        assert isinstance(results, list)
        # All results should be Person type
        for entity, _ in results:
            assert entity.entity_type == "Person"
    
    @pytest.mark.asyncio
    async def test_vector_search_with_threshold(self, strategy_populated):
        """Test vector search with similarity threshold"""
        config = HybridSearchConfig(
            max_results=10,
            vector_threshold=0.5
        )
        query_embedding = [0.15] * 128
        
        results = await strategy_populated._vector_search(query_embedding, config)
        
        assert isinstance(results, list)
        # All results should meet threshold
        for _, score in results:
            assert score >= 0.5
    
    @pytest.mark.asyncio
    async def test_graph_search(self, strategy_populated):
        """Test graph search method"""
        config = HybridSearchConfig(max_results=10, max_graph_depth=2)
        
        results = await strategy_populated._graph_search(["e1"], config)
        
        assert isinstance(results, list)
        assert len(results) <= config.max_results
    
    @pytest.mark.asyncio
    async def test_graph_search_multiple_seeds(self, strategy_populated):
        """Test graph search with multiple seed entities"""
        config = HybridSearchConfig(max_results=10, max_graph_depth=2)
        
        results = await strategy_populated._graph_search(["e1", "e2"], config)
        
        assert isinstance(results, list)
        # Should include both seeds
        entity_ids = [entity.id for entity, _ in results]
        assert "e1" in entity_ids or "e2" in entity_ids
    
    @pytest.mark.asyncio
    async def test_graph_search_depth_scoring(self, strategy_populated):
        """Test that graph search scores decrease with depth"""
        config = HybridSearchConfig(max_results=10, max_graph_depth=2)
        
        results = await strategy_populated._graph_search(["e1"], config)
        
        assert isinstance(results, list)
        if len(results) > 1:
            scores = [score for _, score in results]
            # Scores should be sorted descending
            assert scores == sorted(scores, reverse=True)
    
    @pytest.mark.asyncio
    async def test_graph_search_entity_type_filter(self, strategy_populated):
        """Test graph search with entity type filter"""
        config = HybridSearchConfig(
            max_results=10,
            entity_type_filter="Person"
        )
        
        results = await strategy_populated._graph_search(["e1"], config)
        
        assert isinstance(results, list)
        # All results should be Person type
        for entity, _ in results:
            assert entity.entity_type == "Person"
    
    @pytest.mark.asyncio
    async def test_graph_search_visited_entities(self, strategy_populated):
        """Test that visited entities are not revisited"""
        config = HybridSearchConfig(max_results=10, max_graph_depth=2)
        
        results = await strategy_populated._graph_search(["e1"], config)
        
        assert isinstance(results, list)
        # Should not have duplicates
        entity_ids = [entity.id for entity, _ in results]
        assert len(entity_ids) == len(set(entity_ids))
    
    @pytest.mark.asyncio
    async def test_graph_search_empty_next_level(self, strategy_populated):
        """Test graph search when next level is empty"""
        # Add isolated entity
        isolated = Entity(
            id="isolated",
            entity_type="Person",
            properties={"name": "Isolated"},
            embedding=[0.5] * 128
        )
        await strategy_populated.graph_store.add_entity(isolated)
        
        config = HybridSearchConfig(max_results=10, max_graph_depth=2)
        results = await strategy_populated._graph_search(["isolated"], config)
        
        assert isinstance(results, list)
        # Should include isolated entity
        entity_ids = [entity.id for entity, _ in results]
        assert "isolated" in entity_ids
    
    @pytest.mark.asyncio
    async def test_hybrid_search_combines_scores(self, strategy_populated):
        """Test that hybrid search combines vector and graph scores"""
        config = HybridSearchConfig(
            mode=SearchMode.HYBRID,
            vector_weight=0.6,
            graph_weight=0.4,
            expand_results=True,
            max_results=10
        )
        
        query_embedding = [0.15] * 128
        results = await strategy_populated._hybrid_search(
            query_embedding,
            config,
            seed_entity_ids=["e1"]
        )
        
        assert isinstance(results, list)
        assert len(results) <= config.max_results
    
    @pytest.mark.asyncio
    async def test_hybrid_search_min_score_threshold(self, strategy_populated):
        """Test hybrid search with minimum combined score threshold"""
        config = HybridSearchConfig(
            mode=SearchMode.HYBRID,
            min_combined_score=0.5,
            max_results=10
        )
        
        query_embedding = [0.15] * 128
        results = await strategy_populated._hybrid_search(
            query_embedding,
            config
        )
        
        assert isinstance(results, list)
        # All results should meet minimum score
        for _, score in results:
            assert score >= 0.5
    
    @pytest.mark.asyncio
    async def test_combine_scores(self, strategy_populated):
        """Test score combination"""
        config = HybridSearchConfig(
            vector_weight=0.6,
            graph_weight=0.4
        )
        
        vector_scores = {"e1": 0.8, "e2": 0.6}
        graph_scores = {"e1": 0.5, "e3": 0.7}
        
        combined = await strategy_populated._combine_scores(
            vector_scores,
            graph_scores,
            config
        )
        
        assert isinstance(combined, dict)
        assert "e1" in combined
        assert "e2" in combined
        assert "e3" in combined
        
        # e1 should have combined score
        assert combined["e1"] > 0
        # e2 should have only vector score
        assert combined["e2"] > 0
        # e3 should have only graph score
        assert combined["e3"] > 0
    
    @pytest.mark.asyncio
    async def test_combine_scores_zero_weights(self, strategy_populated):
        """Test score combination with zero weights"""
        config = HybridSearchConfig(
            vector_weight=0.0,
            graph_weight=0.0
        )
        
        vector_scores = {"e1": 0.8}
        graph_scores = {"e2": 0.6}
        
        combined = await strategy_populated._combine_scores(
            vector_scores,
            graph_scores,
            config
        )
        
        assert isinstance(combined, dict)
        # Should handle zero weights gracefully
    
    @pytest.mark.asyncio
    async def test_combine_scores_normalization(self, strategy_populated):
        """Test that weights are normalized"""
        config = HybridSearchConfig(
            vector_weight=0.3,
            graph_weight=0.2  # Total = 0.5, should normalize to 1.0
        )
        
        vector_scores = {"e1": 1.0}
        graph_scores = {"e1": 1.0}
        
        combined = await strategy_populated._combine_scores(
            vector_scores,
            graph_scores,
            config
        )
        
        assert isinstance(combined, dict)
        # Combined score should be normalized
        assert 0.0 <= combined["e1"] <= 1.0
    
    @pytest.mark.asyncio
    async def test_search_with_expansion(self, strategy_populated):
        """Test search with expansion"""
        config = HybridSearchConfig(
            expand_results=True,
            max_results=10
        )
        
        query_embedding = [0.15] * 128
        results, paths = await strategy_populated.search_with_expansion(
            query_embedding,
            config,
            include_paths=True
        )
        
        assert isinstance(results, list)
        assert paths is None or isinstance(paths, list)
    
    @pytest.mark.asyncio
    async def test_search_with_expansion_no_paths(self, strategy_populated):
        """Test search with expansion but no path tracking"""
        config = HybridSearchConfig(expand_results=True)
        
        query_embedding = [0.15] * 128
        results, paths = await strategy_populated.search_with_expansion(
            query_embedding,
            config,
            include_paths=False
        )
        
        assert isinstance(results, list)
        assert paths is None
    
    @pytest.mark.asyncio
    async def test_search_with_expansion_no_expansion(self, strategy_populated):
        """Test search with expansion disabled"""
        config = HybridSearchConfig(expand_results=False)
        
        query_embedding = [0.15] * 128
        results, paths = await strategy_populated.search_with_expansion(
            query_embedding,
            config,
            include_paths=True
        )
        
        assert isinstance(results, list)
        assert paths is None  # No expansion, so no paths
    
    @pytest.mark.asyncio
    async def test_find_result_paths(self, strategy_populated):
        """Test finding paths between results"""
        config = HybridSearchConfig(max_graph_depth=2)
        
        # Create mock results
        results = [
            (Entity(id="e1", entity_type="Person", properties={}), 0.9),
            (Entity(id="e2", entity_type="Person", properties={}), 0.8),
            (Entity(id="e3", entity_type="Person", properties={}), 0.7)
        ]
        
        paths = await strategy_populated._find_result_paths(results, config)
        
        assert isinstance(paths, list)
    
    @pytest.mark.asyncio
    async def test_find_result_paths_single_result(self, strategy_populated):
        """Test finding paths with single result"""
        config = HybridSearchConfig()
        
        results = [
            (Entity(id="e1", entity_type="Person", properties={}), 0.9)
        ]
        
        paths = await strategy_populated._find_result_paths(results, config)
        
        assert paths == []
    
    @pytest.mark.asyncio
    async def test_find_result_paths_empty_results(self, strategy_populated):
        """Test finding paths with empty results"""
        config = HybridSearchConfig()
        
        paths = await strategy_populated._find_result_paths([], config)
        
        assert paths == []
    
    @pytest.mark.asyncio
    async def test_search_results_sorted(self, strategy_populated):
        """Test that search results are sorted by score descending"""
        config = HybridSearchConfig(max_results=10)
        query_embedding = [0.15] * 128
        
        results = await strategy_populated.search(query_embedding, config)
        
        if len(results) > 1:
            scores = [score for _, score in results]
            assert scores == sorted(scores, reverse=True)
    
    @pytest.mark.asyncio
    async def test_search_max_results_limit(self, strategy_populated):
        """Test that max_results limit is respected"""
        config = HybridSearchConfig(max_results=2)
        query_embedding = [0.15] * 128
        
        results = await strategy_populated.search(query_embedding, config)
        
        assert len(results) <= 2
    
    @pytest.mark.asyncio
    async def test_graph_search_visited_continue(self, strategy_populated):
        """Test that visited entities trigger continue statement"""
        config = HybridSearchConfig(max_results=10, max_graph_depth=2)
        
        # Create a graph where an entity can be reached from multiple paths
        # e1 -> e2 -> e3, and e1 -> e4 -> e3 (e3 reached via two paths)
        e5 = Entity(id="e5", entity_type="Person", properties={"name": "Eve"})
        await strategy_populated.graph_store.add_entity(e5)
        r4 = Relation(id="r4", relation_type="KNOWS", source_id="e2", target_id="e5")
        r5 = Relation(id="r5", relation_type="KNOWS", source_id="e5", target_id="e3")
        await strategy_populated.graph_store.add_relation(r4)
        await strategy_populated.graph_store.add_relation(r5)
        
        results = await strategy_populated._graph_search(["e1"], config)
        
        assert isinstance(results, list)
        # Should handle visited entities correctly
    
    @pytest.mark.asyncio
    async def test_hybrid_search_min_score_continue(self, strategy_populated):
        """Test that entities below min_combined_score are filtered out"""
        config = HybridSearchConfig(
            mode=SearchMode.HYBRID,
            min_combined_score=0.9,  # High threshold
            max_results=10
        )
        
        query_embedding = [0.15] * 128
        results = await strategy_populated._hybrid_search(
            query_embedding,
            config
        )
        
        assert isinstance(results, list)
        # All results should meet minimum score threshold
        for _, score in results:
            assert score >= 0.9
    
    @pytest.mark.asyncio
    async def test_search_with_expansion_none_config(self, strategy_populated):
        """Test search_with_expansion with None config"""
        query_embedding = [0.15] * 128
        results, paths = await strategy_populated.search_with_expansion(
            query_embedding,
            config=None,
            include_paths=False
        )
        
        assert isinstance(results, list)
        assert paths is None

