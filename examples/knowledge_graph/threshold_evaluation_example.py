"""
Example: Using the A/B Testing Framework for Threshold Evaluation

This example demonstrates how to:
1. Create an evaluation dataset
2. Set up the A/B testing framework
3. Evaluate different threshold configurations
4. Compare results and validate performance
"""

import asyncio
import logging

from aiecs.application.knowledge_graph.fusion.ab_testing import (
    ABTestingFramework,
)
from aiecs.application.knowledge_graph.fusion.evaluation_dataset import (
    create_default_evaluation_dataset,
)
from aiecs.application.knowledge_graph.fusion.matching_config import (
    FusionMatchingConfig,
)
from aiecs.application.knowledge_graph.fusion.similarity_pipeline import (
    SimilarityPipeline,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Run threshold evaluation example."""
    # Step 1: Create evaluation dataset
    logger.info("Creating evaluation dataset...")
    dataset = create_default_evaluation_dataset()
    logger.info(f"Dataset contains {len(dataset)} entity pairs")
    logger.info(f"  Positive pairs (should match): {len(dataset.get_positive_pairs())}")
    logger.info(f"  Negative pairs (should not match): {len(dataset.get_negative_pairs())}")

    # Step 2: Initialize similarity pipeline
    logger.info("Initializing similarity pipeline...")
    pipeline = SimilarityPipeline()
    # Note: In production, you would configure matchers:
    # pipeline.set_alias_matcher(alias_matcher)
    # pipeline.set_abbreviation_expander(abbreviation_expander)
    # pipeline.set_name_normalizer(name_normalizer)
    # pipeline.set_semantic_matcher(semantic_matcher)

    # Step 3: Create A/B testing framework
    logger.info("Setting up A/B testing framework...")
    framework = ABTestingFramework(pipeline=pipeline, dataset=dataset)

    # Step 4: Evaluate default configuration
    logger.info("\nEvaluating default configuration...")
    default_config = FusionMatchingConfig()
    default_result = await framework.evaluate_config("default", default_config)

    print("\n" + "=" * 80)
    print("DEFAULT CONFIGURATION RESULTS")
    print("=" * 80)
    print(f"True Positives:  {default_result.metrics.true_positives}")
    print(f"False Positives: {default_result.metrics.false_positives}")
    print(f"False Negatives: {default_result.metrics.false_negatives}")
    print(f"True Negatives:  {default_result.metrics.true_negatives}")
    print(f"\nPrecision: {default_result.metrics.precision:.3f}")
    print(f"Recall:    {default_result.metrics.recall:.3f}")
    print(f"F1 Score:  {default_result.metrics.f1_score:.3f}")
    print(f"Accuracy:  {default_result.metrics.accuracy:.3f}")
    print(f"\nStage Breakdown: {default_result.stage_breakdown}")

    # Step 5: Validate against requirements
    logger.info("\nValidating thresholds...")
    is_valid, validation = framework.validate_thresholds(
        default_result, min_recall=0.90, min_precision=0.75
    )
    print("\n" + "=" * 80)
    print("VALIDATION RESULTS")
    print("=" * 80)
    print(f"Valid: {'✓ PASS' if is_valid else '✗ FAIL'}")
    print(f"Recall:    {validation['recall']:.3f} (required: ≥ {validation['min_recall']:.3f}) {'✓' if validation['recall_met'] else '✗'}")
    print(f"Precision: {validation['precision']:.3f} (required: ≥ {validation['min_precision']:.3f}) {'✓' if validation['precision_met'] else '✗'}")

    # Step 6: Test custom configuration (higher recall)
    logger.info("\nEvaluating high-recall configuration...")
    high_recall_config = FusionMatchingConfig(
        semantic_threshold=0.80,  # Lower threshold for more matches
        string_similarity_threshold=0.75,
    )
    high_recall_result = await framework.evaluate_config(
        "high_recall", high_recall_config
    )

    print("\n" + "=" * 80)
    print("HIGH-RECALL CONFIGURATION RESULTS")
    print("=" * 80)
    print(f"Precision: {high_recall_result.metrics.precision:.3f}")
    print(f"Recall:    {high_recall_result.metrics.recall:.3f}")
    print(f"F1 Score:  {high_recall_result.metrics.f1_score:.3f}")

    # Step 7: Compare configurations
    logger.info("\nComparing configurations...")
    comparison = framework.compare_results([default_result, high_recall_result])
    print("\n" + "=" * 80)
    print("CONFIGURATION COMPARISON")
    print("=" * 80)
    print(f"Best Precision: {comparison['best_precision']}")
    print(f"Best Recall:   {comparison['best_recall']}")
    print(f"Best F1 Score: {comparison['best_f1']}")

    # Step 8: Domain-specific evaluation
    logger.info("\nEvaluating domain-specific datasets...")
    for domain in ["academic", "corporate", "medical"]:
        domain_dataset = dataset.get_by_domain(domain)
        if len(domain_dataset) > 0:
            domain_framework = ABTestingFramework(
                pipeline=pipeline, dataset=domain_dataset
            )
            domain_result = await domain_framework.evaluate_config(
                f"default_{domain}", default_config
            )
            print(f"\n{domain.upper()} Domain:")
            print(f"  Dataset size: {len(domain_dataset)}")
            print(f"  Precision: {domain_result.metrics.precision:.3f}")
            print(f"  Recall: {domain_result.metrics.recall:.3f}")

    logger.info("\nEvaluation complete!")


if __name__ == "__main__":
    asyncio.run(main())
