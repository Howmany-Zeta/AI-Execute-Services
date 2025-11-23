"""
Path Scoring and Ranking

Provides utilities for scoring and ranking graph paths based on various criteria.
"""

from typing import List, Callable, Optional, Dict, Any, Tuple
from aiecs.domain.knowledge_graph.models.path import Path


class PathScorer:
    """
    Path Scoring Utility

    Scores and ranks paths based on configurable criteria:
    - Path length (shorter/longer)
    - Relation types (preferred types)
    - Entity types (preferred types)
    - Relation weights (accumulated)
    - Custom scoring functions

    Example:
        ```python
        scorer = PathScorer()

        # Score by path length (shorter is better)
        scored_paths = scorer.score_by_length(paths, prefer_shorter=True)

        # Score by relation weights
        scored_paths = scorer.score_by_weights(paths)

        # Custom scoring
        scored_paths = scorer.score_custom(paths, lambda p: compute_score(p))

        # Rank and return top paths
        top_paths = scorer.rank_paths(scored_paths, top_k=10)
        ```
    """

    def score_by_length(
        self,
        paths: List[Path],
        prefer_shorter: bool = True,
        normalize: bool = True,
    ) -> List[Path]:
        """
        Score paths by their length

        Args:
            paths: List of paths to score
            prefer_shorter: If True, shorter paths get higher scores
            normalize: If True, normalize scores to 0-1 range

        Returns:
            List of paths with scores assigned
        """
        if not paths:
            return []

        # Get length range
        lengths = [p.length for p in paths]
        min_len = min(lengths)
        max_len = max(lengths)

        scored_paths = []
        for path in paths:
            if max_len == min_len:
                # All paths same length
                score = 1.0
            elif prefer_shorter:
                # Shorter paths get higher scores
                if normalize:
                    score = 1.0 - ((path.length - min_len) / (max_len - min_len))
                else:
                    score = 1.0 / (path.length + 1)
            else:
                # Longer paths get higher scores
                if normalize:
                    score = (path.length - min_len) / (max_len - min_len)
                else:
                    score = path.length / (max_len + 1)

            # Create new path with score
            scored_path = Path(nodes=path.nodes, edges=path.edges, score=score)
            scored_paths.append(scored_path)

        return scored_paths

    def score_by_weights(self, paths: List[Path], aggregation: str = "mean") -> List[Path]:
        """
        Score paths by relation weights

        Args:
            paths: List of paths to score
            aggregation: How to aggregate weights ("mean", "sum", "min", "max")

        Returns:
            List of paths with scores based on relation weights
        """
        scored_paths = []

        for path in paths:
            if not path.edges:
                score = 1.0
            else:
                weights = [edge.weight for edge in path.edges]

                if aggregation == "mean":
                    score = sum(weights) / len(weights)
                elif aggregation == "sum":
                    score = sum(weights) / len(weights)  # Normalized by length
                elif aggregation == "min":
                    score = min(weights)
                elif aggregation == "max":
                    score = max(weights)
                else:
                    score = sum(weights) / len(weights)  # Default to mean

            scored_path = Path(nodes=path.nodes, edges=path.edges, score=score)
            scored_paths.append(scored_path)

        return scored_paths

    def score_by_relation_types(
        self,
        paths: List[Path],
        preferred_types: List[str],
        penalty: float = 0.5,
    ) -> List[Path]:
        """
        Score paths by preferred relation types

        Args:
            paths: List of paths to score
            preferred_types: List of preferred relation types
            penalty: Score multiplier for non-preferred relations

        Returns:
            List of paths scored by relation type preferences
        """
        scored_paths = []

        for path in paths:
            if not path.edges:
                score = 1.0
            else:
                # Calculate score based on preferred types
                type_scores = []
                for edge in path.edges:
                    if edge.relation_type in preferred_types:
                        type_scores.append(1.0)
                    else:
                        type_scores.append(penalty)

                score = sum(type_scores) / len(type_scores)

            scored_path = Path(nodes=path.nodes, edges=path.edges, score=score)
            scored_paths.append(scored_path)

        return scored_paths

    def score_custom(self, paths: List[Path], scoring_fn: Callable[[Path], float]) -> List[Path]:
        """
        Score paths using a custom scoring function

        Args:
            paths: List of paths to score
            scoring_fn: Function that takes a Path and returns a score (0.0-1.0)

        Returns:
            List of paths with custom scores
        """
        scored_paths = []

        for path in paths:
            score = scoring_fn(path)
            # Clamp score to valid range
            score = max(0.0, min(1.0, score))

            scored_path = Path(nodes=path.nodes, edges=path.edges, score=score)
            scored_paths.append(scored_path)

        return scored_paths

    def combine_scores(
        self,
        paths_lists: List[List[Path]],
        weights: Optional[List[float]] = None,
    ) -> List[Path]:
        """
        Combine scores from multiple scoring methods

        Args:
            paths_lists: List of path lists (each with different scores)
            weights: Optional weights for each scoring method

        Returns:
            List of paths with combined scores
        """
        if not paths_lists:
            return []

        if weights is None:
            weights = [1.0] * len(paths_lists)

        # Normalize weights
        total_weight = sum(weights)
        weights = [w / total_weight for w in weights]

        # Build path ID to combined score mapping
        path_scores: Dict[Tuple[str, ...], Dict[str, Any]] = {}

        for paths, weight in zip(paths_lists, weights):
            for path in paths:
                # Use path node IDs as key
                path_key = tuple(p.id for p in path.nodes)

                if path_key not in path_scores:
                    path_scores[path_key] = {"path": path, "score": 0.0}

                # Add weighted score
                if path.score is not None:
                    score = path_scores[path_key]["score"]
                    if isinstance(score, (int, float)):
                        path_scores[path_key]["score"] = score + path.score * weight

        # Create scored paths
        combined_paths = []
        for data in path_scores.values():
            scored_path = Path(
                nodes=data["path"].nodes,
                edges=data["path"].edges,
                score=data["score"],
            )
            combined_paths.append(scored_path)

        return combined_paths

    def rank_paths(
        self,
        paths: List[Path],
        top_k: Optional[int] = None,
        min_score: Optional[float] = None,
    ) -> List[Path]:
        """
        Rank paths by score and return top results

        Args:
            paths: List of paths to rank
            top_k: Number of top paths to return (None = all)
            min_score: Minimum score threshold (None = no threshold)

        Returns:
            Sorted list of paths (highest score first)
        """
        # Filter by minimum score if specified
        if min_score is not None:
            paths = [p for p in paths if p.score is not None and p.score >= min_score]

        # Sort by score (descending)
        sorted_paths = sorted(
            paths,
            key=lambda p: p.score if p.score is not None else 0.0,
            reverse=True,
        )

        # Return top k if specified
        if top_k is not None:
            return sorted_paths[:top_k]

        return sorted_paths
