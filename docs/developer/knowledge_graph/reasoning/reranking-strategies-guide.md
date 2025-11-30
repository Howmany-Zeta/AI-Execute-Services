# Reranking Strategies Guide

**Version**: 1.0  
**Date**: 2025-11-14  
**Module**: `aiecs.application.knowledge_graph.search.reranker_strategies`

## Overview

This guide covers the built-in reranking strategies available in the knowledge graph search system. Each strategy uses different signals to score entity relevance, and they can be combined for optimal results.

## Built-in Strategies

### 1. TextSimilarityReranker

Scores entities based on text similarity using BM25 and Jaccard similarity.

```python
from aiecs.application.knowledge_graph.search.reranker_strategies import TextSimilarityReranker
```

#### How It Works

- **BM25**: Term-based relevance scoring (TF-IDF variant)
- **Jaccard**: Set overlap between query and entity text
- **Combination**: Weighted combination of both scores

#### Constructor

```python
def __init__(
    self,
    bm25_weight: float = 0.7,
    jaccard_weight: float = 0.3,
    text_fields: Optional[List[str]] = None
)
```

**Parameters**:
- `bm25_weight` (float): Weight for BM25 score (default: 0.7)
- `jaccard_weight` (float): Weight for Jaccard score (default: 0.3)
- `text_fields` (Optional[List[str]]): Entity fields to use for text (default: ["name", "description"])

#### Example

```python
# Create text similarity reranker
text_reranker = TextSimilarityReranker(
    bm25_weight=0.7,
    jaccard_weight=0.3,
    text_fields=["name", "description", "content"]
)

# Score entities
scores = await text_reranker.score(
    query="machine learning algorithms",
    entities=search_results
)
```

#### When to Use

- ✅ Query contains specific keywords
- ✅ Exact term matching is important
- ✅ Entity text is rich and descriptive
- ❌ Query is very short or generic
- ❌ Semantic meaning is more important than keywords

#### Performance

- **Speed**: Fast (no external calls)
- **Memory**: Low
- **Accuracy**: Good for keyword-based queries

---

### 2. SemanticReranker

Scores entities based on semantic similarity using vector embeddings.

```python
from aiecs.application.knowledge_graph.search.reranker_strategies import SemanticReranker
```

#### How It Works

- **Embeddings**: Uses entity embedding vectors
- **Similarity**: Computes cosine similarity with query embedding
- **Fallback**: Returns 0.5 if embeddings are missing

#### Constructor

```python
def __init__(self)
```

No parameters required.

#### Example

```python
# Create semantic reranker
semantic_reranker = SemanticReranker()

# Score entities (requires query_embedding)
scores = await semantic_reranker.score(
    query="machine learning",
    entities=search_results,
    query_embedding=[0.1, 0.2, 0.3, ...]  # Query vector
)
```

#### When to Use

- ✅ Semantic meaning is important
- ✅ Query and entities have embeddings
- ✅ Handling synonyms and related concepts
- ✅ Cross-lingual search
- ❌ Embeddings are not available
- ❌ Exact keyword matching is critical

#### Performance

- **Speed**: Fast (vector operations)
- **Memory**: Medium (stores embeddings)
- **Accuracy**: Excellent for semantic queries

---

### 3. StructuralReranker

Scores entities based on graph structure (PageRank, centrality).

```python
from aiecs.application.knowledge_graph.search.reranker_strategies import StructuralReranker
```

#### How It Works

- **PageRank**: Scores based on entity importance in graph
- **Degree Centrality**: Scores based on number of connections
- **Combination**: Weighted combination of both metrics

#### Constructor

```python
def __init__(
    self,
    graph_store: GraphStore,
    pagerank_weight: float = 0.7,
    centrality_weight: float = 0.3,
    use_cache: bool = True
)
```

**Parameters**:
- `graph_store` (GraphStore): Graph storage backend
- `pagerank_weight` (float): Weight for PageRank score (default: 0.7)
- `centrality_weight` (float): Weight for centrality score (default: 0.3)
- `use_cache` (bool): Whether to cache PageRank scores (default: True)

#### Example

```python
# Create structural reranker
structural_reranker = StructuralReranker(
    graph_store=store,
    pagerank_weight=0.7,
    centrality_weight=0.3
)

# Score entities
scores = await structural_reranker.score(
    query="important entities",
    entities=search_results
)
```

#### When to Use

- ✅ Entity importance matters
- ✅ Well-connected entities are more relevant
- ✅ Graph structure is meaningful
- ❌ All entities are equally important
- ❌ Graph is sparse or disconnected

