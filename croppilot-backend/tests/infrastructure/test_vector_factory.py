"""Tests for build_vector_store factory and the vector_backend setting."""

from __future__ import annotations

import pytest

from app.domains.vector.repositories import (
    KnowledgeVectorRepository,
    VectorSearchRepository,
    VectorWriteRepository,
)
from app.infrastructure.config import Settings
from app.infrastructure.factories import build_vector_store
from app.infrastructure.repositories.chroma_store import ChromaVectorStore


def test_default_backend_is_chroma(tmp_path) -> None:
    settings = Settings(chroma_persist_dir=str(tmp_path / "chroma"))
    store = build_vector_store(settings)
    assert isinstance(store, ChromaVectorStore)


def test_build_vector_store_returns_knowledge_vector_repository(tmp_path) -> None:
    settings = Settings(chroma_persist_dir=str(tmp_path / "chroma"))
    store = build_vector_store(settings)
    assert hasattr(store, "upsert")
    assert hasattr(store, "search")
    assert hasattr(store, "list_chunks")
    assert hasattr(store, "count")
    assert hasattr(store, "count_by_source_uri")
    assert hasattr(store, "delete_by_source_uri")


def test_unknown_vector_backend_raises() -> None:
    settings = Settings()
    settings.__dict__["vector_backend"] = "unknown"
    with pytest.raises(ValueError, match="Unknown vector backend"):
        build_vector_store(settings)
