"""
Knowledge Graph Search Application Layer

Advanced search strategies including hybrid search and text similarity utilities.
"""

from aiecs.application.knowledge_graph.search.hybrid_search import (
    HybridSearchStrategy,
    HybridSearchConfig,
    SearchMode,
)
from aiecs.application.knowledge_graph.search.text_similarity import (
    TextSimilarity,
    BM25Scorer,
    jaccard_similarity,
    jaccard_similarity_text,
    cosine_similarity_text,
    levenshtein_distance,
    normalized_levenshtein_similarity,
    fuzzy_match,
)
from aiecs.application.knowledge_graph.search.reranker import (
    RerankerStrategy,
    ResultReranker,
    ScoreCombinationMethod,
    normalize_scores,
    combine_scores,
)
from aiecs.application.knowledge_graph.search.reranker_strategies import (
    TextSimilarityReranker,
    SemanticReranker,
    StructuralReranker,
    HybridReranker,
    CrossEncoderReranker,
)

__all__ = [
    "HybridSearchStrategy",
    "HybridSearchConfig",
    "SearchMode",
    "TextSimilarity",
    "BM25Scorer",
    "jaccard_similarity",
    "jaccard_similarity_text",
    "cosine_similarity_text",
    "levenshtein_distance",
    "normalized_levenshtein_similarity",
    "fuzzy_match",
    "RerankerStrategy",
    "ResultReranker",
    "ScoreCombinationMethod",
    "normalize_scores",
    "combine_scores",
    "TextSimilarityReranker",
    "SemanticReranker",
    "StructuralReranker",
    "HybridReranker",
    "CrossEncoderReranker",
]
