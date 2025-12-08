# Threshold Tuning Guide for Knowledge Fusion Matching

This guide helps you tune matching thresholds for optimal recall and precision in entity matching.

## Overview

The Knowledge Fusion system uses multiple matching stages with configurable thresholds:

1. **Exact Match** - Case-insensitive exact string match
2. **Alias Match** - Matches via known aliases (O(1) lookup)
3. **Abbreviation Match** - Matches abbreviations to full forms
4. **Normalized Match** - Matches after name normalization (prefixes, suffixes, initials)
5. **Semantic Match** - Embedding-based semantic similarity
6. **String Similarity** - Fallback string similarity (SequenceMatcher + token overlap)

Each stage has a threshold that determines when a match is considered valid.

## Default Thresholds

The system comes with default thresholds optimized for general use:

```python
FusionMatchingConfig(
    alias_match_score=0.98,
    abbreviation_match_score=0.95,
    normalization_match_score=0.90,
    semantic_threshold=0.85,
    string_similarity_threshold=0.80,
)
```

These defaults target:
- **Recall ≥ 90%** - Capture most true matches
- **Precision ≥ 75%** - Minimize false positives

## Threshold Parameters

### `alias_match_score` (default: 0.98)
Score assigned when entities match via alias index lookup.

- **Higher (0.98-1.0)**: More conservative, only high-confidence alias matches
- **Lower (0.90-0.97)**: More permissive, includes lower-confidence aliases
- **Recommendation**: Keep high (0.95+) since alias matches are deterministic

### `abbreviation_match_score` (default: 0.95)
Score assigned when names match via abbreviation expansion.

- **Higher (0.95-1.0)**: Only well-known abbreviations
- **Lower (0.85-0.94)**: Includes more abbreviation patterns
- **Recommendation**: 0.90-0.95 for general use

### `normalization_match_score` (default: 0.90)
Score assigned when names match after normalization (removing titles, suffixes, etc.).

- **Higher (0.90-0.95)**: More conservative normalization matches
- **Lower (0.80-0.89)**: More aggressive normalization
- **Recommendation**: 0.85-0.90 balances recall and precision

### `semantic_threshold` (default: 0.85)
Minimum similarity score for semantic embedding matches.

- **Higher (0.90-0.95)**: High precision, lower recall
- **Lower (0.75-0.84)**: Higher recall, more false positives
- **Recommendation**: 
  - 0.85-0.90 for general use
  - 0.80-0.85 if you need higher recall
  - 0.90+ if precision is critical

### `string_similarity_threshold` (default: 0.80)
Minimum score for fallback string similarity matching.

- **Higher (0.85-0.90)**: More conservative, fewer false positives
- **Lower (0.70-0.79)**: More matches, but more false positives
- **Recommendation**: 0.75-0.85 depending on your tolerance for false positives

## Domain-Specific Recommendations

### Academic Domain
Focus on person name matching with titles and initials:

```python
config = FusionMatchingConfig(
    alias_match_score=0.98,
    abbreviation_match_score=0.95,
    normalization_match_score=0.92,  # Higher for academic titles
    semantic_threshold=0.88,  # Higher for academic precision
    string_similarity_threshold=0.82,
)
```

### Corporate Domain
Focus on organization names and abbreviations:

```python
config = FusionMatchingConfig(
    alias_match_score=0.98,
    abbreviation_match_score=0.93,  # Lower for more abbreviation matches
    normalization_match_score=0.88,
    semantic_threshold=0.83,  # Lower for organization name variations
    string_similarity_threshold=0.78,
)
```

### Medical Domain
Focus on medical terminology and professional titles:

```python
config = FusionMatchingConfig(
    alias_match_score=0.98,
    abbreviation_match_score=0.94,  # Medical abbreviations are common
    normalization_match_score=0.90,
    semantic_threshold=0.87,  # Higher for medical precision
    string_similarity_threshold=0.80,
)
```

## Tuning Process

### Step 1: Evaluate Current Performance

Run the evaluation script to assess current thresholds:

```bash
poetry run python -m aiecs.scripts.knowledge_graph.run_threshold_experiments
```

This generates:
- `comparison.json` - Comparison of different threshold configurations
- `validation.json` - Validation against recall/precision targets
- `sweep_*.json` - Threshold sweep results for each parameter

### Step 2: Identify Issues

Review the metrics:

- **Low Recall (< 90%)**: Too many false negatives (missed matches)
  - Solution: Lower thresholds, especially `semantic_threshold` and `string_similarity_threshold`
  
- **Low Precision (< 75%)**: Too many false positives (incorrect matches)
  - Solution: Raise thresholds, especially `semantic_threshold` and `string_similarity_threshold`

### Step 3: Adjust Thresholds

Create a custom configuration:

```python
from aiecs.application.knowledge_graph.fusion.matching_config import FusionMatchingConfig

# Example: Increase recall
high_recall_config = FusionMatchingConfig(
    semantic_threshold=0.80,  # Lowered from 0.85
    string_similarity_threshold=0.75,  # Lowered from 0.80
)

# Example: Increase precision
high_precision_config = FusionMatchingConfig(
    semantic_threshold=0.90,  # Raised from 0.85
    string_similarity_threshold=0.85,  # Raised from 0.80
)
```

### Step 4: Per-Entity-Type Configuration

For fine-grained control, configure thresholds per entity type:

```python
from aiecs.application.knowledge_graph.fusion.matching_config import (
    FusionMatchingConfig,
    EntityTypeConfig,
)

config = FusionMatchingConfig(
    # Global defaults
    semantic_threshold=0.85,
    
    # Per-type overrides
    entity_type_configs={
        "Person": EntityTypeConfig(
            thresholds={
                "semantic_threshold": 0.88,  # Higher for person names
            }
        ),
        "Organization": EntityTypeConfig(
            thresholds={
                "semantic_threshold": 0.82,  # Lower for organization variations
            }
        ),
    }
)
```

### Step 5: Re-evaluate

Run experiments again with your custom configuration:

```python
from aiecs.application.knowledge_graph.fusion.ab_testing import ABTestingFramework
from aiecs.application.knowledge_graph.fusion.evaluation_dataset import create_default_evaluation_dataset
from aiecs.application.knowledge_graph.fusion.similarity_pipeline import SimilarityPipeline

# Create framework
dataset = create_default_evaluation_dataset()
pipeline = SimilarityPipeline()
framework = ABTestingFramework(pipeline=pipeline, dataset=dataset)

# Evaluate custom config
result = await framework.evaluate_config("custom", high_recall_config)

# Validate
is_valid, details = framework.validate_thresholds(
    result, min_recall=0.90, min_precision=0.75
)
print(f"Valid: {is_valid}, Recall: {details['recall']:.3f}, Precision: {details['precision']:.3f}")
```

## Threshold Sweep Analysis

Use threshold sweeps to find optimal values:

```python
# Sweep semantic threshold
results = await framework.threshold_sweep(
    threshold_name="semantic_threshold",
    threshold_range=[0.70, 0.75, 0.80, 0.85, 0.90, 0.95],
)

# Find best F1 score
best_result = max(results, key=lambda r: r.metrics.f1_score)
print(f"Best threshold: {best_result.config.semantic_threshold}")
print(f"F1 Score: {best_result.metrics.f1_score:.3f}")
```

## Common Patterns

### Pattern 1: High Recall Needed
When you need to capture most matches (e.g., entity linking):

```python
config = FusionMatchingConfig(
    semantic_threshold=0.78,  # Lower
    string_similarity_threshold=0.75,  # Lower
)
```

### Pattern 2: High Precision Needed
When false positives are costly (e.g., deduplication):

```python
config = FusionMatchingConfig(
    semantic_threshold=0.90,  # Higher
    string_similarity_threshold=0.85,  # Higher
)
```

### Pattern 3: Balanced Performance
Default configuration (good for most use cases):

```python
config = FusionMatchingConfig()  # Uses defaults
```

## Monitoring and Validation

After deploying tuned thresholds:

1. **Monitor metrics** in production
2. **Track false positives/negatives** from user feedback
3. **Periodically re-evaluate** as data distribution changes
4. **A/B test** new threshold configurations before full rollout

## Best Practices

1. **Start with defaults** - They're optimized for general use
2. **Tune incrementally** - Make small adjustments and re-evaluate
3. **Use domain-specific configs** - Different domains have different needs
4. **Validate on your data** - Create evaluation dataset from your domain
5. **Consider per-type configs** - Person vs Organization may need different thresholds
6. **Monitor production** - Thresholds may need adjustment as data evolves

## Troubleshooting

### Issue: Too many false positives
- **Solution**: Raise `semantic_threshold` and `string_similarity_threshold`
- **Check**: Disable semantic matching for entity types where it's not needed

### Issue: Too many false negatives
- **Solution**: Lower `semantic_threshold` and `string_similarity_threshold`
- **Check**: Ensure alias index and abbreviation dictionaries are populated

### Issue: Performance degradation
- **Solution**: Use per-type configs to disable expensive stages (semantic) where not needed
- **Check**: Enable early-exit optimization (default: enabled)

## Additional Resources

- Evaluation Dataset: `aiecs.application.knowledge_graph.fusion.evaluation_dataset`
- A/B Testing Framework: `aiecs.application.knowledge_graph.fusion.ab_testing`
- Configuration API: `aiecs.application.knowledge_graph.fusion.matching_config`
