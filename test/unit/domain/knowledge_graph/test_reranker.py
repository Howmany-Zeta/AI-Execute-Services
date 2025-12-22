"""
Unit tests for result reranking framework
"""

import pytest
from aiecs.application.knowledge_graph.search.reranker import (
    RerankerStrategy,
    ResultReranker,
    ScoreCombinationMethod,
    normalize_scores,
    combine_scores,
)
from aiecs.domain.knowledge_graph.models.entity import Entity


class MockRerankerStrategy(RerankerStrategy):
    """Mock strategy for testing"""
    
    def __init__(self, name: str, scores: list):
        self._name = name
        self._scores = scores
    
    @property
    def name(self) -> str:
        return self._name
    
    async def score(
        self,
        query: str,
        entities: list,
        **kwargs
    ) -> list:
        return self._scores


class TestNormalizeScores:
    """Test score normalization utilities"""
    
    def test_normalize_min_max(self):
        """Test min-max normalization"""
        scores = [1.0, 2.0, 3.0, 4.0, 5.0]
        normalized = normalize_scores(scores, method="min_max")
        
        assert len(normalized) == len(scores)
        assert normalized[0] == 0.0  # Min becomes 0
        assert abs(normalized[-1] - 1.0) < 1e-10  # Max becomes 1
        assert all(0.0 <= s <= 1.0 for s in normalized)
    
    def test_normalize_min_max_same_values(self):
        """Test min-max normalization with identical values"""
        scores = [5.0, 5.0, 5.0]
        normalized = normalize_scores(scores, method="min_max")
        
        assert all(abs(s - 1.0) < 1e-10 for s in normalized)
    
    def test_normalize_z_score(self):
        """Test z-score normalization"""
        scores = [1.0, 2.0, 3.0, 4.0, 5.0]
        normalized = normalize_scores(scores, method="z_score")
        
        assert len(normalized) == len(scores)
        assert all(0.0 <= s <= 1.0 for s in normalized)
    
    def test_normalize_softmax(self):
        """Test softmax normalization"""
        scores = [1.0, 2.0, 3.0]
        normalized = normalize_scores(scores, method="softmax")
        
        assert len(normalized) == len(scores)
        assert abs(sum(normalized) - 1.0) < 1e-10  # Sum to 1
        assert all(0.0 <= s <= 1.0 for s in normalized)
    
    def test_normalize_empty(self):
        """Test normalization with empty list"""
        assert normalize_scores([]) == []
    
    def test_normalize_single_value(self):
        """Test normalization with single value"""
        normalized = normalize_scores([5.0])
        assert normalized == [1.0]


