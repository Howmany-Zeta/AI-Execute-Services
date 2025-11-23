"""
Knowledge Graph Configuration

Configuration settings for knowledge graph storage and operations.
"""

from enum import Enum
from pydantic import Field


class GraphStorageBackend(str, Enum):
    """Available graph storage backends"""

    INMEMORY = "inmemory"
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"


class KnowledgeGraphConfig:
    """
    Knowledge Graph Configuration

    This class provides configuration settings for knowledge graph operations.
    It integrates with AIECS Settings through environment variables.
    """

    # Storage backend selection
    backend: GraphStorageBackend = Field(
        default=GraphStorageBackend.INMEMORY,
        description="Graph storage backend to use",
    )

    # SQLite configuration (for file-based persistence)
    sqlite_db_path: str = Field(
        default="./storage/knowledge_graph.db",
        description="Path to SQLite database file",
    )

    # In-memory configuration
    inmemory_max_nodes: int = Field(
        default=100000,
        description="Maximum number of nodes for in-memory storage",
    )

    # Vector search configuration
    vector_dimension: int = Field(
        default=1536,
        description="Dimension of embedding vectors (default for OpenAI ada-002)",
    )

    # Query configuration
    default_search_limit: int = Field(
        default=10,
        description="Default number of results to return in searches",
    )

    max_traversal_depth: int = Field(default=5, description="Maximum depth for graph traversal queries")

    # Cache configuration
    enable_query_cache: bool = Field(default=True, description="Enable caching of query results")

    cache_ttl_seconds: int = Field(
        default=300,
        description="Time-to-live for cached query results (seconds)",
    )

    # Feature flags for new capabilities
    enable_runnable_pattern: bool = Field(
        default=True,
        description="Enable Runnable pattern for composable graph operations",
    )

    enable_knowledge_fusion: bool = Field(
        default=True,
        description="Enable knowledge fusion for cross-document entity merging",
    )

    enable_reranking: bool = Field(
        default=True,
        description="Enable result reranking for improved search relevance",
    )

    enable_logical_queries: bool = Field(
        default=True,
        description="Enable logical query parsing for structured queries",
    )

    enable_structured_import: bool = Field(default=True, description="Enable structured data import (CSV/JSON)")

    # Knowledge Fusion configuration
    fusion_similarity_threshold: float = Field(
        default=0.85,
        description="Similarity threshold for entity fusion (0.0-1.0)",
    )

    fusion_conflict_resolution: str = Field(
        default="most_complete",
        description="Conflict resolution strategy: most_complete, most_recent, most_confident, longest, keep_all",
    )

    # Reranking configuration
    reranking_default_strategy: str = Field(
        default="hybrid",
        description="Default reranking strategy: text, semantic, structural, hybrid",
    )

    reranking_top_k: int = Field(default=100, description="Top-K results to fetch before reranking")

    # Schema cache configuration
    enable_schema_cache: bool = Field(
        default=True,
        description="Enable schema caching for improved performance",
    )

    schema_cache_ttl_seconds: int = Field(default=3600, description="Time-to-live for cached schemas (seconds)")

    # Query optimization configuration
    enable_query_optimization: bool = Field(
        default=True,
        description="Enable query optimization for better performance",
    )

    query_optimization_strategy: str = Field(
        default="balanced",
        description="Query optimization strategy: cost, latency, balanced",
    )


def get_graph_config() -> KnowledgeGraphConfig:
    """Get knowledge graph configuration singleton"""
    return KnowledgeGraphConfig()
