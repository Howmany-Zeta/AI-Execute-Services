"""
Knowledge Graph Configuration

Configuration settings for knowledge graph storage and operations.
"""

from enum import Enum
from pydantic import Field
from typing import Literal


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
        description="Graph storage backend to use"
    )
    
    # SQLite configuration (for file-based persistence)
    sqlite_db_path: str = Field(
        default="./storage/knowledge_graph.db",
        description="Path to SQLite database file"
    )
    
    # In-memory configuration
    inmemory_max_nodes: int = Field(
        default=100000,
        description="Maximum number of nodes for in-memory storage"
    )
    
    # Vector search configuration
    vector_dimension: int = Field(
        default=1536,
        description="Dimension of embedding vectors (default for OpenAI ada-002)"
    )
    
    # Query configuration
    default_search_limit: int = Field(
        default=10,
        description="Default number of results to return in searches"
    )
    
    max_traversal_depth: int = Field(
        default=5,
        description="Maximum depth for graph traversal queries"
    )
    
    # Cache configuration
    enable_query_cache: bool = Field(
        default=True,
        description="Enable caching of query results"
    )
    
    cache_ttl_seconds: int = Field(
        default=300,
        description="Time-to-live for cached query results (seconds)"
    )


def get_graph_config() -> KnowledgeGraphConfig:
    """Get knowledge graph configuration singleton"""
    return KnowledgeGraphConfig()

