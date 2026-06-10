# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Configuration Module for AIECS

Centralized configuration via Pydantic settings (environment variables or .env).

Optional L2 knowledge graph (private package, ADR-003):
    KG_ENABLED: Use NoOpGraphStore when false (default).
    KG_BACKEND_MODULE: importlib module for create_graph_store(settings) when enabled.

Optional L1 temporal memory (Graphiti optional extra):
    TM_ENABLED / TM_BACKEND / TM_* — see TEMPORAL_KG_MEMORY_L1_TASKS §0.7.
"""

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pathlib import Path
import logging
from typing import Any, Literal, Self

_TM_BACKENDS = frozenset({"none", "graphiti", "postgres"})
_TM_GRAPH_BACKENDS = frozenset({"falkordb", "neo4j"})

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # LLM Provider Configuration (optional until used)
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    googleai_api_key: str = Field(default="", alias="GOOGLEAI_API_KEY")
    vertex_project_id: str = Field(default="", alias="VERTEX_PROJECT_ID")
    vertex_location: str = Field(default="us-central1", alias="VERTEX_LOCATION")
    vertex_project_id_anthropic: str = Field(default="", alias="VERTEX_PROJECT_ID_ANTHROPIC")
    vertex_location_anthropic: str = Field(default="", alias="VERTEX_LOCATION_ANTHROPIC")
    vertex_project_id_maas: str = Field(default="", alias="VERTEX_PROJECT_ID_MAAS")
    vertex_location_maas: str = Field(default="", alias="VERTEX_LOCATION_MAAS")
    google_application_credentials: str = Field(default="", alias="GOOGLE_APPLICATION_CREDENTIALS")
    # Per-Vertex-client service account JSON (optional; fall back to GOOGLE_APPLICATION_CREDENTIALS)
    google_application_credentials_vertex_gemini: str = Field(
        default="",
        alias="GOOGLE_APPLICATION_CREDENTIALS_VERTEX_GEMINI",
    )
    google_application_credentials_vertex_anthropic: str = Field(
        default="",
        alias="GOOGLE_APPLICATION_CREDENTIALS_VERTEX_ANTHROPIC",
    )
    google_application_credentials_vertex_maas: str = Field(
        default="",
        alias="GOOGLE_APPLICATION_CREDENTIALS_VERTEX_MAAS",
    )
    google_api_key: str = Field(default="", alias="GOOGLE_API_KEY")
    google_cse_id: str = Field(default="", alias="GOOGLE_CSE_ID")
    xai_api_key: str = Field(default="", alias="XAI_API_KEY")
    grok_api_key: str = Field(default="", alias="GROK_API_KEY")  # Backward compatibility
    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")
    openrouter_http_referer: str = Field(default="", alias="OPENROUTER_HTTP_REFERER")
    openrouter_x_title: str = Field(default="", alias="OPENROUTER_X_TITLE")

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
    qdrant_url: str = Field(default="http://qdrant:6333", alias="QDRANT_URL")
    qdrant_collection: str = Field(default="documents", alias="QDRANT_COLLECTION")

    # Vertex AI Vector Search configuration
    vertex_index_id: str | None = Field(default=None, alias="VERTEX_INDEX_ID")
    vertex_endpoint_id: str | None = Field(default=None, alias="VERTEX_ENDPOINT_ID")
    vertex_deployed_index_id: str | None = Field(default=None, alias="VERTEX_DEPLOYED_INDEX_ID")

    # Vector store backend selection (Qdrant deprecated, using Vertex AI by
    # default)
    vector_store_backend: str = Field(default="vertex", alias="VECTOR_STORE_BACKEND")  # "vertex" (qdrant deprecated)

    # Development/Server Configuration
    reload: bool = Field(default=False, alias="RELOAD")
    port: int = Field(default=8000, alias="PORT")

    # Knowledge Graph Configuration
    # L2 integration (Phase 2): optional private backend via importlib (ADR-003)
    kg_enabled: bool = Field(
        default=False,
        alias="KG_ENABLED",
        description="Enable optional private L2 graph store; when false, NoOpGraphStore is used",
    )
    kg_backend_module: str = Field(
        default="aiecs_kg",
        alias="KG_BACKEND_MODULE",
        description="Module name for private create_graph_store(settings) when KG_ENABLED=true",
    )

    # L1 Temporal Memory (Graphiti optional — install: pip install aiecs[temporal-graphiti])
    tm_enabled: bool = Field(
        default=False,
        alias="TM_ENABLED",
        description="Enable L1 temporal memory; when false, NoOpTemporalMemoryStore is used",
    )
    tm_backend: str = Field(
        default="none",
        alias="TM_BACKEND",
        description="Temporal backend: none | graphiti | postgres",
    )
    tm_postgres_url: str = Field(
        default="",
        alias="TM_POSTGRES_URL",
        description="PostgreSQL DSN for TM_BACKEND=postgres (falls back to POSTGRES_URL)",
    )
    tm_postgres_auto_create_tables: bool = Field(
        default=True,
        alias="TM_POSTGRES_AUTO_CREATE_TABLES",
        description="Auto-apply tm_episode/tm_fact DDL on initialize (dev); use migration in prod",
    )
    tm_graph_backend: str = Field(
        default="falkordb",
        alias="TM_GRAPH_BACKEND",
        description="Graphiti graph driver: falkordb | neo4j",
    )
    tm_falkordb_url: str = Field(
        default="redis://localhost:6379",
        alias="TM_FALKORDB_URL",
        description="FalkorDB connection URL when TM_GRAPH_BACKEND=falkordb",
    )
    tm_neo4j_uri: str = Field(default="", alias="TM_NEO4J_URI")
    tm_neo4j_user: str = Field(default="", alias="TM_NEO4J_USER")
    tm_neo4j_password: str = Field(default="", alias="TM_NEO4J_PASSWORD")
    tm_ingest_async: bool = Field(
        default=True,
        alias="TM_INGEST_ASYNC",
        description="POST_TASK ingest via async queue (non-blocking)",
    )
    tm_store_raw_episode: bool = Field(
        default=False,
        alias="TM_STORE_RAW_EPISODE",
        description="Store raw episode text in Graphiti (PII caution)",
    )
    tm_search_limit: int = Field(default=10, ge=1, alias="TM_SEARCH_LIMIT")
    tm_group_id_prefix: str = Field(
        default="aiecs",
        alias="TM_GROUP_ID_PREFIX",
        description="Namespace prefix for Graphiti group_id values",
    )
    tm_search_primary_group_only: bool = Field(
        default=False,
        alias="TM_SEARCH_PRIMARY_GROUP_ONLY",
        description="Search only the primary session group_id (omit tenant scope)",
    )
    tm_ingest_all_group_ids: bool = Field(
        default=False,
        alias="TM_INGEST_ALL_GROUP_IDS",
        description="Ingest the same episode into every resolved group_id (advanced; default primary only)",
    )
    tm_search_cache_enabled: bool = Field(
        default=True,
        alias="TM_SEARCH_CACHE_ENABLED",
        description="Enable in-process TTL cache for temporal search",
    )
    tm_search_cache_ttl_seconds: float = Field(
        default=30.0,
        gt=0,
        alias="TM_SEARCH_CACHE_TTL_SECONDS",
        description="TTL for temporal search cache entries (seconds)",
    )
    tm_search_cache_max_size: int = Field(
        default=256,
        ge=1,
        alias="TM_SEARCH_CACHE_MAX_SIZE",
        description="Max entries in temporal search TTL cache",
    )
    tm_episode_body_max_chars: int = Field(
        default=4000,
        ge=1,
        alias="TM_EPISODE_BODY_MAX_CHARS",
        description="Max episode body length before ingest (PII / size guard)",
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="allow")

    @field_validator("tm_backend", mode="before")
    @classmethod
    def _normalize_tm_backend(cls, value: Any) -> str:
        if value is None:
            return "none"
        return str(value).strip().lower()

    @field_validator("tm_backend")
    @classmethod
    def _validate_tm_backend(cls, value: str) -> str:
        if value not in _TM_BACKENDS:
            raise ValueError(f"TM_BACKEND must be one of {sorted(_TM_BACKENDS)}; got {value!r}")
        return value

    @field_validator("tm_graph_backend", mode="before")
    @classmethod
    def _normalize_tm_graph_backend(cls, value: Any) -> str:
        if value is None:
            return "falkordb"
        return str(value).strip().lower()

    @field_validator("tm_graph_backend")
    @classmethod
    def _validate_tm_graph_backend(cls, value: str) -> str:
        if value not in _TM_GRAPH_BACKENDS:
            raise ValueError(f"TM_GRAPH_BACKEND must be one of {sorted(_TM_GRAPH_BACKENDS)}; got {value!r}")
        return value

    @model_validator(mode="after")
    def _validate_temporal_memory_settings(self) -> Self:
        backend: Literal["none", "graphiti", "postgres"] = self.tm_backend  # type: ignore[assignment]
        if backend == "postgres" and not self.tm_enabled:
            raise ValueError("TM_BACKEND=postgres requires TM_ENABLED=true")
        if backend == "postgres" and self.tm_enabled:
            dsn = (self.tm_postgres_url or self.postgres_url or "").strip()
            if not dsn:
                raise ValueError("TM_BACKEND=postgres requires TM_POSTGRES_URL or POSTGRES_URL when TM_ENABLED=true")
        if backend == "graphiti" and self.tm_enabled and not (self.has_vertex_gcp_credentials_configured() or (self.openai_api_key or "").strip() or (self.googleai_api_key or "").strip()):
            logger.debug("TM_BACKEND=graphiti with TM_ENABLED=true but no Vertex, OpenAI, or Google AI credentials; " "Graphiti LLM/embedder initialization may fail")
        return self

    def has_vertex_gcp_credentials_configured(self) -> bool:
        """True if any explicit GCP JSON credential path is set (global or per-Vertex-client)."""
        return bool(
            self.google_application_credentials
            or self.google_application_credentials_vertex_gemini
            or self.google_application_credentials_vertex_anthropic
            or self.google_application_credentials_vertex_maas
        )

    @property
    def anthropic_vertex_project_id(self) -> str:
        """GCP project for Claude on Vertex; falls back to VERTEX_PROJECT_ID."""
        s = (self.vertex_project_id_anthropic or "").strip()
        return s or (self.vertex_project_id or "").strip()

    @property
    def anthropic_vertex_location(self) -> str:
        """Region for Claude on Vertex; falls back to VERTEX_LOCATION."""
        s = (self.vertex_location_anthropic or "").strip()
        return s or (self.vertex_location or "us-central1").strip() or "us-central1"

    @property
    def maas_vertex_project_id(self) -> str:
        """GCP project for Vertex AI MaaS OpenAPI; falls back to VERTEX_PROJECT_ID."""
        s = (self.vertex_project_id_maas or "").strip()
        return s or (self.vertex_project_id or "").strip()

    @property
    def maas_vertex_location(self) -> str:
        """Region for Vertex MaaS (e.g. global for Grok); falls back to VERTEX_LOCATION."""
        s = (self.vertex_location_maas or "").strip()
        return s or (self.vertex_location or "us-central1").strip() or "us-central1"

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

    def get_fusion_matching_config(self) -> Any:
        """Legacy fusion matching config stub (monorepo KG removed; use private aiecs-kg)."""
        logger.warning("get_fusion_matching_config() is legacy after monorepo KG removal; " "configure matching in private aiecs-kg if needed")

        class _FusionMatchingConfigStub:
            def __init__(self, **kwargs: Any) -> None:
                self.__dict__.update(kwargs)
                self.entity_type_configs: dict[str, Any] = {}

            def get_config_for_type(self, entity_type: str) -> "_FusionMatchingConfigStub":
                _ = entity_type
                return self

            def add_entity_type_config(self, entity_type: str, type_config: Any) -> None:
                self.entity_type_configs[entity_type] = type_config

        return _FusionMatchingConfigStub(
            alias_match_score=0.98,
            abbreviation_match_score=0.95,
            normalization_match_score=0.90,
            semantic_threshold=0.85,
            string_similarity_threshold=0.80,
            enabled_stages=["exact", "alias", "abbreviation", "normalized", "semantic", "string"],
            semantic_enabled=True,
        )


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
        any_vertex_project = bool(settings.vertex_project_id or settings.vertex_project_id_anthropic or settings.vertex_project_id_maas)
        llm_configs = [
            ("OpenAI", settings.openai_api_key),
            (
                "Vertex AI",
                any_vertex_project and settings.has_vertex_gcp_credentials_configured(),
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
        if settings.kg_enabled and not (settings.kg_backend_module or "").strip():
            missing.append("KG_BACKEND_MODULE (required when KG_ENABLED=true)")

    if missing:
        raise ValueError(f"Missing required settings for {operation_type} operation: {', '.join(missing)}\n" "Please check your .env file or environment variables.")

    return True
