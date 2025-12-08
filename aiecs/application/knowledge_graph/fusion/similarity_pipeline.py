"""
Enhanced Similarity Pipeline for Knowledge Graph Entity Matching.

Orchestrates multiple matching strategies in a configurable pipeline:
1. Exact match (normalized)
2. Alias match (via AliasIndex)
3. Abbreviation match (via AbbreviationExpander)
4. Normalized name match (via NameNormalizer)
5. Semantic embedding match (via SemanticNameMatcher)
6. String similarity (fallback)

Supports per-entity-type stage filtering and early-exit optimization.
"""

import logging
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from aiecs.application.knowledge_graph.fusion.matching_config import (
    EntityTypeConfig,
    FusionMatchingConfig,
)

logger = logging.getLogger(__name__)


class MatchStage(str, Enum):
    """Matching stages in the similarity pipeline."""
    EXACT = "exact"
    ALIAS = "alias"
    ABBREVIATION = "abbreviation"
    NORMALIZED = "normalized"
    SEMANTIC = "semantic"
    STRING = "string"


@dataclass
class MatchResult:
    """
    Result from a matching stage.

    Attributes:
        score: Similarity score (0.0 to 1.0)
        stage: Stage that produced this result
        is_match: Whether this is considered a match (above threshold)
        details: Additional details about the match
    """
    score: float
    stage: MatchStage
    is_match: bool = False
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineResult:
    """
    Result from the full similarity pipeline.

    Attributes:
        final_score: Final similarity score after pipeline execution
        is_match: Whether the entities are considered a match
        matched_stage: Stage that produced the match (if any)
        stage_results: Results from each stage that was executed
        early_exit: Whether pipeline exited early on high-confidence match
    """
    final_score: float
    is_match: bool
    matched_stage: Optional[MatchStage] = None
    stage_results: List[MatchResult] = field(default_factory=list)
    early_exit: bool = False