class TestCombineScores:
    """Test score combination utilities"""
    
    def test_combine_weighted_average(self):
        """Test weighted average combination"""
        score_dicts = [
            {"e1": 0.8, "e2": 0.6, "e3": 0.4},
            {"e1": 0.6, "e2": 0.8, "e3": 0.2},
        ]
        weights = {"strategy_0": 0.6, "strategy_1": 0.4}
        
        combined = combine_scores(
            score_dicts,
            method=ScoreCombinationMethod.WEIGHTED_AVERAGE,
            weights=weights
        )
        
        assert "e1" in combined
        assert "e2" in combined
        assert "e3" in combined
        # e1: 0.8*0.6 + 0.6*0.4 = 0.48 + 0.24 = 0.72
        assert abs(combined["e1"] - 0.72) < 1e-10
    
    def test_combine_weighted_average_equal_weights(self):
        """Test weighted average with equal weights"""
        score_dicts = [
            {"e1": 0.8, "e2": 0.6},
            {"e1": 0.6, "e2": 0.8},
        ]
        
        combined = combine_scores(
            score_dicts,
            method=ScoreCombinationMethod.WEIGHTED_AVERAGE
        )
        
        # Equal weights: (0.8 + 0.6) / 2 = 0.7
        assert abs(combined["e1"] - 0.7) < 1e-10
        assert abs(combined["e2"] - 0.7) < 1e-10
    
    def test_combine_rrf(self):
        """Test Reciprocal Rank Fusion"""
        score_dicts = [
            {"e1": 0.9, "e2": 0.8, "e3": 0.7},  # e1 rank 1, e2 rank 2, e3 rank 3
            {"e1": 0.7, "e2": 0.9, "e3": 0.8},  # e2 rank 1, e3 rank 2, e1 rank 3
        ]
        
        combined = combine_scores(
            score_dicts,
            method=ScoreCombinationMethod.RRF
        )
        
        assert "e1" in combined
        assert "e2" in combined
        assert "e3" in combined
        # e2 should have highest RRF (rank 1 in second strategy)
        assert combined["e2"] > combined["e1"]
    
    def test_combine_max(self):
        """Test max combination"""
        score_dicts = [
            {"e1": 0.8, "e2": 0.6},
            {"e1": 0.6, "e2": 0.9},
        ]
        
        combined = combine_scores(
            score_dicts,
            method=ScoreCombinationMethod.MAX
        )
        
        assert combined["e1"] == 0.8
        assert combined["e2"] == 0.9
    
    def test_combine_min(self):
        """Test min combination"""
        score_dicts = [
            {"e1": 0.8, "e2": 0.6},
            {"e1": 0.6, "e2": 0.9},
        ]
        
        combined = combine_scores(
            score_dicts,
            method=ScoreCombinationMethod.MIN
        )
        
        assert combined["e1"] == 0.6
        assert combined["e2"] == 0.6
    
    def test_combine_empty(self):
        """Test combination with empty list"""
        assert combine_scores([]) == {}
    
    def test_combine_missing_entities(self):
        """Test combination when entities missing from some strategies"""
        score_dicts = [
            {"e1": 0.8, "e2": 0.6},
            {"e1": 0.6},  # e2 missing
        ]
        
        combined = combine_scores(
            score_dicts,
            method=ScoreCombinationMethod.WEIGHTED_AVERAGE
        )
        
        assert "e1" in combined
        assert "e2" in combined
        # e2 should have lower score (0.6 / 2 = 0.3)
        assert combined["e2"] < combined["e1"]


class TestRerankerStrategy:
    """Test RerankerStrategy abstract base class"""
    
    def test_strategy_interface(self):
        """Test that strategy implements required interface"""
        strategy = MockRerankerStrategy("test", [0.5, 0.7, 0.9])
        
        assert strategy.name == "test"
        assert isinstance(strategy, RerankerStrategy)


