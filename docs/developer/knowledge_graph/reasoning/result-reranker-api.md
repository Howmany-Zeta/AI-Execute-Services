# ResultReranker API Documentation

**Version**: 1.0  
**Date**: 2025-11-14  
**Module**: `aiecs.application.knowledge_graph.search.reranker`

## Overview

The ResultReranker framework provides a pluggable system for improving search result relevance through multiple reranking strategies. It allows combining different scoring methods (text similarity, semantic similarity, structural importance) to produce better-ranked search results.

## Core Classes

### ResultReranker

Main orchestrator class that combines multiple reranking strategies.

```python
from aiecs.application.knowledge_graph.search.reranker import (
    ResultReranker,
    ScoreCombinationMethod
)
```

#### Constructor

```python
def __init__(
    self,
    strategies: List[RerankerStrategy],
    combination_method: ScoreCombinationMethod = ScoreCombinationMethod.WEIGHTED_AVERAGE,
    weights: Optional[Dict[str, float]] = None,
    normalize_scores: bool = True,
    normalization_method: str = "min_max"
)
```

**Parameters**:
- `strategies` (List[RerankerStrategy]): List of reranking strategies to use
- `combination_method` (ScoreCombinationMethod): Method for combining scores from multiple strategies
  - `WEIGHTED_AVERAGE`: Weighted average of scores (default)
  - `RRF`: Reciprocal Rank Fusion
  - `MAX`: Maximum score across strategies
  - `MIN`: Minimum score across strategies
- `weights` (Optional[Dict[str, float]]): Strategy weights for weighted average (e.g., `{"text": 0.6, "semantic": 0.4}`)
- `normalize_scores` (bool): Whether to normalize scores to [0.0, 1.0] before combining (default: True)
- `normalization_method` (str): Normalization method - "min_max", "z_score", or "softmax" (default: "min_max")

**Example**:
```python
from aiecs.application.knowledge_graph.search.reranker_strategies import (
    TextSimilarityReranker,
    SemanticReranker
)

# Create strategies
text_reranker = TextSimilarityReranker()
semantic_reranker = SemanticReranker()

# Create reranker with weighted average
reranker = ResultReranker(
    strategies=[text_reranker, semantic_reranker],
    combination_method=ScoreCombinationMethod.WEIGHTED_AVERAGE,
    weights={"text": 0.6, "semantic": 0.4}
)
```

#### Methods

##### rerank()

Rerank entities using all configured strategies.

```python
async def rerank(
    self,
    query: str,
    entities: List[Entity],
    top_k: Optional[int] = None,
    **kwargs
) -> List[Tuple[Entity, float]]
```

**Parameters**:
- `query` (str): Query text or context
- `entities` (List[Entity]): List of entities to rerank
- `top_k` (Optional[int]): Optional limit on number of results to return
- `**kwargs`: Additional parameters passed to strategies (e.g., `query_embedding`)

**Returns**:
- `List[Tuple[Entity, float]]`: List of (entity, combined_score) tuples, sorted by score descending

**Example**:
```python
# Rerank search results
reranked = await reranker.rerank(
    query="machine learning",
    entities=search_results,
    top_k=10
)

# Access results
for entity, score in reranked:
    print(f"{entity.name}: {score:.3f}")
```

---

### RerankerStrategy (Abstract Base Class)

Base class for implementing custom reranking strategies.

```python
from aiecs.application.knowledge_graph.search.reranker import RerankerStrategy
```

#### Abstract Methods

##### name

Strategy name for identification.

```python
@property
@abstractmethod
def name(self) -> str:
    pass
```

##### score()

Compute relevance scores for entities.

```python
@abstractmethod
async def score(
    self,
    query: str,
    entities: List[Entity],
    **kwargs
) -> List[float]
```

**Parameters**:
- `query` (str): Query text or context
- `entities` (List[Entity]): List of entities to score
- `**kwargs`: Strategy-specific parameters

**Returns**:
- `List[float]`: List of scores (one per entity), same order as entities. Scores should be in range [0.0, 1.0] for best results.

**Example Implementation**:
```python
class CustomReranker(RerankerStrategy):
    @property
    def name(self) -> str:
        return "custom"
    
    async def score(
        self,
        query: str,
        entities: List[Entity],
        **kwargs
    ) -> List[float]:
        # Compute custom scores
        scores = []
        for entity in entities:
            score = compute_custom_score(query, entity)
            scores.append(score)
        return scores
```

---

### ScoreCombinationMethod (Enum)

Methods for combining scores from multiple strategies.

```python
from aiecs.application.knowledge_graph.search.reranker import ScoreCombinationMethod
```

