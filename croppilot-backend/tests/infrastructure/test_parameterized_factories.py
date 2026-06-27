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
from app.infrastructure.loaders.dea_gov_lk_si_loader import DeaGovLkSiLoader
from app.infrastructure.loaders.doa_hordi_loader import DoaHordiLoader
from app.infrastructure.loaders.text_loader import TextLoader
from app.infrastructure.chunkers.dea_gov_lk_si_chunker import DeaGovLkSiChunker
from app.infrastructure.chunkers.doa_hordi_chunker import DoaHordiChunker
from app.infrastructure.embedders.fastembed_bge import FastEmbedBGEEmbedder
from app.infrastructure.embedders.fastembed_e5 import FastEmbedE5Embedder

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


def test_build_loader_dea_gov_lk_si() -> None:
    loader = build_loader_by_name("dea_gov_lk_si")
    assert isinstance(loader, DeaGovLkSiLoader)


def test_build_chunker_dea_gov_lk_si() -> None:
    chunker = build_chunker_by_name("dea_gov_lk_si")
    assert isinstance(chunker, DeaGovLkSiChunker)


def test_build_loader_doa_hordi() -> None:
    loader = build_loader_by_name("doa_hordi")
    assert isinstance(loader, DoaHordiLoader)


def test_build_chunker_doa_hordi() -> None:
    chunker = build_chunker_by_name("doa_hordi")
    assert isinstance(chunker, DoaHordiChunker)


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


def test_build_chunker_dea_hybrid() -> None:
    from app.infrastructure.chunkers.dea_hybrid_chunker import DeaHybridChunker

    chunker = build_chunker_by_name("dea_hybrid", chunk_size=800, chunk_overlap=50)
    assert isinstance(chunker, DeaHybridChunker)
    long_text = "Detail sentence. " * 80
    doc = _doc(long_text)
    doc.metadata["section_name"] = "History"
    chunks = chunker.chunk([doc], crop_tag="Pepper")
    assert len(chunks) > 1


def test_build_chunker_unknown_raises() -> None:
    with pytest.raises(ValueError, match="Unknown chunker"):
        build_chunker_by_name("sliding_window")


def test_build_embedder_fast_alias() -> None:
    """'fast' is kept as a backward-compat alias for bge_small."""
    from pathlib import Path
    from unittest.mock import patch

    with patch("app.infrastructure.embedders.fastembed_bge.validate_model_cache"), \
         patch("app.infrastructure.embedders.fastembed_bge.TextEmbedding"):
        embedder = build_embedder_by_name("fast", cache_dir=Path("/fake/cache"))
    assert isinstance(embedder, FastEmbedBGEEmbedder)


def test_build_embedder_bge_small() -> None:
    from pathlib import Path
    from unittest.mock import patch

    with patch("app.infrastructure.embedders.fastembed_bge.validate_model_cache"), \
         patch("app.infrastructure.embedders.fastembed_bge.TextEmbedding"):
        embedder = build_embedder_by_name("bge_small", cache_dir=Path("/fake/cache"))
    assert isinstance(embedder, FastEmbedBGEEmbedder)


def test_build_embedder_e5_multilingual() -> None:
    from pathlib import Path
    from unittest.mock import patch

    with patch("app.infrastructure.embedders.fastembed_e5.validate_model_cache"), \
         patch("app.infrastructure.embedders.fastembed_e5.TextEmbedding"):
        embedder = build_embedder_by_name("e5_multilingual", cache_dir=Path("/fake/cache"))
    assert isinstance(embedder, FastEmbedE5Embedder)


def test_build_embedder_unknown_raises() -> None:
    with pytest.raises(ValueError, match="Unknown embedder"):
        build_embedder_by_name("openai")
