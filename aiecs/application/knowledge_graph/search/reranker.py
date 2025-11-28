"""
Result Reranking Framework

Pluggable reranking strategies for improving search result relevance.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Tuple, Set
from enum import Enum

from aiecs.domain.knowledge_graph.models.entity import Entity


class ScoreCombinationMethod(str, Enum):
    """Methods for combining scores from multiple reranking strategies"""

    WEIGHTED_AVERAGE = "weighted_average"
    RRF = "rrf"  # Reciprocal Rank Fusion
    MAX = "max"
    MIN = "min"


class RerankerStrategy(ABC):
    """
    Abstract base class for reranking strategies

    Each strategy computes a relevance score for entities given a query.
    Strategies can be combined using different combination methods.

    Example::

        class TextSimilarityReranker(RerankerStrategy):
            async def score(
                self,
                query: str,
                entities: List[Entity]
            ) -> List[float]:
                # Compute BM25 scores
                return scores
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Strategy name for identification"""

    @abstractmethod
    async def score(self, query: str, entities: List[Entity], **kwargs) -> List[float]:
        """
        Compute relevance scores for entities

        Args:
            query: Query text or context
            entities: List of entities to score
            **kwargs: Strategy-specific parameters

        Returns:
            List of scores (one per entity), same order as entities
            Scores should be in range [0.0, 1.0] for best results
        """


def normalize_scores(scores: List[float], method: str = "min_max") -> List[float]:
    """
    Normalize scores to [0.0, 1.0] range

    Args:
        scores: Raw scores to normalize
        method: Normalization method ("min_max", "z_score", "softmax")

    Returns:
        Normalized scores in [0.0, 1.0] range
    """
    if not scores:
        return []

    if method == "min_max":
        min_score = min(scores)
        max_score = max(scores)
        if max_score == min_score:
            return [1.0] * len(scores)
        return [(s - min_score) / (max_score - min_score) for s in scores]

    elif method == "z_score":
        import statistics

        if len(scores) < 2:
            return [1.0] * len(scores)
        mean = statistics.mean(scores)
        stdev = statistics.stdev(scores) if len(scores) > 1 else 1.0
        if stdev == 0:
            return [1.0] * len(scores)
        # Normalize to [0, 1] using sigmoid
        normalized = [(s - mean) / stdev for s in scores]
        import math

        return [1 / (1 + math.exp(-n)) for n in normalized]

    elif method == "softmax":
        import math

        # Shift to avoid overflow
        max_score = max(scores)
        exp_scores = [math.exp(s - max_score) for s in scores]
        sum_exp = sum(exp_scores)
        if sum_exp == 0:
            return [1.0 / len(scores)] * len(scores)
        return [e / sum_exp for e in exp_scores]

    else:
        raise ValueError(f"Unknown normalization method: {method}")


def combine_scores(
    score_dicts: List[Dict[str, float]],
    method: ScoreCombinationMethod = ScoreCombinationMethod.WEIGHTED_AVERAGE,
    weights: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    """
    Combine scores from multiple strategies

    Args:
        score_dicts: List of {entity_id: score} dictionaries from each strategy
        method: Combination method
        weights: Optional weights for each strategy (for weighted_average)

    Returns:
        Combined scores as {entity_id: combined_score}
    """
    if not score_dicts:
        return {}

    # Collect all entity IDs
    all_entity_ids: Set[str] = set()
    for score_dict in score_dicts:
        all_entity_ids.update(score_dict.keys())

    if method == ScoreCombinationMethod.WEIGHTED_AVERAGE:
        if weights is None:
            # Equal weights
            weight = 1.0 / len(score_dicts)
            weights = {f"strategy_{i}": weight for i in range(len(score_dicts))}

        combined = {}
        for entity_id in all_entity_ids:
            weighted_sum = 0.0
            total_weight = 0.0
            for i, score_dict in enumerate(score_dicts):
                strategy_name = f"strategy_{i}"
                weight = weights.get(strategy_name, 1.0 / len(score_dicts))
                score = score_dict.get(entity_id, 0.0)
                weighted_sum += weight * score
                total_weight += weight
            combined[entity_id] = weighted_sum / total_weight if total_weight > 0 else 0.0
        return combined

    elif method == ScoreCombinationMethod.RRF:
        # Reciprocal Rank Fusion
        k = 60  # RRF constant
        combined = {}
        for entity_id in all_entity_ids:
            rrf_score = 0.0
            for score_dict in score_dicts:
                if entity_id in score_dict:
                    # Get rank (1-indexed, higher score = lower rank)
                    scores = sorted(score_dict.values(), reverse=True)
                    rank = scores.index(score_dict[entity_id]) + 1
                    rrf_score += 1.0 / (k + rank)
            combined[entity_id] = rrf_score
        return combined

    elif method == ScoreCombinationMethod.MAX:
        combined = {}
        for entity_id in all_entity_ids:
            combined[entity_id] = max(score_dict.get(entity_id, 0.0) for score_dict in score_dicts)
        return combined

    elif method == ScoreCombinationMethod.MIN:
        combined = {}
        for entity_id in all_entity_ids:
            combined[entity_id] = min(score_dict.get(entity_id, 1.0) for score_dict in score_dicts)
        return combined

    else:
        raise ValueError(f"Unknown combination method: {method}")


class ResultReranker:
    """
    Result Reranker orchestrator

    Combines multiple reranking strategies to improve search result relevance.

    Example::

        # Create strategies
        text_reranker = TextSimilarityReranker()
        semantic_reranker = SemanticReranker()

        # Create reranker
        reranker = ResultReranker(
            strategies=[text_reranker, semantic_reranker],
            combination_method=ScoreCombinationMethod.WEIGHTED_AVERAGE,
            weights={"text": 0.6, "semantic": 0.4}
        )

        # Rerank results
        reranked = await reranker.rerank(
            query="machine learning",
            entities=search_results
        )
    """

    def __init__(
        self,
        strategies: List[RerankerStrategy],
        combination_method: ScoreCombinationMethod = ScoreCombinationMethod.WEIGHTED_AVERAGE,
        weights: Optional[Dict[str, float]] = None,
        normalize_scores: bool = True,
        normalization_method: str = "min_max",
    ):
        """
        Initialize ResultReranker

        Args:
            strategies: List of reranking strategies
            combination_method: Method for combining scores
            weights: Optional weights for strategies (for weighted_average)
            normalize_scores: Whether to normalize scores before combining
            normalization_method: Normalization method ("min_max", "z_score", "softmax")
        """
        if not strategies:
            raise ValueError("At least one strategy is required")

        self.strategies = strategies
        self.combination_method = combination_method
        self.weights = weights or {}
        self.normalize_scores = normalize_scores
        self.normalization_method = normalization_method

    async def rerank(
        self,
        query: str,
        entities: List[Entity],
        top_k: Optional[int] = None,
        **kwargs,
    ) -> List[Tuple[Entity, float]]:
        """
        Rerank entities using all strategies

        Args:
            query: Query text or context
            entities: List of entities to rerank
            top_k: Optional limit on number of results
            **kwargs: Additional parameters passed to strategies

        Returns:
            List of (entity, combined_score) tuples, sorted by score descending
        """
        if not entities:
            return []

        # Get scores from each strategy
        strategy_scores = []
        for strategy in self.strategies:
            scores = await strategy.score(query, entities, **kwargs)

            # Normalize if requested
            if self.normalize_scores:
                scores = normalize_scores(scores, self.normalization_method)

            # Convert to entity_id -> score dictionary
            score_dict = {entity.id: score for entity, score in zip(entities, scores)}
            strategy_scores.append(score_dict)

        # Combine scores
        combined_scores = combine_scores(
            strategy_scores,
            method=self.combination_method,
            weights=self.weights,
        )

        # Create (entity, score) tuples
        reranked = [(entity, combined_scores.get(entity.id, 0.0)) for entity in entities]

        # Sort by score descending
        reranked.sort(key=lambda x: x[1], reverse=True)

        # Apply top_k limit
        if top_k is not None:
            reranked = reranked[:top_k]

        return reranked
