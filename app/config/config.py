from pydantic import Field, ConfigDict
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    vertex_project_id: str = Field(..., alias="VERTEX_PROJECT_ID")
    vertex_location: str = Field(default="us-central1", alias="VERTEX_LOCATION")
    google_application_credentials: str = Field(None, alias="GOOGLE_APPLICATION_CREDENTIALS")
    xai_api_key: str = Field(None, alias="XAI_API_KEY")
    grok_api_key: str = Field(None, alias="GROK_API_KEY")  # Backward compatibility
    celery_broker_url: str = Field(..., alias="CELERY_BROKER_URL")
    cors_allowed_origins: str = Field("http://express-gateway:3001", alias="CORS_ALLOWED_ORIGINS")

    # PostgreSQL Database Configuration
    db_host: str = Field(..., alias="DB_HOST")
    db_user: str = Field(..., alias="DB_USER")
    db_password: str = Field(..., alias="DB_PASSWORD")
    db_name: str = Field(..., alias="DB_NAME")
    db_port: int = Field(5432, alias="DB_PORT")
    postgres_url: str = Field(None, alias="POSTGRES_URL")

    # Google Cloud Storage Configuration
    google_cloud_project_id: str = Field(..., alias="GOOGLE_CLOUD_PROJECT_ID")
    google_cloud_storage_bucket: str = Field(..., alias="GOOGLE_CLOUD_STORAGE_BUCKET")

    # Qdrant configuration (legacy)
    qdrant_url: str = Field("http://qdrant:6333", alias="QDRANT_URL")
    qdrant_collection: str = Field("documents", alias="QDRANT_COLLECTION")

    # Vertex AI Vector Search configuration
    vertex_index_id: str | None = Field(default=None, alias="VERTEX_INDEX_ID")
    vertex_endpoint_id: str | None = Field(default=None, alias="VERTEX_ENDPOINT_ID")
    vertex_deployed_index_id: str | None = Field(default=None, alias="VERTEX_DEPLOYED_INDEX_ID")

    # Vector store backend selection (Qdrant deprecated, using Vertex AI by default)
    vector_store_backend: str = Field("vertex", alias="VECTOR_STORE_BACKEND")  # "vertex" (qdrant deprecated)

    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")

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

@lru_cache()
def get_settings():
    return Settings()