#### Performance

- **Speed**: Medium (requires graph queries)
- **Memory**: Medium (caches PageRank)
- **Accuracy**: Good for authority-based ranking

---

### 4. HybridReranker

Combines text, semantic, and structural signals into a single strategy.

```python
from aiecs.application.knowledge_graph.search.reranker_strategies import HybridReranker
```

#### How It Works

- **Multi-Signal**: Combines all three reranking approaches
- **Weighted**: Configurable weights for each signal
- **Normalized**: Normalizes scores before combining

#### Constructor

```python
def __init__(
    self,
    graph_store: GraphStore,
    text_weight: float = 0.4,
    semantic_weight: float = 0.4,
    structural_weight: float = 0.2,
    text_fields: Optional[List[str]] = None
)
```

**Parameters**:
- `graph_store` (GraphStore): Graph storage backend
- `text_weight` (float): Weight for text similarity (default: 0.4)
- `semantic_weight` (float): Weight for semantic similarity (default: 0.4)
- `structural_weight` (float): Weight for structural importance (default: 0.2)
- `text_fields` (Optional[List[str]]): Entity fields for text similarity

#### Example

```python
# Create hybrid reranker
hybrid_reranker = HybridReranker(
    graph_store=store,
    text_weight=0.4,
    semantic_weight=0.4,
    structural_weight=0.2
)

# Score entities
scores = await hybrid_reranker.score(
    query="machine learning",
    entities=search_results,
    query_embedding=[0.1, 0.2, ...]
)
```

#### When to Use

- ✅ Want comprehensive ranking
- ✅ Multiple signals are available
- ✅ Balanced approach is needed
- ❌ Only one signal is available
- ❌ Need fine-grained control over strategies

#### Performance

- **Speed**: Medium (combines all strategies)
- **Memory**: Medium
- **Accuracy**: Excellent for general-purpose ranking

---

## Strategy Comparison

| Strategy | Speed | Memory | Best For | Requires |
|----------|-------|--------|----------|----------|
| TextSimilarity | Fast | Low | Keyword queries | Entity text |
| Semantic | Fast | Medium | Semantic queries | Embeddings |
| Structural | Medium | Medium | Authority ranking | Graph structure |
| Hybrid | Medium | Medium | General purpose | All of above |

---

## Combining Strategies

### Using ResultReranker

Combine multiple strategies with custom weights:

```python
from aiecs.application.knowledge_graph.search.reranker import (
    ResultReranker,
    ScoreCombinationMethod
)

# Create individual strategies
text_reranker = TextSimilarityReranker()
semantic_reranker = SemanticReranker()
structural_reranker = StructuralReranker(graph_store)

# Combine with weighted average
reranker = ResultReranker(
    strategies=[text_reranker, semantic_reranker, structural_reranker],
    combination_method=ScoreCombinationMethod.WEIGHTED_AVERAGE,
    weights={
        "text": 0.4,
        "semantic": 0.4,
        "structural": 0.2
    }
)
```

### Combination Methods

#### 1. Weighted Average (Recommended)

Combines scores using weighted average:

```python
combination_method=ScoreCombinationMethod.WEIGHTED_AVERAGE
weights={"text": 0.6, "semantic": 0.4}
```

**When to use**: Most cases, allows fine-tuning importance

#### 2. Reciprocal Rank Fusion (RRF)

Combines based on ranks rather than scores:

```python
combination_method=ScoreCombinationMethod.RRF
```

**When to use**: Scores are on different scales, want rank-based fusion

#### 3. Max Score

Takes maximum score across strategies:

```python
combination_method=ScoreCombinationMethod.MAX
```

**When to use**: Want entities that excel in any strategy

#### 4. Min Score

Takes minimum score across strategies:

```python
combination_method=ScoreCombinationMethod.MIN
```

**When to use**: Want entities that score well in all strategies

---

## Best Practices

### 1. Choose the Right Strategy

```python
# For keyword-heavy queries
if query_has_specific_terms:
    use TextSimilarityReranker

# For semantic/conceptual queries
if query_is_conceptual:
    use SemanticReranker

# For authority-based ranking
if importance_matters:
    use StructuralReranker

# For general purpose
else:
    use HybridReranker
```

### 2. Tune Weights

Start with default weights and adjust based on results:

```python
# Default balanced weights
weights = {"text": 0.4, "semantic": 0.4, "structural": 0.2}

# Keyword-focused
weights = {"text": 0.7, "semantic": 0.2, "structural": 0.1}

# Semantic-focused
weights = {"text": 0.2, "semantic": 0.7, "structural": 0.1}

# Authority-focused
weights = {"text": 0.3, "semantic": 0.3, "structural": 0.4}
```

