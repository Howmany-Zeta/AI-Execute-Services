from pydantic import Field, ConfigDict
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    vertex_project_id: str = Field(..., alias="VERTEX_PROJECT_ID")
    vertex_location: str = Field(default="us-central1", alias="VERTEX_LOCATION")
    grok_api_key: str = Field(None, alias="GROK_API_KEY")
    celery_broker_url: str = Field(..., alias="CELERY_BROKER_URL")
    cors_allowed_origins: str = Field("http://express-gateway:3001", alias="CORS_ALLOWED_ORIGINS")
    qdrant_url: str = Field("http://qdrant:6333", alias="QDRANT_URL")
    qdrant_collection: str = Field("documents", alias="QDRANT_COLLECTION")

    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")

@lru_cache()
def get_settings():
    return Settings()
