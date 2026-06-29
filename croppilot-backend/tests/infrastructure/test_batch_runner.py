from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.shared.document.content import ExtractOptions
from app.domains.ingestion.data import KnowledgeChunk
from app.shared.document.loader import KnowledgeDocument
from app.domains.ingestion.persistence import SourceAlreadyIngestedError
from app.infrastructure.ingestion.batch_manifest import ManifestEntry
from app.infrastructure.ingestion.batch_runner import ingest_manifest_entry
from app.infrastructure.repositories.db import Base
from app.infrastructure.repositories.knowledge_source_repo import SqlKnowledgeSourceRepository

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PEPPER_HTML = REPO_ROOT / "data" / "web_collection" / "html" / "dea-gov-lk-pepper.html"


@pytest.fixture
def source_repository():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield SqlKnowledgeSourceRepository(session)
    session.close()


def test_ingest_manifest_entry_skips_when_already_ingested(source_repository) -> None:
    pipeline = MagicMock()
    chunker = MagicMock()
    embedder = MagicMock()
    vector_store = MagicMock()

    vector_store.count_by_source_uri.return_value = 3
    source_repository.create_pending("pepper.txt", "Pepper")
    source_repository.update_status(1, "INDEXED")

    entry = ManifestEntry(source_uri="pepper.txt", crop_name="Pepper", source_type="file")
    result = ingest_manifest_entry(
        entry,
        pipeline=pipeline,
        loader="text",
        chunker=chunker,
        embedder=embedder,
        vector_store=vector_store,
        source_repository=source_repository,
        skip_existing=True,
    )

    assert result.outcome == "skipped"
    assert result.chunk_count == 3
    pipeline.load_documents.assert_not_called()


def test_ingest_manifest_entry_errors_when_already_ingested_without_skip(source_repository) -> None:
    pipeline = MagicMock()
    chunker = MagicMock()
    embedder = MagicMock()
    vector_store = MagicMock()

    vector_store.count_by_source_uri.return_value = 2
    source_repository.create_pending("pepper.txt", "Pepper")
    source_repository.update_status(1, "INDEXED")

    entry = ManifestEntry(source_uri="pepper.txt", crop_name="Pepper", source_type="file")
    result = ingest_manifest_entry(
        entry,
        pipeline=pipeline,
        loader="text",
        chunker=chunker,
        embedder=embedder,
        vector_store=vector_store,
        source_repository=source_repository,
        skip_existing=False,
    )

    assert result.outcome == "error"
    assert "already ingested" in result.message.lower()


def test_ingest_manifest_entry_success_with_mocks(source_repository) -> None:
    pipeline = MagicMock()
    chunker = MagicMock()
    embedder = MagicMock()
    vector_store = MagicMock()

    doc = KnowledgeDocument(text="Section text", metadata={})
    chunk = KnowledgeChunk(
        text_content="Section text",
        metadata={"crop_tag": "Pepper", "section_name": "History", "page_number": 0},
    )
    pipeline.load_documents.return_value = [doc]
    chunker.chunk.return_value = [chunk]
    embedder.embed.side_effect = lambda chunks: chunks

    entry = ManifestEntry(source_uri="pepper.txt", crop_name="Pepper", source_type="file")
    result = ingest_manifest_entry(
        entry,
        pipeline=pipeline,
        loader="text",
        chunker=chunker,
        embedder=embedder,
        vector_store=vector_store,
        source_repository=source_repository,
    )

    assert result.outcome == "ok"
    assert result.chunk_count == 1
    assert result.source_id == 1
    vector_store.upsert.assert_called_once()


def test_ingest_manifest_entry_passes_extract_options(source_repository) -> None:
    pipeline = MagicMock()
    chunker = MagicMock()
    embedder = MagicMock()
    vector_store = MagicMock()

    doc = KnowledgeDocument(text="Section text", metadata={})
    chunk = KnowledgeChunk(
        text_content="Section text",
        metadata={"crop_tag": "Pepper", "section_name": "History", "page_number": 0},
    )
    pipeline.load_documents.return_value = [doc]
    chunker.chunk.return_value = [chunk]
    embedder.embed.side_effect = lambda chunks: chunks

    entry = ManifestEntry(
        source_uri="https://dea.gov.lk/pepper/",
        crop_name="Pepper",
        source_type="web_url",
    )
    extract_options = ExtractOptions(timeout_seconds=120)

    ingest_manifest_entry(
        entry,
        pipeline=pipeline,
        loader="dea_gov_lk",
        chunker=chunker,
        embedder=embedder,
        vector_store=vector_store,
        source_repository=source_repository,
        extract_options=extract_options,
    )

    pipeline.load_documents.assert_called_once_with(
        "https://dea.gov.lk/pepper/",
        "web_url",
        "dea_gov_lk",
        extract_options=extract_options,
    )


@pytest.mark.slow
@pytest.mark.skipif(not PEPPER_HTML.exists(), reason="pepper.html fixture not present")
def test_ingest_manifest_entry_dea_html_integration(tmp_path: Path, source_repository) -> None:
    from app.infrastructure.config import Settings
    from app.infrastructure.factories import (
        build_chunker_by_name,
        build_document_pipeline,
        build_embedder,
        build_vector_store,
    )

    settings = Settings(chroma_persist_dir=str(tmp_path / "chroma"))
    pipeline = build_document_pipeline(settings)
    chunker = build_chunker_by_name("dea_gov_lk")
    embedder = build_embedder(settings)
    vector_store = build_vector_store(settings)

    entry = ManifestEntry(
        source_uri=str(PEPPER_HTML),
        crop_name="Pepper",
        source_type="file",
    )
    result = ingest_manifest_entry(
        entry,
        pipeline=pipeline,
        loader="dea_gov_lk",
        chunker=chunker,
        embedder=embedder,
        vector_store=vector_store,
        source_repository=source_repository,
    )

    assert result.outcome == "ok"
    assert result.chunk_count >= 8
    assert vector_store.count() == result.chunk_count