class TestResultReranker:
    """Test ResultReranker orchestrator"""
    
    @pytest.mark.asyncio
    async def test_rerank_single_strategy(self):
        """Test reranking with single strategy"""
        strategy = MockRerankerStrategy("test", [0.3, 0.7, 0.5])
        reranker = ResultReranker(strategies=[strategy])
        
        entities = [
            Entity(id="e1", entity_type="Test", properties={}),
            Entity(id="e2", entity_type="Test", properties={}),
            Entity(id="e3", entity_type="Test", properties={}),
        ]
        
        reranked = await reranker.rerank("query", entities)
        
        assert len(reranked) == 3
        # Should be sorted by score descending
        assert reranked[0][1] >= reranked[1][1]
        assert reranked[1][1] >= reranked[2][1]
        # e2 should be first (score 0.7)
        assert reranked[0][0].id == "e2"
    
    @pytest.mark.asyncio
    async def test_rerank_multiple_strategies(self):
        """Test reranking with multiple strategies"""
        strategy1 = MockRerankerStrategy("strategy1", [0.8, 0.6, 0.4])
        strategy2 = MockRerankerStrategy("strategy2", [0.6, 0.9, 0.3])
        
        reranker = ResultReranker(
            strategies=[strategy1, strategy2],
            combination_method=ScoreCombinationMethod.WEIGHTED_AVERAGE
        )
        
        entities = [
            Entity(id="e1", entity_type="Test", properties={}),
            Entity(id="e2", entity_type="Test", properties={}),
            Entity(id="e3", entity_type="Test", properties={}),
        ]
        
        reranked = await reranker.rerank("query", entities)
        
        assert len(reranked) == 3
        # Should be sorted by combined score
        assert reranked[0][1] >= reranked[1][1]
        assert reranked[1][1] >= reranked[2][1]
    
    @pytest.mark.asyncio
    async def test_rerank_with_weights(self):
        """Test reranking with custom weights"""
        strategy1 = MockRerankerStrategy("strategy1", [0.9, 0.1])
        strategy2 = MockRerankerStrategy("strategy2", [0.1, 0.9])
        
        reranker = ResultReranker(
            strategies=[strategy1, strategy2],
            combination_method=ScoreCombinationMethod.WEIGHTED_AVERAGE,
            weights={"strategy_0": 0.8, "strategy_1": 0.2}
        )
        
        entities = [
            Entity(id="e1", entity_type="Test", properties={}),
            Entity(id="e2", entity_type="Test", properties={}),
        ]
        
        reranked = await reranker.rerank("query", entities)
        
        # e1 should rank higher (0.9*0.8 + 0.1*0.2 = 0.74)
        # e2 should rank lower (0.1*0.8 + 0.9*0.2 = 0.26)
        assert reranked[0][0].id == "e1"
        assert reranked[1][0].id == "e2"
    
    @pytest.mark.asyncio
    async def test_rerank_top_k(self):
        """Test reranking with top_k limit"""
        strategy = MockRerankerStrategy("test", [0.9, 0.7, 0.5, 0.3])
        reranker = ResultReranker(strategies=[strategy])
        
        entities = [
            Entity(id=f"e{i}", entity_type="Test", properties={})
            for i in range(4)
        ]
        
        reranked = await reranker.rerank("query", entities, top_k=2)
        
        assert len(reranked) == 2
        assert reranked[0][0].id == "e0"
        assert reranked[1][0].id == "e1"
    
    @pytest.mark.asyncio
    async def test_rerank_empty_entities(self):
        """Test reranking with empty entity list"""
        strategy = MockRerankerStrategy("test", [])
        reranker = ResultReranker(strategies=[strategy])
        
        reranked = await reranker.rerank("query", [])
        
        assert reranked == []
    
    @pytest.mark.asyncio
    async def test_rerank_no_normalization(self):
        """Test reranking without score normalization"""
        strategy = MockRerankerStrategy("test", [10.0, 5.0, 1.0])
        reranker = ResultReranker(
            strategies=[strategy],
            normalize_scores=False
        )
        
        entities = [
            Entity(id=f"e{i}", entity_type="Test", properties={})
            for i in range(3)
        ]
        
        reranked = await reranker.rerank("query", entities)
        
        # Scores should remain unnormalized
        assert reranked[0][1] == 10.0
        assert reranked[1][1] == 5.0
        assert reranked[2][1] == 1.0
    
    def test_reranker_init_no_strategies(self):
        """Test that reranker requires at least one strategy"""
        with pytest.raises(ValueError, match="At least one strategy"):
            ResultReranker(strategies=[])
    
    @pytest.mark.asyncio
    async def test_rerank_rrf_method(self):
        """Test reranking with RRF combination method"""
        strategy1 = MockRerankerStrategy("strategy1", [0.9, 0.5, 0.1])
        strategy2 = MockRerankerStrategy("strategy2", [0.1, 0.9, 0.5])
        
        reranker = ResultReranker(
            strategies=[strategy1, strategy2],
            combination_method=ScoreCombinationMethod.RRF
        )
        
        entities = [
            Entity(id=f"e{i}", entity_type="Test", properties={})
            for i in range(3)
        ]
        
        reranked = await reranker.rerank("query", entities)
        
        assert len(reranked) == 3
        # e1 should rank highest (rank 1 in strategy2)
        assert reranked[0][0].id == "e1"

