from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./croppilot.db"
    chroma_persist_dir: str = "./chroma_db"

    vector_backend: Literal["chroma"] = "chroma"

    embedding_backend: Literal["bge_small", "e5_multilingual"] = "e5_multilingual"
    llm_backend: Literal["ollama", "openai", "gemini"] = "gemini"
    default_loader: Literal["text", "docling", "html_plain"] = "text"
    default_chunker: Literal["section", "recursive"] = "section"

    recursive_chunk_size: int = 500
    recursive_chunk_overlap: int = 50
    retrieval_top_k: int = 3
    default_ask_template: Literal["context_only", "hybrid"] = "context_only"

    # CORS (comma-separated list, e.g. "http://localhost:5173,http://localhost:3000")
    cors_allow_origins: str = "http://localhost:5173,http://localhost:3000"

    debug_enabled: bool = True

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

    # --- Embedding model cache ---
    # Permanent directory for FastEmbed ONNX models.
    # Never rely on the /tmp default — that is wiped on reboot.
    # Local dev:  ./models/fastembed  (gitignored)
    # Docker/prod: /app/models/fastembed  (baked in image via bootstrap_models.py)
    fastembed_cache_dir: str = "./models/fastembed"

    # When True the app will NOT fetch from Hugging Face at runtime.
    # Always True in Docker/prod; bootstrap_models.py overrides to False while downloading.
    hf_hub_offline: bool = False

    # Safety guard: if True, embedder constructors are allowed to trigger a download.
    # Must be False in production and CI; only True inside bootstrap_models.py.
    allow_model_download: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
