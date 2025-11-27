from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pathlib import Path
import logging
from typing import Literal

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # LLM Provider Configuration (optional until used)
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    googleai_api_key: str = Field(default="", alias="GOOGLEAI_API_KEY")
    vertex_project_id: str = Field(default="", alias="VERTEX_PROJECT_ID")
    vertex_location: str = Field(default="us-central1", alias="VERTEX_LOCATION")
    google_application_credentials: str = Field(default="", alias="GOOGLE_APPLICATION_CREDENTIALS")
    google_api_key: str = Field(default="", alias="GOOGLE_API_KEY")
    google_cse_id: str = Field(default="", alias="GOOGLE_CSE_ID")
    xai_api_key: str = Field(default="", alias="XAI_API_KEY")
    grok_api_key: str = Field(default="", alias="GROK_API_KEY")  # Backward compatibility

    # LLM Models Configuration
    llm_models_config_path: str = Field(
        default="",
        alias="LLM_MODELS_CONFIG",
        description="Path to LLM models YAML configuration file",
    )

    # Infrastructure Configuration (with sensible defaults)
    celery_broker_url: str = Field(default="redis://localhost:6379/0", alias="CELERY_BROKER_URL")
    cors_allowed_origins: str = Field(
        default="http://localhost:3000,http://express-gateway:3001",
        alias="CORS_ALLOWED_ORIGINS",
    )

    # PostgreSQL Database Configuration (with defaults)
    db_host: str = Field(default="localhost", alias="DB_HOST")
    db_user: str = Field(default="postgres", alias="DB_USER")
    db_password: str = Field(default="", alias="DB_PASSWORD")
    db_name: str = Field(default="aiecs", alias="DB_NAME")
    db_port: int = Field(default=5432, alias="DB_PORT")
    postgres_url: str = Field(default="", alias="POSTGRES_URL")
    # Connection mode: "local" (use individual parameters) or "cloud" (use POSTGRES_URL)
    # If "cloud" is set, POSTGRES_URL will be used; otherwise individual
    # parameters are used
    db_connection_mode: str = Field(default="local", alias="DB_CONNECTION_MODE")

    # Google Cloud Storage Configuration (optional)
    google_cloud_project_id: str = Field(default="", alias="GOOGLE_CLOUD_PROJECT_ID")
    google_cloud_storage_bucket: str = Field(default="", alias="GOOGLE_CLOUD_STORAGE_BUCKET")

    # Qdrant configuration (legacy)
    qdrant_url: str = Field("http://qdrant:6333", alias="QDRANT_URL")
    qdrant_collection: str = Field("documents", alias="QDRANT_COLLECTION")

    # Vertex AI Vector Search configuration
    vertex_index_id: str | None = Field(default=None, alias="VERTEX_INDEX_ID")
    vertex_endpoint_id: str | None = Field(default=None, alias="VERTEX_ENDPOINT_ID")
    vertex_deployed_index_id: str | None = Field(default=None, alias="VERTEX_DEPLOYED_INDEX_ID")

    # Vector store backend selection (Qdrant deprecated, using Vertex AI by
    # default)
    vector_store_backend: str = Field("vertex", alias="VECTOR_STORE_BACKEND")  # "vertex" (qdrant deprecated)

    # Development/Server Configuration
    reload: bool = Field(default=False, alias="RELOAD")
    port: int = Field(default=8000, alias="PORT")

    # Knowledge Graph Configuration
    # Storage backend selection
    kg_storage_backend: Literal["inmemory", "sqlite", "postgresql"] = Field(
        default="inmemory",
        alias="KG_STORAGE_BACKEND",
        description="Knowledge graph storage backend: inmemory (default), sqlite (file-based), or postgresql (production)",
    )

    # SQLite configuration (for file-based persistence)
    kg_sqlite_db_path: str = Field(
        default="./storage/knowledge_graph.db",
        alias="KG_SQLITE_DB_PATH",
        description="Path to SQLite database file for knowledge graph storage",
    )

    # PostgreSQL configuration (uses main database config by default)
    # If you want a separate database for knowledge graph, set these:
    kg_db_host: str = Field(default="", alias="KG_DB_HOST")
    kg_db_port: int = Field(default=5432, alias="KG_DB_PORT")
    kg_db_user: str = Field(default="", alias="KG_DB_USER")
    kg_db_password: str = Field(default="", alias="KG_DB_PASSWORD")
    kg_db_name: str = Field(default="", alias="KG_DB_NAME")
    kg_postgres_url: str = Field(default="", alias="KG_POSTGRES_URL")

    # PostgreSQL connection pool settings
    kg_min_pool_size: int = Field(
        default=5,
        alias="KG_MIN_POOL_SIZE",
        description="Minimum number of connections in PostgreSQL pool",
    )
    kg_max_pool_size: int = Field(
        default=20,
        alias="KG_MAX_POOL_SIZE",
        description="Maximum number of connections in PostgreSQL pool",
    )

    # PostgreSQL pgvector support
    kg_enable_pgvector: bool = Field(
        default=False,
        alias="KG_ENABLE_PGVECTOR",
        description="Enable pgvector extension for optimized vector search (requires pgvector installed)",
    )

    # In-memory configuration
    kg_inmemory_max_nodes: int = Field(
        default=100000,
        alias="KG_INMEMORY_MAX_NODES",
        description="Maximum number of nodes for in-memory storage",
    )

    # Vector search configuration
    kg_vector_dimension: int = Field(
        default=1536,
        alias="KG_VECTOR_DIMENSION",
        description="Dimension of embedding vectors (default 1536 for OpenAI ada-002)",
    )

    # Query configuration
    kg_default_search_limit: int = Field(
        default=10,
        alias="KG_DEFAULT_SEARCH_LIMIT",
        description="Default number of results to return in searches",
    )

    kg_max_traversal_depth: int = Field(
        default=5,
        alias="KG_MAX_TRAVERSAL_DEPTH",
        description="Maximum depth for graph traversal queries",
    )

    # Cache configuration
    kg_enable_query_cache: bool = Field(
        default=True,
        alias="KG_ENABLE_QUERY_CACHE",
        description="Enable caching of query results",
    )

    kg_cache_ttl_seconds: int = Field(
        default=300,
        alias="KG_CACHE_TTL_SECONDS",
        description="Time-to-live for cached query results (seconds)",
    )

    # Entity Extraction LLM Configuration
    kg_entity_extraction_llm_provider: str = Field(
        default="",
        alias="KG_ENTITY_EXTRACTION_LLM_PROVIDER",
        description="LLM provider for entity extraction (supports custom providers registered via LLMClientFactory)",
    )

    kg_entity_extraction_llm_model: str = Field(
        default="",
        alias="KG_ENTITY_EXTRACTION_LLM_MODEL",
        description="LLM model for entity extraction",
    )

    kg_entity_extraction_temperature: float = Field(
        default=0.1,
        alias="KG_ENTITY_EXTRACTION_TEMPERATURE",
        description="Temperature for entity extraction (low for deterministic results)",
    )

    kg_entity_extraction_max_tokens: int = Field(
        default=2000,
        alias="KG_ENTITY_EXTRACTION_MAX_TOKENS",
        description="Maximum tokens for entity extraction response",
    )

    # Embedding Configuration
    kg_embedding_provider: str = Field(
        default="openai",
        alias="KG_EMBEDDING_PROVIDER",
        description="LLM provider for embeddings (supports custom providers registered via LLMClientFactory)",
    )

    kg_embedding_model: str = Field(
        default="text-embedding-ada-002",
        alias="KG_EMBEDDING_MODEL",
        description="Model for generating embeddings",
    )

    kg_embedding_dimension: int = Field(
        default=1536,
        alias="KG_EMBEDDING_DIMENSION",
        description="Dimension of embedding vectors (must match model output, e.g., 1536 for ada-002)",
    )

    # Feature flags for new capabilities
    kg_enable_runnable_pattern: bool = Field(
        default=True,
        alias="KG_ENABLE_RUNNABLE_PATTERN",
        description="Enable Runnable pattern for composable graph operations",
    )

    kg_enable_knowledge_fusion: bool = Field(
        default=True,
        alias="KG_ENABLE_KNOWLEDGE_FUSION",
        description="Enable knowledge fusion for cross-document entity merging",
    )

    kg_enable_reranking: bool = Field(
        default=True,
        alias="KG_ENABLE_RERANKING",
        description="Enable result reranking for improved search relevance",
    )

    kg_enable_logical_queries: bool = Field(
        default=True,
        alias="KG_ENABLE_LOGICAL_QUERIES",
        description="Enable logical query parsing for structured queries",
    )

    kg_enable_structured_import: bool = Field(
        default=True,
        alias="KG_ENABLE_STRUCTURED_IMPORT",
        description="Enable structured data import (CSV/JSON)",
    )

    # Knowledge Fusion configuration
    kg_fusion_similarity_threshold: float = Field(
        default=0.85,
        alias="KG_FUSION_SIMILARITY_THRESHOLD",
        description="Similarity threshold for entity fusion (0.0-1.0)",
    )

    kg_fusion_conflict_resolution: str = Field(
        default="most_complete",
        alias="KG_FUSION_CONFLICT_RESOLUTION",
        description="Conflict resolution strategy: most_complete, most_recent, most_confident, longest, keep_all",
    )

    # Reranking configuration
    kg_reranking_default_strategy: str = Field(
        default="hybrid",
        alias="KG_RERANKING_DEFAULT_STRATEGY",
        description="Default reranking strategy: text, semantic, structural, hybrid",
    )

    kg_reranking_top_k: int = Field(
        default=100,
        alias="KG_RERANKING_TOP_K",
        description="Top-K results to fetch before reranking",
    )

    # Schema cache configuration
    kg_enable_schema_cache: bool = Field(
        default=True,
        alias="KG_ENABLE_SCHEMA_CACHE",
        description="Enable schema caching for improved performance",
    )

    kg_schema_cache_ttl_seconds: int = Field(
        default=3600,
        alias="KG_SCHEMA_CACHE_TTL_SECONDS",
        description="Time-to-live for cached schemas (seconds)",
    )

    # Query optimization configuration
    kg_enable_query_optimization: bool = Field(
        default=True,
        alias="KG_ENABLE_QUERY_OPTIMIZATION",
        description="Enable query optimization for better performance",
    )

    kg_query_optimization_strategy: str = Field(
        default="balanced",
        alias="KG_QUERY_OPTIMIZATION_STRATEGY",
        description="Query optimization strategy: cost, latency, balanced",
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="allow")

    @property
    def database_config(self) -> dict:
        """
        Get database configuration for asyncpg.

        Supports both connection string (POSTGRES_URL) and individual parameters.
        The connection mode is controlled by DB_CONNECTION_MODE:
        - "cloud": Use POSTGRES_URL connection string (for cloud databases)
        - "local": Use individual parameters (for local databases)

        If DB_CONNECTION_MODE is "cloud" but POSTGRES_URL is not provided,
        falls back to individual parameters with a warning.
        """
        # Check connection mode
        if self.db_connection_mode.lower() == "cloud":
            # Use connection string for cloud databases
            if self.postgres_url:
                return {"dsn": self.postgres_url}
            else:
                logger.warning("DB_CONNECTION_MODE is set to 'cloud' but POSTGRES_URL is not provided. " "Falling back to individual parameters (local mode).")
                # Fall back to individual parameters
                return {
                    "host": self.db_host,
                    "user": self.db_user,
                    "password": self.db_password,
                    "database": self.db_name,
                    "port": self.db_port,
                }
        else:
            # Use individual parameters for local databases (default)
            return {
                "host": self.db_host,
                "user": self.db_user,
                "password": self.db_password,
                "database": self.db_name,
                "port": self.db_port,
            }

    @property
    def file_storage_config(self) -> dict:
        """Get file storage configuration for Google Cloud Storage"""
        return {
            "gcs_project_id": self.google_cloud_project_id,
            "gcs_bucket_name": self.google_cloud_storage_bucket,
            "gcs_credentials_path": self.google_application_credentials,
            "enable_local_fallback": True,
            "local_storage_path": "./storage",
        }

    @property
    def kg_database_config(self) -> dict:
        """
        Get knowledge graph database configuration.

        Returns configuration for the knowledge graph storage backend:
        - For PostgreSQL: Returns connection parameters (uses main DB config if KG-specific not set)
        - For SQLite: Returns db_path
        - For in-memory: Returns max_nodes limit
        """
        if self.kg_storage_backend == "postgresql":
            # Use KG-specific config if provided, otherwise fall back to main
            # DB config
            if self.kg_postgres_url:
                return {
                    "dsn": self.kg_postgres_url,
                    "min_pool_size": self.kg_min_pool_size,
                    "max_pool_size": self.kg_max_pool_size,
                    "enable_pgvector": self.kg_enable_pgvector,
                }
            elif self.kg_db_host:
                return {
                    "host": self.kg_db_host,
                    "port": self.kg_db_port,
                    "user": self.kg_db_user,
                    "password": self.kg_db_password,
                    "database": self.kg_db_name or "aiecs_knowledge_graph",
                    "min_pool_size": self.kg_min_pool_size,
                    "max_pool_size": self.kg_max_pool_size,
                    "enable_pgvector": self.kg_enable_pgvector,
                }
            else:
                # Fall back to main database config
                db_config = self.database_config.copy()
                db_config["min_pool_size"] = self.kg_min_pool_size
                db_config["max_pool_size"] = self.kg_max_pool_size
                db_config["enable_pgvector"] = self.kg_enable_pgvector
                return db_config
        elif self.kg_storage_backend == "sqlite":
            return {"db_path": self.kg_sqlite_db_path}
        else:  # inmemory
            return {"max_nodes": self.kg_inmemory_max_nodes}

    @property
    def kg_query_config(self) -> dict:
        """Get knowledge graph query configuration"""
        return {
            "default_search_limit": self.kg_default_search_limit,
            "max_traversal_depth": self.kg_max_traversal_depth,
            "vector_dimension": self.kg_vector_dimension,
        }

    @property
    def kg_cache_config(self) -> dict:
        """Get knowledge graph cache configuration"""
        return {
            "enable_query_cache": self.kg_enable_query_cache,
            "cache_ttl_seconds": self.kg_cache_ttl_seconds,
        }

    @field_validator("kg_storage_backend")
    @classmethod
    def validate_kg_storage_backend(cls, v: str) -> str:
        """Validate knowledge graph storage backend selection"""
        valid_backends = ["inmemory", "sqlite", "postgresql"]
        if v not in valid_backends:
            raise ValueError(f"Invalid KG_STORAGE_BACKEND: {v}. " f"Must be one of: {', '.join(valid_backends)}")
        return v

    @field_validator("kg_sqlite_db_path")
    @classmethod
    def validate_kg_sqlite_path(cls, v: str) -> str:
        """Validate and create parent directory for SQLite database"""
        if v and v != ":memory:":
            path = Path(v)
            # Create parent directory if it doesn't exist
            path.parent.mkdir(parents=True, exist_ok=True)
        return v

    @field_validator("kg_max_traversal_depth")
    @classmethod
    def validate_kg_max_traversal_depth(cls, v: int) -> int:
        """Validate maximum traversal depth"""
        if v < 1:
            raise ValueError("KG_MAX_TRAVERSAL_DEPTH must be at least 1")
        if v > 10:
            logger.warning(f"KG_MAX_TRAVERSAL_DEPTH is set to {v}, which may cause performance issues. " "Consider using a value <= 10 for production use.")
        return v

    @field_validator("kg_vector_dimension")
    @classmethod
    def validate_kg_vector_dimension(cls, v: int) -> int:
        """Validate vector dimension"""
        if v < 1:
            raise ValueError("KG_VECTOR_DIMENSION must be at least 1")
        # Common dimensions: 128, 256, 384, 512, 768, 1024, 1536, 3072
        common_dims = [128, 256, 384, 512, 768, 1024, 1536, 3072]
        if v not in common_dims:
            logger.warning(f"KG_VECTOR_DIMENSION is set to {v}, which is not a common embedding dimension. " f"Common dimensions are: {common_dims}")
        return v

    def validate_llm_models_config(self) -> bool:
        """
        Validate that LLM models configuration file exists.

        Returns:
            True if config file exists or can be found in default locations

        Raises:
            FileNotFoundError: If config file doesn't exist
        """
        if self.llm_models_config_path:
            config_path = Path(self.llm_models_config_path)
            if not config_path.exists():
                raise FileNotFoundError(f"LLM models config file not found: {config_path}")
            return True

        # Check default locations
        current_dir = Path(__file__).parent
        default_path = current_dir / "llm_models.yaml"

        if default_path.exists():
            return True

        # If not found, it's still okay - the config loader will try to find it
        return True


