from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./croppilot.db"
    chroma_persist_dir: str = "./chroma_db"

    embedding_backend: Literal["fast", "hf", "openai", "gemini"] = "fast"
    llm_backend: Literal["ollama", "openai", "gemini"] = "gemini"
    default_loader: Literal["text", "docling"] = "text"
    default_chunker: Literal["section", "recursive"] = "section"

    recursive_chunk_size: int = 500
    recursive_chunk_overlap: int = 50
    retrieval_top_k: int = 3

    # CORS (comma-separated list, e.g. "http://localhost:5173,http://localhost:3000")
    cors_allow_origins: str = "http://localhost:5173,http://localhost:3000"

    # LLM model names
    gemini_model: str = "models/gemini-2.5-flash"
    ollama_model: str = "llama3"
    openai_model: str = "gpt-4o-mini"

    # API keys (loaded from .env)
    google_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GOOGLE_API_KEY", "GEMINI_API_KEY"),
    )
    openai_api_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
