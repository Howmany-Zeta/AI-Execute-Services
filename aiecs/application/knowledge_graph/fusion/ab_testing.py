"""
A/B Testing Framework for Knowledge Fusion Threshold Validation.

Provides tools for comparing different threshold configurations and
evaluating matching performance across different parameter sets.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from aiecs.application.knowledge_graph.fusion.evaluation_dataset import (
    EntityPair,
    EvaluationDataset,
)
from aiecs.application.knowledge_graph.fusion.matching_config import (
    FusionMatchingConfig,
)
from aiecs.application.knowledge_graph.fusion.similarity_pipeline import (
    MatchStage,
    PipelineResult,
    SimilarityPipeline,
)

logger = logging.getLogger(__name__)


@dataclass
class EvaluationMetrics:
    """
    Metrics for evaluating matching performance.

    Attributes:
        true_positives: Number of correct matches
        false_positives: Number of incorrect matches
        false_negatives: Number of missed matches
        true_negatives: Number of correct non-matches
        precision: Precision score (TP / (TP + FP))
        recall: Recall score (TP / (TP + FN))
        f1_score: F1 score (harmonic mean of precision and recall)
        accuracy: Overall accuracy ((TP + TN) / Total)
    """

    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    true_negatives: int = 0

    @property
    def precision(self) -> float:
        """Calculate precision."""
        total_positive = self.true_positives + self.false_positives
        if total_positive == 0:
            return 0.0
        return self.true_positives / total_positive

    @property
    def recall(self) -> float:
        """Calculate recall."""
        total_should_match = self.true_positives + self.false_negatives
        if total_should_match == 0:
            return 0.0
        return self.true_positives / total_should_match

    @property
    def f1_score(self) -> float:
        """Calculate F1 score."""
        p = self.precision
        r = self.recall
        if p + r == 0:
            return 0.0
        return 2 * (p * r) / (p + r)

    @property
    def accuracy(self) -> float:
        """Calculate overall accuracy."""
        total = (
            self.true_positives
            + self.false_positives
            + self.false_negatives
            + self.true_negatives
        )
        if total == 0:
            return 0.0
        return (self.true_positives + self.true_negatives) / total

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "true_negatives": self.true_negatives,
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
            "accuracy": self.accuracy,
        }


@dataclass
class ExperimentResult:
    """
    Result from a single threshold configuration experiment.

    Attributes:
        config_name: Name/identifier for this configuration
        config: The FusionMatchingConfig used
        metrics: Evaluation metrics
        stage_breakdown: Breakdown of matches by stage
        errors: List of errors encountered during evaluation
    """

    config_name: str
    config: FusionMatchingConfig
    metrics: EvaluationMetrics
    stage_breakdown: Dict[str, int] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


class ABTestingFramework:
    """
    A/B Testing framework for comparing threshold configurations.

    Example:
        ```python
        framework = ABTestingFramework(
            pipeline=pipeline,
            dataset=evaluation_dataset
        )

        # Test default config
        default_result = await framework.evaluate_config(
            "default",
            FusionMatchingConfig()
        )

        # Test custom config
        custom_config = FusionMatchingConfig(
            semantic_threshold=0.80,
            alias_match_score=0.95
        )
        custom_result = await framework.evaluate_config(
            "custom",
            custom_config
        )

        # Compare results
        comparison = framework.compare_results([default_result, custom_result])
        ```
    """

    def __init__(
        self,
        pipeline: SimilarityPipeline,
        dataset: EvaluationDataset,
    ):
        """
        Initialize A/B testing framework.

        Args:
            pipeline: SimilarityPipeline instance for matching
            dataset: EvaluationDataset with test cases
        """
        self._pipeline = pipeline
        self._dataset = dataset

    async def evaluate_config(
        self,
        config_name: str,
        config: FusionMatchingConfig,
        entity_type: Optional[str] = None,
    ) -> ExperimentResult:
        """
        Evaluate a threshold configuration against the dataset.

        Args:
            config_name: Name/identifier for this configuration
            config: FusionMatchingConfig to evaluate
            entity_type: Optional entity type filter

        Returns:
            ExperimentResult with metrics and breakdown
        """
        logger.info(f"Evaluating configuration: {config_name}")

        # Update pipeline config
        self._pipeline.set_config(config)

        # Filter dataset if entity type specified
        test_dataset = self._dataset
        if entity_type:
            test_dataset = self._dataset.get_by_type(entity_type)

        # Initialize metrics
        metrics = EvaluationMetrics()
        stage_breakdown: Dict[str, int] = {}
        errors: List[str] = []

        # Evaluate each pair
        for pair in test_dataset.pairs:
            try:
                result = await self._pipeline.compute_similarity(
                    name1=pair.name1,
                    name2=pair.name2,
                    entity_type=pair.entity_type or entity_type,
                )

                # Track which stage matched
                if result.is_match and result.matched_stage:
                    stage_name = result.matched_stage.value
                    stage_breakdown[stage_name] = (
                        stage_breakdown.get(stage_name, 0) + 1
                    )

                # Update metrics
                if pair.should_match:
                    if result.is_match:
                        metrics.true_positives += 1
                    else:
                        metrics.false_negatives += 1
                else:
                    if result.is_match:
                        metrics.false_positives += 1
                    else:
                        metrics.true_negatives += 1

            except Exception as e:
                error_msg = f"Error evaluating pair ({pair.name1}, {pair.name2}): {e}"
                logger.warning(error_msg)
                errors.append(error_msg)
                # Count errors as false negatives if should match, false positives if shouldn't
                if pair.should_match:
                    metrics.false_negatives += 1
                else:
                    metrics.false_positives += 1

        return ExperimentResult(
            config_name=config_name,
            config=config,
            metrics=metrics,
            stage_breakdown=stage_breakdown,
            errors=errors,
        )

    async def threshold_sweep(
        self,
        threshold_name: str,
        threshold_range: List[float],
        base_config: Optional[FusionMatchingConfig] = None,
        entity_type: Optional[str] = None,
    ) -> List[ExperimentResult]:
        """
        Perform threshold sweep for a specific threshold parameter.

        Tests multiple values of a threshold to find optimal value.

        Args:
            threshold_name: Name of threshold to sweep (e.g., "semantic_threshold")
            threshold_range: List of threshold values to test
            base_config: Base configuration (uses default if not provided)
            entity_type: Optional entity type filter

        Returns:
            List of ExperimentResult for each threshold value
        """
        if base_config is None:
            base_config = FusionMatchingConfig()

        results: List[ExperimentResult] = []

        for threshold_value in threshold_range:
            # Create config with modified threshold
            config = FusionMatchingConfig(
                alias_match_score=base_config.alias_match_score,
                abbreviation_match_score=base_config.abbreviation_match_score,
                normalization_match_score=base_config.normalization_match_score,
                semantic_threshold=base_config.semantic_threshold,
                string_similarity_threshold=base_config.string_similarity_threshold,
                enabled_stages=base_config.enabled_stages.copy(),
                semantic_enabled=base_config.semantic_enabled,
                entity_type_configs=base_config.entity_type_configs.copy(),
            )

            # Set the threshold being swept
            if threshold_name == "alias_match_score":
                config.alias_match_score = threshold_value
            elif threshold_name == "abbreviation_match_score":
                config.abbreviation_match_score = threshold_value
            elif threshold_name == "normalization_match_score":
                config.normalization_match_score = threshold_value
            elif threshold_name == "semantic_threshold":
                config.semantic_threshold = threshold_value
            elif threshold_name == "string_similarity_threshold":
                config.string_similarity_threshold = threshold_value
            else:
                raise ValueError(f"Unknown threshold name: {threshold_name}")

            config_name = f"{threshold_name}_{threshold_value:.3f}"
            result = await self.evaluate_config(config_name, config, entity_type)
            results.append(result)

        return results

    def compare_results(
        self, results: List[ExperimentResult]
    ) -> Dict[str, Any]:
        """
        Compare multiple experiment results.

        Args:
            results: List of ExperimentResult to compare

        Returns:
            Dictionary with comparison metrics
        """
        if not results:
            return {}

        comparison = {
            "configs": [],
            "best_precision": None,
            "best_recall": None,
            "best_f1": None,
            "best_accuracy": None,
        }

        best_precision_score = -1
        best_recall_score = -1
        best_f1_score = -1
        best_accuracy_score = -1

        for result in results:
            config_info = {
                "name": result.config_name,
                "metrics": result.metrics.to_dict(),
                "stage_breakdown": result.stage_breakdown,
                "errors": len(result.errors),
            }
            comparison["configs"].append(config_info)

            # Track best scores
            if result.metrics.precision > best_precision_score:
                best_precision_score = result.metrics.precision
                comparison["best_precision"] = result.config_name

            if result.metrics.recall > best_recall_score:
                best_recall_score = result.metrics.recall
                comparison["best_recall"] = result.config_name

            if result.metrics.f1_score > best_f1_score:
                best_f1_score = result.metrics.f1_score
                comparison["best_f1"] = result.config_name

            if result.metrics.accuracy > best_accuracy_score:
                best_accuracy_score = result.metrics.accuracy
                comparison["best_accuracy"] = result.config_name

        return comparison

    def validate_thresholds(
        self,
        result: ExperimentResult,
        min_recall: float = 0.90,
        min_precision: float = 0.75,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate that thresholds meet minimum performance requirements.

        Args:
            result: ExperimentResult to validate
            min_recall: Minimum recall requirement (default: 0.90)
            min_precision: Minimum precision requirement (default: 0.75)

        Returns:
            Tuple of (is_valid, validation_details)
        """
        metrics = result.metrics
        is_valid = (
            metrics.recall >= min_recall and metrics.precision >= min_precision
        )

        validation_details = {
            "is_valid": is_valid,
            "recall": metrics.recall,
            "precision": metrics.precision,
            "f1_score": metrics.f1_score,
            "min_recall": min_recall,
            "min_precision": min_precision,
            "recall_met": metrics.recall >= min_recall,
            "precision_met": metrics.precision >= min_precision,
        }

        return is_valid, validation_details
