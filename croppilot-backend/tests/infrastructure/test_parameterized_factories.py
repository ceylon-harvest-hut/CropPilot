from pathlib import Path

import pytest

from app.domains.ingestion.content import RawContent
from app.domains.ingestion.loader import KnowledgeDocument
from app.domains.ingestion.source_types import SOURCE_TYPE_FILE
from app.infrastructure.chunkers.recursive_chunker import RecursiveChunker
from app.infrastructure.chunkers.section_chunker import SectionChunker
from app.infrastructure.config import Settings
from app.infrastructure.factories import (
    build_chunker_by_name,
    build_document_pipeline,
    build_embedder_by_name,
    build_loader_by_name,
    build_loader_registry,
)
from app.infrastructure.loaders.docling_loader import DoclingLoader
from app.infrastructure.loaders.html_plain_loader import HtmlPlainLoader
from app.infrastructure.loaders.text_loader import TextLoader
from app.infrastructure.llm.embeddings import FastEmbedEmbeddingService

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def _doc(text: str) -> KnowledgeDocument:
    return KnowledgeDocument(text=text, metadata={"source_uri": "test", "media_type": "text/plain"})


def _raw_txt(path: str) -> RawContent:
    p = Path(path)
    return RawContent(
        source_uri=path,
        resolved_uri=path,
        source_type=SOURCE_TYPE_FILE,
        media_type="text/plain",
        data=p.read_bytes() if p.exists() else b"test",
        local_path=p if p.exists() else None,
    )


def test_build_loader_text() -> None:
    loader = build_loader_by_name("text")
    assert isinstance(loader, TextLoader)
    assert loader.supports(_raw_txt("file.txt"))


def test_build_loader_docling() -> None:
    loader = build_loader_by_name("docling")
    assert isinstance(loader, DoclingLoader)
    assert loader.supports(
        RawContent(
            source_uri="file.pdf",
            resolved_uri="file.pdf",
            source_type=SOURCE_TYPE_FILE,
            media_type="application/pdf",
            data=b"",
        )
    )


def test_build_loader_html_plain() -> None:
    loader = build_loader_by_name("html_plain")
    assert isinstance(loader, HtmlPlainLoader)
    assert loader.supports(
        RawContent(
            source_uri="page.html",
            resolved_uri="page.html",
            source_type=SOURCE_TYPE_FILE,
            media_type="text/html",
            data=b"<html/>",
        )
    )


def test_build_loader_unknown_raises() -> None:
    with pytest.raises(ValueError, match="Unknown loader"):
        build_loader_by_name("pdf")


def test_build_document_pipeline_loads_text_file() -> None:
    settings = Settings()
    pipeline = build_document_pipeline(settings)
    source_uri = str(FIXTURES_DIR / "pepper.txt")
    docs = pipeline.load_documents(source_uri, SOURCE_TYPE_FILE, "text")
    assert len(docs) == 1
    assert isinstance(docs[0], KnowledgeDocument)


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
