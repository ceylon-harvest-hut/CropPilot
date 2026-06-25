from functools import lru_cache
from typing import Literal

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


@lru_cache
def get_settings() -> Settings:
    return Settings()