### 3. Normalize Scores

Always normalize scores when combining strategies:

```python
reranker = ResultReranker(
    strategies=[...],
    normalize_scores=True,  # Important!
    normalization_method="min_max"
)
```

### 4. Use Top-K Limiting

Limit results for better performance:

```python
reranked = await reranker.rerank(
    query=query,
    entities=entities,
    top_k=20  # Only return top 20
)
```

### 5. Cache When Possible

Enable caching for structural reranker:

```python
structural_reranker = StructuralReranker(
    graph_store=store,
    use_cache=True  # Cache PageRank scores
)
```

---

## Custom Strategies

### Creating a Custom Strategy

Implement the `RerankerStrategy` interface:

```python
from aiecs.application.knowledge_graph.search.reranker import RerankerStrategy
from typing import List
from aiecs.domain.knowledge_graph.models.entity import Entity

class RecencyReranker(RerankerStrategy):
    """Rerank based on entity recency"""

    @property
    def name(self) -> str:
        return "recency"

    async def score(
        self,
        query: str,
        entities: List[Entity],
        **kwargs
    ) -> List[float]:
        """Score based on creation/update time"""
        scores = []
        for entity in entities:
            # Get timestamp from entity metadata
            timestamp = entity.metadata.get("updated_at", 0)
            # Normalize to [0, 1] based on age
            age_days = (time.time() - timestamp) / 86400
            score = 1.0 / (1.0 + age_days / 365)  # Decay over year
            scores.append(score)
        return scores
```

### Using Custom Strategy

```python
# Create custom strategy
recency_reranker = RecencyReranker()

# Use with ResultReranker
reranker = ResultReranker(
    strategies=[text_reranker, recency_reranker],
    weights={"text": 0.7, "recency": 0.3}
)
```

---

## Use Cases

### Use Case 1: Academic Paper Search

**Goal**: Find relevant papers with high citation count

**Strategy**:
```python
# Combine semantic similarity with structural importance
reranker = ResultReranker(
    strategies=[
        SemanticReranker(),
        StructuralReranker(graph_store)  # Citations = high PageRank
    ],
    weights={
        "semantic": 0.6,
        "structural": 0.4  # Emphasize citations
    }
)
```

### Use Case 2: Product Search

**Goal**: Find products matching keywords with good reviews

**Strategy**:
```python
# Combine text matching with custom review score
class ReviewReranker(RerankerStrategy):
    @property
    def name(self) -> str:
        return "reviews"

    async def score(self, query, entities, **kwargs):
        return [
            entity.metadata.get("review_score", 0.5) / 5.0
            for entity in entities
        ]

reranker = ResultReranker(
    strategies=[
        TextSimilarityReranker(),
        ReviewReranker()
    ],
    weights={"text": 0.7, "reviews": 0.3}
)
```

### Use Case 3: Expert Finding

**Goal**: Find experts in a domain

**Strategy**:
```python
# Emphasize structural importance (connections, collaborations)
reranker = ResultReranker(
    strategies=[
        SemanticReranker(),
        StructuralReranker(graph_store)
    ],
    weights={
        "semantic": 0.3,
        "structural": 0.7  # Emphasize network position
    }
)
```

### Use Case 4: News Article Search

**Goal**: Find relevant recent articles

**Strategy**:
```python
# Combine relevance with recency
reranker = ResultReranker(
    strategies=[
        TextSimilarityReranker(),
        SemanticReranker(),
        RecencyReranker()
    ],
    weights={
        "text": 0.4,
        "semantic": 0.3,
        "recency": 0.3  # Boost recent articles
    }
)
```

---

## Performance Optimization

### 1. Batch Processing

Process multiple queries efficiently:

```python
async def rerank_batch(queries, entities_list):
    """Rerank multiple query-entity pairs"""
    tasks = [
        reranker.rerank(query, entities)
        for query, entities in zip(queries, entities_list)
    ]
    return await asyncio.gather(*tasks)
```

### 2. Caching

Cache expensive computations:

```python
from functools import lru_cache

class CachedStructuralReranker(StructuralReranker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pagerank_cache = {}

    async def _get_pagerank_scores(self, entity_ids):
        # Check cache first
        cache_key = tuple(sorted(entity_ids))
        if cache_key in self._pagerank_cache:
            return self._pagerank_cache[cache_key]

        # Compute and cache
        scores = await super()._get_pagerank_scores(entity_ids)
        self._pagerank_cache[cache_key] = scores
        return scores
```