class SimilarityPipeline:
    """
    Orchestrates multiple matching strategies for entity similarity.

    The pipeline executes matching stages in order, supporting:
    - Per-entity-type stage filtering
    - Early exit on high-confidence matches
    - Configurable thresholds for each stage

    Example:
        ```python
        config = FusionMatchingConfig(
            alias_match_score=0.98,
            entity_type_configs={
                "Person": EntityTypeConfig(
                    enabled_stages=["exact", "alias", "normalized"],
                    semantic_enabled=False
                )
            }
        )

        pipeline = SimilarityPipeline(
            config=config,
            alias_matcher=alias_matcher,
            abbreviation_expander=expander,
            name_normalizer=normalizer,
            semantic_matcher=semantic_matcher,
        )

        result = await pipeline.compute_similarity(
            name1="Dr. John Smith",
            name2="J. Smith",
            entity_type="Person"
        )
        ```
    """

    # Default stage order
    DEFAULT_STAGE_ORDER = [
        MatchStage.EXACT,
        MatchStage.ALIAS,
        MatchStage.ABBREVIATION,
        MatchStage.NORMALIZED,
        MatchStage.SEMANTIC,
        MatchStage.STRING,
    ]

    def __init__(
        self,
        config: Optional[FusionMatchingConfig] = None,
        alias_matcher: Optional[Any] = None,
        abbreviation_expander: Optional[Any] = None,
        name_normalizer: Optional[Any] = None,
        semantic_matcher: Optional[Any] = None,
        early_exit_threshold: float = 0.95,
    ):
        """
        Initialize similarity pipeline.

        Args:
            config: Matching configuration (uses defaults if not provided)
            alias_matcher: AliasMatcher instance for alias lookup
            abbreviation_expander: AbbreviationExpander for acronym handling
            name_normalizer: NameNormalizer for name normalization
            semantic_matcher: SemanticNameMatcher for embedding-based matching
            early_exit_threshold: Score threshold for early exit (skip later stages)
        """
        self._config = config or FusionMatchingConfig()
        self._alias_matcher = alias_matcher
        self._abbreviation_expander = abbreviation_expander
        self._name_normalizer = name_normalizer
        self._semantic_matcher = semantic_matcher
        self._early_exit_threshold = early_exit_threshold

        # Statistics
        self._match_counts: Dict[MatchStage, int] = {stage: 0 for stage in MatchStage}
        self._early_exit_count = 0
        self._total_comparisons = 0

    @property
    def config(self) -> FusionMatchingConfig:
        """Get current configuration."""
        return self._config

    def set_config(self, config: FusionMatchingConfig) -> None:
        """Update configuration."""
        self._config = config

    def set_alias_matcher(self, matcher: Any) -> None:
        """Set alias matcher instance."""
        self._alias_matcher = matcher

    def set_abbreviation_expander(self, expander: Any) -> None:
        """Set abbreviation expander instance."""
        self._abbreviation_expander = expander

    def set_name_normalizer(self, normalizer: Any) -> None:
        """Set name normalizer instance."""
        self._name_normalizer = normalizer

    def set_semantic_matcher(self, matcher: Any) -> None:
        """Set semantic matcher instance."""
        self._semantic_matcher = matcher

    async def compute_similarity(
        self,
        name1: str,
        name2: str,
        entity_type: Optional[str] = None,
        threshold: Optional[float] = None,
    ) -> PipelineResult:
        """
        Compute similarity between two names using the matching pipeline.

        Executes stages in order, respecting per-entity-type configuration
        and early-exit optimization.

        Args:
            name1: First name to compare
            name2: Second name to compare
            entity_type: Entity type for per-type configuration (optional)
            threshold: Override threshold for match determination (optional)

        Returns:
            PipelineResult with score and stage information
        """
        self._total_comparisons += 1

        # Get effective config for entity type
        type_config = self._config.get_config_for_type(entity_type or "_default")

        # Determine effective threshold
        effective_threshold = threshold or self._config.semantic_threshold

        # Get enabled stages for this entity type
        enabled_stages = self._get_enabled_stages(type_config)

        # Execute pipeline
        stage_results: List[MatchResult] = []
        best_score = 0.0
        matched_stage: Optional[MatchStage] = None
        early_exit = False

        for stage in self.DEFAULT_STAGE_ORDER:
            if stage not in enabled_stages:
                continue

            result = await self._execute_stage(
                stage, name1, name2, type_config
            )
            stage_results.append(result)

            if result.score > best_score:
                best_score = result.score
                matched_stage = stage

            # Check for early exit on high-confidence match
            if result.score >= self._early_exit_threshold:
                self._early_exit_count += 1
                early_exit = True
                logger.debug(
                    f"Early exit at stage {stage.value} with score {result.score:.3f}"
                )
                break

        # Determine if this is a match
        is_match = best_score >= effective_threshold
        if is_match and matched_stage:
            self._match_counts[matched_stage] += 1

        return PipelineResult(
            final_score=best_score,
            is_match=is_match,
            matched_stage=matched_stage,
            stage_results=stage_results,
            early_exit=early_exit,
        )

    def _get_enabled_stages(
        self, type_config: EntityTypeConfig
    ) -> List[MatchStage]:
        """Get list of enabled stages for entity type config."""
        enabled = []
        for stage in self.DEFAULT_STAGE_ORDER:
            if type_config.is_stage_enabled(stage.value):
                enabled.append(stage)
        return enabled

    async def _execute_stage(
        self,
        stage: MatchStage,
        name1: str,
        name2: str,
        type_config: EntityTypeConfig,
    ) -> MatchResult:
        """Execute a single matching stage."""
        try:
            if stage == MatchStage.EXACT:
                return self._exact_match(name1, name2)
            elif stage == MatchStage.ALIAS:
                return await self._alias_match(name1, name2, type_config)
            elif stage == MatchStage.ABBREVIATION:
                return self._abbreviation_match(name1, name2, type_config)
            elif stage == MatchStage.NORMALIZED:
                return self._normalized_match(name1, name2, type_config)
            elif stage == MatchStage.SEMANTIC:
                return await self._semantic_match(name1, name2, type_config)
            elif stage == MatchStage.STRING:
                return self._string_similarity(name1, name2, type_config)
            else:
                return MatchResult(score=0.0, stage=stage)
        except Exception as e:
            logger.warning(f"Error in stage {stage.value}: {e}")
            return MatchResult(score=0.0, stage=stage, details={"error": str(e)})

    def _exact_match(self, name1: str, name2: str) -> MatchResult:
        """Check for exact match (case-insensitive, normalized whitespace)."""
        n1 = " ".join(name1.lower().split())
        n2 = " ".join(name2.lower().split())

        if n1 == n2:
            return MatchResult(
                score=1.0,
                stage=MatchStage.EXACT,
                is_match=True,
                details={"normalized_name": n1},
            )
        return MatchResult(score=0.0, stage=MatchStage.EXACT)

    async def _alias_match(
        self, name1: str, name2: str, type_config: EntityTypeConfig
    ) -> MatchResult:
        """Check for alias match via AliasIndex."""
        if self._alias_matcher is None:
            return MatchResult(score=0.0, stage=MatchStage.ALIAS)

        # Look up both names in alias index
        match1 = await self._alias_matcher.lookup(name1)
        match2 = await self._alias_matcher.lookup(name2)

        # Check if they point to the same entity
        if match1 and match2 and match1.entity_id == match2.entity_id:
            score = type_config.get_threshold(
                "alias_match_score", self._config.alias_match_score
            )
            return MatchResult(
                score=score,
                stage=MatchStage.ALIAS,
                is_match=True,
                details={"entity_id": match1.entity_id},
            )

        return MatchResult(score=0.0, stage=MatchStage.ALIAS)

    def _abbreviation_match(
        self, name1: str, name2: str, type_config: EntityTypeConfig
    ) -> MatchResult:
        """Check for abbreviation/acronym match."""
        if self._abbreviation_expander is None:
            return MatchResult(score=0.0, stage=MatchStage.ABBREVIATION)

        # Check if names match via abbreviation expansion
        if self._abbreviation_expander.matches(name1, name2):
            score = type_config.get_threshold(
                "abbreviation_match_score", self._config.abbreviation_match_score
            )
            return MatchResult(
                score=score,
                stage=MatchStage.ABBREVIATION,
                is_match=True,
                details={"abbreviation_match": True},
            )

        return MatchResult(score=0.0, stage=MatchStage.ABBREVIATION)

    def _normalized_match(
        self, name1: str, name2: str, type_config: EntityTypeConfig
    ) -> MatchResult:
        """Check for normalized name match (after stripping prefixes/suffixes)."""
        if self._name_normalizer is None:
            return MatchResult(score=0.0, stage=MatchStage.NORMALIZED)

        result1 = self._name_normalizer.normalize(name1)
        result2 = self._name_normalizer.normalize(name2)

        # Check exact normalized match
        if result1.normalized == result2.normalized:
            score = type_config.get_threshold(
                "normalization_match_score", self._config.normalization_match_score
            )
            return MatchResult(
                score=score,
                stage=MatchStage.NORMALIZED,
                is_match=True,
                details={
                    "normalized1": result1.normalized,
                    "normalized2": result2.normalized,
                },
            )

        # Check if one matches with initials expanded
        if self._name_normalizer.names_match_with_initials(name1, name2):
            score = type_config.get_threshold(
                "normalization_match_score", self._config.normalization_match_score
            )
            return MatchResult(
                score=score * 0.95,  # Slightly lower for initial matches
                stage=MatchStage.NORMALIZED,
                is_match=True,
                details={"initial_match": True},
            )

        return MatchResult(score=0.0, stage=MatchStage.NORMALIZED)

    async def _semantic_match(
        self, name1: str, name2: str, type_config: EntityTypeConfig
    ) -> MatchResult:
        """Check for semantic similarity via embeddings."""
        if self._semantic_matcher is None:
            return MatchResult(score=0.0, stage=MatchStage.SEMANTIC)

        if not type_config.semantic_enabled:
            return MatchResult(score=0.0, stage=MatchStage.SEMANTIC)

        # Get semantic threshold
        threshold = type_config.get_threshold(
            "semantic_threshold", self._config.semantic_threshold
        )

        # Compute semantic similarity
        result = await self._semantic_matcher.match(name1, name2, threshold=threshold)

        return MatchResult(
            score=result.similarity,
            stage=MatchStage.SEMANTIC,
            is_match=result.is_match,
            details={"threshold": threshold},
        )

    def _string_similarity(
        self, name1: str, name2: str, type_config: EntityTypeConfig
    ) -> MatchResult:
        """Compute string similarity as fallback."""
        # Normalize strings
        n1 = name1.lower().strip()
        n2 = name2.lower().strip()

        # One is substring of other
        if n1 in n2 or n2 in n1:
            return MatchResult(
                score=0.90,
                stage=MatchStage.STRING,
                is_match=True,
                details={"substring_match": True},
            )

        # Sequence matcher
        seq_similarity = SequenceMatcher(None, n1, n2).ratio()

        # Token overlap (for multi-word names)
        tokens1 = set(n1.split())
        tokens2 = set(n2.split())
        if tokens1 and tokens2:
            token_overlap = len(tokens1 & tokens2) / len(tokens1 | tokens2)
        else:
            token_overlap = 0.0

        # Combine scores
        final_score = max(seq_similarity, 0.7 * seq_similarity + 0.3 * token_overlap)

        threshold = type_config.get_threshold(
            "string_similarity_threshold", self._config.string_similarity_threshold
        )

        return MatchResult(
            score=final_score,
            stage=MatchStage.STRING,
            is_match=final_score >= threshold,
            details={
                "seq_similarity": seq_similarity,
                "token_overlap": token_overlap,
            },
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline execution statistics."""
        return {
            "total_comparisons": self._total_comparisons,
            "early_exit_count": self._early_exit_count,
            "early_exit_rate": (
                self._early_exit_count / self._total_comparisons
                if self._total_comparisons > 0
                else 0.0
            ),
            "match_counts": {
                stage.value: count
                for stage, count in self._match_counts.items()
            },
        }

    def reset_stats(self) -> None:
        """Reset execution statistics."""
        self._match_counts = {stage: 0 for stage in MatchStage}
        self._early_exit_count = 0
        self._total_comparisons = 0

    def compute_similarity_sync(
        self,
        name1: str,
        name2: str,
        entity_type: Optional[str] = None,
    ) -> float:
        """
        Synchronous string similarity computation (no async matchers).

        Useful for quick similarity checks without async overhead.
        Only uses exact match and string similarity stages.

        Args:
            name1: First name
            name2: Second name
            entity_type: Entity type (unused, for API consistency)

        Returns:
            Similarity score (0.0 to 1.0)
        """
        # Check exact match first
        n1 = " ".join(name1.lower().split())
        n2 = " ".join(name2.lower().split())

        if n1 == n2:
            return 1.0

        # Normalized match (if normalizer available)
        if self._name_normalizer:
            result1 = self._name_normalizer.normalize(name1)
            result2 = self._name_normalizer.normalize(name2)
            if result1.normalized == result2.normalized:
                return self._config.normalization_match_score
            if self._name_normalizer.names_match_with_initials(name1, name2):
                return self._config.normalization_match_score * 0.95

        # Abbreviation match (if expander available)
        if self._abbreviation_expander:
            if self._abbreviation_expander.matches(name1, name2):
                return self._config.abbreviation_match_score

        # String similarity fallback
        if n1 in n2 or n2 in n1:
            return 0.90

        seq_similarity = SequenceMatcher(None, n1, n2).ratio()
        tokens1 = set(n1.split())
        tokens2 = set(n2.split())
        if tokens1 and tokens2:
            token_overlap = len(tokens1 & tokens2) / len(tokens1 | tokens2)
        else:
            token_overlap = 0.0

        return max(seq_similarity, 0.7 * seq_similarity + 0.3 * token_overlap)