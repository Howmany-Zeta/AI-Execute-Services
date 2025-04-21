from pydantic import BaseSettings, Field
from functools import lru_cache

class Settings(BaseSettings):
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    vector_db_project_id: str = Field(..., env="VECTOR_DB_PROJECT_ID")
    celery_broker_url: str = Field(..., env="CELERY_BROKER_URL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings():
    return Settings()
