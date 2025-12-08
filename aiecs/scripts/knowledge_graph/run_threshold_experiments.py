"""
Script to run threshold sweep experiments for knowledge fusion matching.

Usage:
    poetry run python -m aiecs.scripts.knowledge_graph.run_threshold_experiments
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import List

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from aiecs.application.knowledge_graph.fusion.ab_testing import (
    ABTestingFramework,
    ExperimentResult,
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

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def run_threshold_sweeps(
    framework: ABTestingFramework,
    output_dir: Path,
) -> None:
    """
    Run threshold sweep experiments for all matching stages.

    Args:
        framework: ABTestingFramework instance
        output_dir: Directory to save results
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Define threshold ranges for each stage
    threshold_sweeps = {
        "alias_match_score": [0.90, 0.92, 0.94, 0.96, 0.98, 1.0],
        "abbreviation_match_score": [0.85, 0.88, 0.90, 0.92, 0.95, 0.98],
        "normalization_match_score": [0.80, 0.85, 0.88, 0.90, 0.92, 0.95],
        "semantic_threshold": [0.70, 0.75, 0.80, 0.85, 0.90, 0.95],
        "string_similarity_threshold": [0.70, 0.75, 0.80, 0.85, 0.90],
    }

    all_results: List[ExperimentResult] = []

    # Run sweeps for each threshold
    for threshold_name, threshold_range in threshold_sweeps.items():
        logger.info(f"Running sweep for {threshold_name}...")
        results = await framework.threshold_sweep(
            threshold_name=threshold_name,
            threshold_range=threshold_range,
        )
        all_results.extend(results)

        # Save individual sweep results
        sweep_file = output_dir / f"sweep_{threshold_name}.json"
        sweep_data = [
            {
                "config_name": r.config_name,
                "threshold_value": getattr(r.config, threshold_name),
                "metrics": r.metrics.to_dict(),
                "stage_breakdown": r.stage_breakdown,
            }
            for r in results
        ]
        with open(sweep_file, "w") as f:
            json.dump(sweep_data, f, indent=2)
        logger.info(f"Saved sweep results to {sweep_file}")

    # Evaluate default configuration
    logger.info("Evaluating default configuration...")
    default_config = FusionMatchingConfig()
    default_result = await framework.evaluate_config("default", default_config)
    all_results.append(default_result)

    # Compare all results
    comparison = framework.compare_results(all_results)
    comparison_file = output_dir / "comparison.json"
    with open(comparison_file, "w") as f:
        json.dump(comparison, f, indent=2)
    logger.info(f"Saved comparison results to {comparison_file}")

    # Validate default thresholds
    is_valid, validation = framework.validate_thresholds(
        default_result, min_recall=0.90, min_precision=0.75
    )
    validation_file = output_dir / "validation.json"
    with open(validation_file, "w") as f:
        json.dump(validation, f, indent=2)
    logger.info(f"Validation result: {'PASS' if is_valid else 'FAIL'}")
    logger.info(f"Saved validation results to {validation_file}")

    # Print summary
    print("\n" + "=" * 80)
    print("EXPERIMENT SUMMARY")
    print("=" * 80)
    print(f"\nDefault Configuration Metrics:")
    print(f"  Recall:    {default_result.metrics.recall:.3f}")
    print(f"  Precision: {default_result.metrics.precision:.3f}")
    print(f"  F1 Score:  {default_result.metrics.f1_score:.3f}")
    print(f"  Accuracy:  {default_result.metrics.accuracy:.3f}")
    print(f"\nValidation: {'PASS' if is_valid else 'FAIL'}")
    if not is_valid:
        print(f"  Recall requirement: {validation['recall']:.3f} >= {validation['min_recall']:.3f} ({'✓' if validation['recall_met'] else '✗'})")
        print(f"  Precision requirement: {validation['precision']:.3f} >= {validation['min_precision']:.3f} ({'✓' if validation['precision_met'] else '✗'})")
    print("\n" + "=" * 80)


async def run_domain_specific_experiments(
    framework: ABTestingFramework,
    output_dir: Path,
) -> None:
    """
    Run experiments for domain-specific datasets.

    Args:
        framework: ABTestingFramework instance
        output_dir: Directory to save results
    """
    domains = ["academic", "corporate", "medical"]
    domain_results: dict = {}

    for domain in domains:
        logger.info(f"Running experiments for {domain} domain...")
        domain_dataset = framework._dataset.get_by_domain(domain)

        # Create domain-specific framework
        domain_framework = ABTestingFramework(
            pipeline=framework._pipeline,
            dataset=domain_dataset,
        )

        # Evaluate default config on domain dataset
        default_config = FusionMatchingConfig()
        result = await domain_framework.evaluate_config(
            f"default_{domain}", default_config
        )

        domain_results[domain] = {
            "dataset_size": len(domain_dataset),
            "metrics": result.metrics.to_dict(),
            "stage_breakdown": result.stage_breakdown,
        }

    # Save domain-specific results
    domain_file = output_dir / "domain_results.json"
    with open(domain_file, "w") as f:
        json.dump(domain_results, f, indent=2)
    logger.info(f"Saved domain-specific results to {domain_file}")


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Run threshold sweep experiments for knowledge fusion"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="experiment_results",
        help="Output directory for results",
    )
    parser.add_argument(
        "--domain-only",
        action="store_true",
        help="Only run domain-specific experiments",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)

    # Create evaluation dataset
    logger.info("Creating evaluation dataset...")
    dataset = create_default_evaluation_dataset()
    logger.info(f"Dataset contains {len(dataset)} pairs")

    # Initialize pipeline (without actual matchers for now - they're optional)
    pipeline = SimilarityPipeline()

    # Create framework
    framework = ABTestingFramework(pipeline=pipeline, dataset=dataset)

    if args.domain_only:
        await run_domain_specific_experiments(framework, output_dir)
    else:
        await run_threshold_sweeps(framework, output_dir)
        await run_domain_specific_experiments(framework, output_dir)

    logger.info("Experiments completed!")


if __name__ == "__main__":
    asyncio.run(main())
