"""Centralized application configuration.

All runtime configuration is sourced from environment variables (with
sensible local defaults) via pydantic-settings, so the same image can be
promoted across environments without code changes.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "RAGDocs API"
    environment: str = "development"
    api_key: str = "change-me-local-dev-key"

    database_url: str = "postgresql+psycopg://ragdocs:ragdocs@db:5432/ragdocs"

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384

    chunk_size: int = 800
    chunk_overlap: int = 120

    top_k: int = 4

    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    upload_dir: str = "/app/data/uploads"
    max_upload_mb: int = 20

    @property
    def is_generation_enabled(self) -> bool:
        return bool(self.openai_api_key)


@lru_cache
def get_settings() -> Settings:
    """Settings are cached so env parsing happens once per process."""
    return Settings()
