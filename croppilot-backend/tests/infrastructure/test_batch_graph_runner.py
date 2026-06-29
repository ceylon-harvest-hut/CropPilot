from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.domains.graph.data import GraphIngestResult
from app.domains.graph.persistence import SourceAlreadyGraphIngestedError
from app.infrastructure.ingestion.batch_graph_runner import ingest_graph_manifest_entry
from app.infrastructure.ingestion.batch_manifest import ManifestEntry
from app.infrastructure.repositories.db import Base, KNOWLEDGE_SOURCE_STATUS_GRAPH_INDEXED
from app.infrastructure.repositories.knowledge_source_repo import SqlKnowledgeSourceRepository


@pytest.fixture
def source_repository():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield SqlKnowledgeSourceRepository(session)
    session.close()


def test_ingest_graph_manifest_entry_skips_when_graph_indexed(source_repository) -> None:
    service = MagicMock()
    source_repository.create_pending("https://doa.gov.lk/cabbage/", "ගෝවා")
    source_repository.update_status(1, KNOWLEDGE_SOURCE_STATUS_GRAPH_INDEXED)

    entry = ManifestEntry(
        source_uri="https://doa.gov.lk/cabbage/",
        crop_name="ගෝවා",
        source_type="web_url",
    )
    result = ingest_graph_manifest_entry(
        entry,
        service=service,
        source_repository=source_repository,
        loader="doa_hordi",
        skip_existing=True,
    )

    assert result.outcome == "skipped"
    assert result.message == "already graph-ingested"
    service.ingest.assert_not_called()


def test_ingest_graph_manifest_entry_errors_when_graph_indexed_without_skip(
    source_repository,
) -> None:
    service = MagicMock()
    service.ingest.side_effect = SourceAlreadyGraphIngestedError(
        1, 1, KNOWLEDGE_SOURCE_STATUS_GRAPH_INDEXED, ["ගෝවා"]
    )

    entry = ManifestEntry(
        source_uri="https://doa.gov.lk/cabbage/",
        crop_name="ගෝවා",
        source_type="web_url",
    )
    result = ingest_graph_manifest_entry(
        entry,
        service=service,
        source_repository=source_repository,
        loader="doa_hordi",
        skip_existing=False,
    )

    assert result.outcome == "error"
    assert "graph-ingested" in result.message.lower()


def test_ingest_graph_manifest_entry_success(source_repository) -> None:
    service = MagicMock()
    service.ingest.return_value = GraphIngestResult(
        source_id=1,
        crop_name="ගෝවා",
        status=KNOWLEDGE_SOURCE_STATUS_GRAPH_INDEXED,
        replaced=False,
    )

    entry = ManifestEntry(
        source_uri="https://doa.gov.lk/cabbage/",
        crop_name="ගෝවා",
        source_type="web_url",
    )
    result = ingest_graph_manifest_entry(
        entry,
        service=service,
        source_repository=source_repository,
        loader="doa_hordi",
    )

    assert result.outcome == "ok"
    assert result.source_id == 1
    assert result.message == "graph-indexed"
    service.ingest.assert_called_once_with(
        "https://doa.gov.lk/cabbage/",
        manifest_crop_name="ගෝවා",
        source_type="web_url",
        loader="doa_hordi",
        replace_existing=False,
        extract_options=None,
        artifacts=None,
    )


def test_ingest_graph_manifest_entry_passes_extract_options(source_repository) -> None:
    from app.shared.document.content import ExtractOptions

    service = MagicMock()
    service.ingest.return_value = GraphIngestResult(
        source_id=2,
        crop_name="ගෝවා",
        status=KNOWLEDGE_SOURCE_STATUS_GRAPH_INDEXED,
    )
    extract_options = ExtractOptions(timeout_seconds=120)

    entry = ManifestEntry(
        source_uri="https://doa.gov.lk/cabbage/",
        crop_name="ගෝවා",
        source_type="web_url",
    )
    ingest_graph_manifest_entry(
        entry,
        service=service,
        source_repository=source_repository,
        loader="doa_hordi",
        extract_options=extract_options,
    )

    service.ingest.assert_called_once_with(
        "https://doa.gov.lk/cabbage/",
        manifest_crop_name="ගෝවා",
        source_type="web_url",
        loader="doa_hordi",
        replace_existing=False,
        extract_options=extract_options,
        artifacts=None,
    )


def test_ingest_graph_manifest_entry_does_not_skip_vector_indexed_only(
    source_repository,
) -> None:
    """VECTOR INDEXED sources should still be graph-ingested unless GRAPH_INDEXED."""
    service = MagicMock()
    service.ingest.return_value = GraphIngestResult(
        source_id=1,
        crop_name="Pepper",
        status=KNOWLEDGE_SOURCE_STATUS_GRAPH_INDEXED,
    )
    source_repository.create_pending("pepper.txt", "Pepper")
    source_repository.update_status(1, "INDEXED")

    entry = ManifestEntry(source_uri="pepper.txt", crop_name="Pepper", source_type="file")
    result = ingest_graph_manifest_entry(
        entry,
        service=service,
        source_repository=source_repository,
        loader="text",
        skip_existing=True,
    )

    assert result.outcome == "ok"
    service.ingest.assert_called_once()