**Values**:
- `WEIGHTED_AVERAGE`: Weighted average of scores (requires weights)
- `RRF`: Reciprocal Rank Fusion (rank-based combination)
- `MAX`: Maximum score across all strategies
- `MIN`: Minimum score across all strategies

**Example**:
```python
# Use RRF for combining strategies
reranker = ResultReranker(
    strategies=[strategy1, strategy2],
    combination_method=ScoreCombinationMethod.RRF
)
```

---

## Utility Functions

### normalize_scores()

Normalize scores to [0.0, 1.0] range.

```python
def normalize_scores(
    scores: List[float],
    method: str = "min_max"
) -> List[float]
```

**Parameters**:
- `scores` (List[float]): Raw scores to normalize
- `method` (str): Normalization method
  - `"min_max"`: Linear scaling to [0, 1]
  - `"z_score"`: Z-score normalization with sigmoid
  - `"softmax"`: Softmax normalization

**Returns**:
- `List[float]`: Normalized scores in [0.0, 1.0] range

**Example**:
```python
from aiecs.application.knowledge_graph.search.reranker import normalize_scores

raw_scores = [10, 25, 15, 30, 20]
normalized = normalize_scores(raw_scores, method="min_max")
# Result: [0.0, 0.75, 0.25, 1.0, 0.5]
```

### combine_scores()

Combine scores from multiple strategies.

```python
def combine_scores(
    score_dicts: List[Dict[str, float]],
    method: ScoreCombinationMethod = ScoreCombinationMethod.WEIGHTED_AVERAGE,
    weights: Optional[Dict[str, float]] = None
) -> Dict[str, float]
```

**Parameters**:
- `score_dicts` (List[Dict[str, float]]): List of {entity_id: score} dictionaries from each strategy
- `method` (ScoreCombinationMethod): Combination method
- `weights` (Optional[Dict[str, float]]): Optional weights for strategies

**Returns**:
- `Dict[str, float]`: Combined scores as {entity_id: combined_score}

**Example**:
```python
from aiecs.application.knowledge_graph.search.reranker import (
    combine_scores,
    ScoreCombinationMethod
)

# Scores from two strategies
strategy1_scores = {"entity1": 0.8, "entity2": 0.6}
strategy2_scores = {"entity1": 0.7, "entity2": 0.9}

# Combine with weighted average
combined = combine_scores(
    [strategy1_scores, strategy2_scores],
    method=ScoreCombinationMethod.WEIGHTED_AVERAGE,
    weights={"strategy_0": 0.6, "strategy_1": 0.4}
)
# Result: {"entity1": 0.76, "entity2": 0.72}
```

---

## Complete Example

```python
from aiecs.application.knowledge_graph.search.reranker import (
    ResultReranker,
    ScoreCombinationMethod
)
from aiecs.application.knowledge_graph.search.reranker_strategies import (
    TextSimilarityReranker,
    SemanticReranker,
    StructuralReranker
)

# Create reranking strategies
text_reranker = TextSimilarityReranker(
    bm25_weight=0.7,
    jaccard_weight=0.3
)
semantic_reranker = SemanticReranker()
structural_reranker = StructuralReranker(graph_store)

# Create result reranker
reranker = ResultReranker(
    strategies=[text_reranker, semantic_reranker, structural_reranker],
    combination_method=ScoreCombinationMethod.WEIGHTED_AVERAGE,
    weights={
        "text": 0.4,
        "semantic": 0.4,
        "structural": 0.2
    },
    normalize_scores=True,
    normalization_method="min_max"
)

# Rerank search results
reranked = await reranker.rerank(
    query="machine learning papers",
    entities=search_results,
    top_k=20,
    query_embedding=query_vector
)

# Process results
for entity, score in reranked:
    print(f"{entity.name}: {score:.3f}")
```

---

## Type Hints

All public APIs include type hints for better IDE support:

```python
from typing import List, Dict, Optional, Tuple
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.application.knowledge_graph.search.reranker import (
    ResultReranker,
    RerankerStrategy,
    ScoreCombinationMethod
)

reranker: ResultReranker = ResultReranker(strategies=[...])
results: List[Tuple[Entity, float]] = await reranker.rerank(query, entities)
```

---

## Thread Safety

The ResultReranker is **thread-safe** for concurrent use:
- Each `rerank()` call is independent
- No shared mutable state between requests
- Safe for use in async/concurrent applications

```python
import asyncio

# Safe to use concurrently
async def rerank_multiple_queries():
    tasks = [
        reranker.rerank(query1, entities1),
        reranker.rerank(query2, entities2),
        reranker.rerank(query3, entities3)
    ]
    results = await asyncio.gather(*tasks)
    return results
```