@lru_cache()
def get_settings():
    return Settings()


def validate_required_settings(operation_type: str = "full") -> bool:
    """
    Validate that required settings are present for specific operations

    Args:
        operation_type: Type of operation to validate for
            - "basic": Only basic package functionality
            - "llm": LLM provider functionality
            - "database": Database operations
            - "storage": Cloud storage operations
            - "knowledge_graph": Knowledge graph operations
            - "full": All functionality

    Returns:
        True if settings are valid, False otherwise

    Raises:
        ValueError: If required settings are missing for the operation type
    """
    settings = get_settings()
    missing = []

    if operation_type in ["llm", "full"]:
        # At least one LLM provider should be configured
        llm_configs = [
            ("OpenAI", settings.openai_api_key),
            (
                "Vertex AI",
                settings.vertex_project_id and settings.google_application_credentials,
            ),
            ("xAI", settings.xai_api_key),
        ]

        if not any(config[1] for config in llm_configs):
            missing.append("At least one LLM provider (OpenAI, Vertex AI, or xAI)")

    if operation_type in ["database", "full"]:
        if not settings.db_password:
            missing.append("DB_PASSWORD")

    if operation_type in ["storage", "full"]:
        if settings.google_cloud_project_id and not settings.google_cloud_storage_bucket:
            missing.append("GOOGLE_CLOUD_STORAGE_BUCKET (required when GOOGLE_CLOUD_PROJECT_ID is set)")

    if operation_type in ["knowledge_graph", "full"]:
        # Validate knowledge graph configuration
        if settings.kg_storage_backend == "postgresql":
            # Check if KG-specific or main DB config is available
            if not (settings.kg_postgres_url or settings.kg_db_host or settings.db_password):
                missing.append("Knowledge graph PostgreSQL configuration: " "Either set KG_POSTGRES_URL, KG_DB_* parameters, or main DB_PASSWORD")
        elif settings.kg_storage_backend == "sqlite":
            if not settings.kg_sqlite_db_path:
                missing.append("KG_SQLITE_DB_PATH (required for SQLite backend)")

    if missing:
        raise ValueError(f"Missing required settings for {operation_type} operation: {', '.join(missing)}\n" "Please check your .env file or environment variables.")

    return True
