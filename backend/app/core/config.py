from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Agentic Research Workspace"
    app_version: str = "0.1.0"
    api_prefix: str = "/api/v1"
    environment: Literal["local", "development", "staging", "production"] = "local"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    database_url: str = "sqlite:///./agentic_research.db"
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_collection_prefix: str = "workspace"

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_secure: bool = False
    minio_documents_bucket: str = "documents"
    minio_reports_bucket: str = "reports"

    jwt_secret_key: str = Field(default="change-me", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    reranker_model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # ── LLM Keys ──────────────────────────────────────────────────────────
    # Gemini (free) — https://aistudio.google.com/apikey
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")

    # OpenAI / compatible (optional)
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_base_url: str = Field(default="https://api.openai.com/v1", alias="OPENAI_BASE_URL")

    # Model name — used for whichever provider is active
    llm_model: str = Field(default="gemini-2.0-flash", alias="LLM_MODEL")
    llm_provider: str = Field(default="gemini", alias="LLM_PROVIDER")

    web_search_provider: str = "duckduckgo"
    enable_langsmith: bool = False
    langsmith_project: str = "agentic-research-workspace"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
