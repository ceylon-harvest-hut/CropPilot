import pytest

from app.infrastructure.factories import (
    build_chunker_by_name,
    build_embedder_by_name,
    build_loader_by_name,
)
from app.infrastructure.loaders.text_loader import TextDocumentLoader
from app.infrastructure.llm.embeddings import FastEmbedEmbeddingService
from app.domains.ingestion.chunker import BaseChunker


def test_build_loader_text() -> None:
    loader = build_loader_by_name("text")
    assert isinstance(loader, TextDocumentLoader)
    assert loader.supports("file.txt")


def test_build_loader_unknown_raises() -> None:
    with pytest.raises(ValueError, match="Unknown loader"):
        build_loader_by_name("pdf")


def test_build_chunker_section() -> None:
    chunker = build_chunker_by_name("section")
    assert isinstance(chunker, BaseChunker)
    chunks = chunker.chunk("Introduction\nSome text.", crop_tag="Pepper")
    assert len(chunks) >= 1


def test_build_chunker_recursive() -> None:
    chunker = build_chunker_by_name("recursive", chunk_size=100, chunk_overlap=10)
    assert isinstance(chunker, BaseChunker)
    chunks = chunker.chunk("Word " * 100, crop_tag="Pepper")
    assert len(chunks) >= 1


def test_build_chunker_unknown_raises() -> None:
    with pytest.raises(ValueError, match="Unknown chunker"):
        build_chunker_by_name("sliding_window")


def test_build_embedder_fast() -> None:
    embedder = build_embedder_by_name("fast")
    assert isinstance(embedder, FastEmbedEmbeddingService)


def test_build_embedder_unknown_raises() -> None:
    with pytest.raises(ValueError, match="Unknown embedder"):
        build_embedder_by_name("openai")
