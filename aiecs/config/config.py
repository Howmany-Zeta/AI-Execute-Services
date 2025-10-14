from pydantic import Field, ConfigDict
from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path

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
        description="Path to LLM models YAML configuration file"
    )
    
    # Infrastructure Configuration (with sensible defaults)
    celery_broker_url: str = Field(default="redis://localhost:6379/0", alias="CELERY_BROKER_URL")
    cors_allowed_origins: str = Field(default="http://localhost:3000,http://express-gateway:3001", alias="CORS_ALLOWED_ORIGINS")

    # PostgreSQL Database Configuration (with defaults)
    db_host: str = Field(default="localhost", alias="DB_HOST")
    db_user: str = Field(default="postgres", alias="DB_USER")
    db_password: str = Field(default="", alias="DB_PASSWORD")
    db_name: str = Field(default="aiecs", alias="DB_NAME")
    db_port: int = Field(default=5432, alias="DB_PORT")
    postgres_url: str = Field(default="", alias="POSTGRES_URL")

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

    # Vector store backend selection (Qdrant deprecated, using Vertex AI by default)
    vector_store_backend: str = Field("vertex", alias="VECTOR_STORE_BACKEND")  # "vertex" (qdrant deprecated)

    # Development/Server Configuration
    reload: bool = Field(default=False, alias="RELOAD")
    port: int = Field(default=8000, alias="PORT")

    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8", extra="allow")

    @property
    def database_config(self) -> dict:
        """Get database configuration for asyncpg"""
        return {
            "host": self.db_host,
            "user": self.db_user,
            "password": self.db_password,
            "database": self.db_name,
            "port": self.db_port
        }

    @property
    def file_storage_config(self) -> dict:
        """Get file storage configuration for Google Cloud Storage"""
        return {
            "gcs_project_id": self.google_cloud_project_id,
            "gcs_bucket_name": self.google_cloud_storage_bucket,
            "gcs_credentials_path": self.google_application_credentials,
            "enable_local_fallback": True,
            "local_storage_path": "./storage"
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
                raise FileNotFoundError(
                    f"LLM models config file not found: {config_path}"
                )
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
            ("Vertex AI", settings.vertex_project_id and settings.google_application_credentials),
            ("xAI", settings.xai_api_key)
        ]
        
        if not any(config[1] for config in llm_configs):
            missing.append("At least one LLM provider (OpenAI, Vertex AI, or xAI)")
    
    if operation_type in ["database", "full"]:
        if not settings.db_password:
            missing.append("DB_PASSWORD")
        
    if operation_type in ["storage", "full"]:
        if settings.google_cloud_project_id and not settings.google_cloud_storage_bucket:
            missing.append("GOOGLE_CLOUD_STORAGE_BUCKET (required when GOOGLE_CLOUD_PROJECT_ID is set)")
    
    if missing:
        raise ValueError(
            f"Missing required settings for {operation_type} operation: {', '.join(missing)}\n"
            "Please check your .env file or environment variables."
        )
    
    return True
