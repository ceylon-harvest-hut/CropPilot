import pytest

from app.domains.ingestion.loader import KnowledgeDocument
from app.infrastructure.chunkers.recursive_chunker import RecursiveChunker
from app.infrastructure.chunkers.section_chunker import SectionChunker
from app.infrastructure.factories import (
    build_chunker_by_name,
    build_embedder_by_name,
    build_loader_by_name,
    build_loader_registry,
)
from app.infrastructure.loaders.docling_loader import DoclingDocumentLoader
from app.infrastructure.loaders.text_loader import TextDocumentLoader
from app.infrastructure.llm.embeddings import FastEmbedEmbeddingService


def _doc(text: str) -> KnowledgeDocument:
    return KnowledgeDocument(text=text, metadata={"source_uri": "test", "media_type": "text/plain"})


def test_build_loader_text() -> None:
    loader = build_loader_by_name("text")
    assert isinstance(loader, TextDocumentLoader)
    assert loader.supports("file.txt")


def test_build_loader_docling() -> None:
    loader = build_loader_by_name("docling")
    assert isinstance(loader, DoclingDocumentLoader)
    assert loader.supports("file.pdf")


def test_build_loader_registry_resolves_by_extension() -> None:
    from app.infrastructure.config import Settings

    registry = build_loader_registry(Settings())
    assert isinstance(registry.resolve("notes.txt"), TextDocumentLoader)
    assert isinstance(registry.resolve("report.pdf"), DoclingDocumentLoader)


def test_build_loader_unknown_raises() -> None:
    with pytest.raises(ValueError, match="Unknown loader"):
        build_loader_by_name("pdf")


def test_build_chunker_section() -> None:
    chunker = build_chunker_by_name("section")
    assert isinstance(chunker, SectionChunker)
    chunks = chunker.chunk([_doc("Introduction\n\nSome text.")], crop_tag="Pepper")
    assert len(chunks) >= 1


def test_build_chunker_recursive() -> None:
    chunker = build_chunker_by_name("recursive", chunk_size=100, chunk_overlap=10)
    assert isinstance(chunker, RecursiveChunker)
    chunks = chunker.chunk([_doc("Word " * 100)], crop_tag="Pepper")
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