### 3. Parallel Strategy Execution

Execute strategies in parallel:

```python
import asyncio

async def parallel_rerank(query, entities):
    """Execute all strategies in parallel"""
    # Get scores from all strategies concurrently
    score_tasks = [
        strategy.score(query, entities)
        for strategy in reranker.strategies
    ]
    all_scores = await asyncio.gather(*score_tasks)

    # Combine scores
    # ... (combination logic)
```

### 4. Early Stopping

Stop processing if top results are clear:

```python
async def rerank_with_early_stop(
    query,
    entities,
    confidence_threshold=0.9
):
    """Stop if top result has high confidence"""
    reranked = await reranker.rerank(query, entities)

    if reranked and reranked[0][1] > confidence_threshold:
        # Top result is very confident, return early
        return reranked[:10]

    return reranked
```

---

## Troubleshooting

### Problem: Low Scores for All Entities

**Cause**: Normalization issue or missing data

**Solution**:
```python
# Check raw scores before normalization
reranker = ResultReranker(
    strategies=[...],
    normalize_scores=False  # Disable to debug
)

# Or use different normalization
reranker = ResultReranker(
    strategies=[...],
    normalization_method="softmax"  # Try different method
)
```

### Problem: One Strategy Dominates

**Cause**: Scores on different scales

**Solution**:
```python
# Always normalize scores
reranker = ResultReranker(
    strategies=[...],
    normalize_scores=True,  # Enable normalization
    normalization_method="min_max"
)

# Or adjust weights
weights = {
    "dominant_strategy": 0.3,  # Reduce weight
    "other_strategy": 0.7      # Increase weight
}
```

### Problem: Slow Performance

**Cause**: Expensive strategy computations

**Solution**:
```python
# Use caching
structural_reranker = StructuralReranker(
    graph_store=store,
    use_cache=True
)

# Limit results early
reranked = await reranker.rerank(
    query=query,
    entities=entities[:100],  # Limit input size
    top_k=20
)

# Use faster strategies
# Replace SemanticReranker with TextSimilarityReranker if embeddings are slow
```

### Problem: Missing Embeddings

**Cause**: Entities don't have embedding vectors

**Solution**:
```python
# Provide fallback score
class SafeSemanticReranker(SemanticReranker):
    async def score(self, query, entities, **kwargs):
        scores = []
        for entity in entities:
            if entity.embedding:
                score = compute_similarity(query_emb, entity.embedding)
            else:
                score = 0.5  # Neutral score for missing embeddings
            scores.append(score)
        return scores
```

---

## Testing Strategies

### Unit Testing

```python
import pytest

@pytest.mark.asyncio
async def test_text_similarity_reranker():
    """Test text similarity reranker"""
    reranker = TextSimilarityReranker()

    # Create test entities
    entities = [
        Entity(id="1", name="Machine Learning", description="ML algorithms"),
        Entity(id="2", name="Deep Learning", description="Neural networks"),
        Entity(id="3", name="Cooking", description="Recipes and food")
    ]

    # Score entities
    scores = await reranker.score("machine learning", entities)

    # Verify scores
    assert len(scores) == 3
    assert scores[0] > scores[2]  # ML more relevant than cooking
    assert all(0 <= s <= 1 for s in scores)  # Scores in valid range
```

### Integration Testing

```python
@pytest.mark.asyncio
async def test_result_reranker_integration():
    """Test full reranker pipeline"""
    reranker = ResultReranker(
        strategies=[
            TextSimilarityReranker(),
            SemanticReranker()
        ],
        weights={"text": 0.6, "semantic": 0.4}
    )

    # Rerank entities
    reranked = await reranker.rerank(
        query="machine learning",
        entities=test_entities,
        top_k=10
    )

    # Verify results
    assert len(reranked) <= 10
    assert all(isinstance(item, tuple) for item in reranked)
    assert all(0 <= score <= 1 for _, score in reranked)
    # Verify sorted descending
    scores = [score for _, score in reranked]
    assert scores == sorted(scores, reverse=True)
```

---

## Conclusion

The reranking framework provides flexible, composable strategies for improving search result relevance. Key takeaways:

- ✅ **Choose the right strategy** for your use case
- ✅ **Combine strategies** for better results
- ✅ **Tune weights** based on your data
- ✅ **Normalize scores** when combining
- ✅ **Cache expensive computations**
- ✅ **Test thoroughly** before production

For more information, see the [ResultReranker API Documentation](result-reranker-api.md).
