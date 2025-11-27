"""
Retrieval Strategy Types

Defines the types of retrieval strategies available for knowledge graph queries.
"""

from enum import Enum


class RetrievalStrategy(str, Enum):
    """
    Retrieval strategy enumeration for knowledge graph queries.

    Defines different strategies for retrieving relevant knowledge from the graph
    based on query intent and characteristics.
    """

    VECTOR_SEARCH = "vector_search"  # Semantic similarity search using embeddings
    MULTI_HOP = "multi_hop"  # Multi-hop neighbor traversal
    PAGERANK = "pagerank"  # Personalized PageRank retrieval
    FILTERED = "filtered"  # Property-based filtering
    HYBRID = "hybrid"  # Combination of multiple strategies

