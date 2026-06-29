from unittest.mock import MagicMock

import pytest

from app.domains.graph.data import ExtractedCropKnowledge, GraphIngestArtifacts, GraphIngestResult
from app.domains.graph.persistence import SourceAlreadyGraphIngestedError
from app.domains.graph.service import GraphIngestionService
from app.domains.ingestion.repositories import ExistingSourceInfo
from app.infrastructure.repositories.db import (
    KNOWLEDGE_SOURCE_STATUS_FAILED,
    KNOWLEDGE_SOURCE_STATUS_GRAPH_INDEXED,
)
from app.shared.document.content import ExtractOptions
from app.shared.document.loader import KnowledgeDocument


def test_graph_ingestion_service_happy_path() -> None:
    pipeline = MagicMock()
    pipeline.load_documents.return_value = [
        KnowledgeDocument("Crop document text.", {"source_uri": "pepper.html"}),
    ]
    extractor = MagicMock()
    extractor.extract.return_value = ExtractedCropKnowledge(
        crop_name="Wrong",
        scientific_name="Piper nigrum",
    )
    graph_store = MagicMock()
    source_repo = MagicMock()
    source_repo.find_by_origin_url.return_value = None
    source_repo.create_pending.return_value = 5

    service = GraphIngestionService(
        pipeline=pipeline,
        extractor=extractor,
        graph_store=graph_store,
        source_repository=source_repo,
        default_loader="html_plain",
    )

    result = service.ingest("pepper.html", "Pepper", loader="html_plain")

    assert isinstance(result, GraphIngestResult)
    assert result.source_id == 5
    assert result.crop_name == "Pepper"
    extractor.extract.assert_called_once()
    upsert_call = graph_store.upsert_crop.call_args
    assert upsert_call.kwargs["crop_tag"] == "Pepper"
    assert upsert_call.args[0].crop_name == "Pepper"


def test_graph_ingestion_service_marks_failed_on_error() -> None:
    pipeline = MagicMock()
    pipeline.load_documents.side_effect = RuntimeError("load failed")
    source_repo = MagicMock()
    source_repo.find_by_origin_url.return_value = MagicMock(source_id=3)

    service = GraphIngestionService(
        pipeline=pipeline,
        extractor=MagicMock(),
        graph_store=MagicMock(),
        source_repository=source_repo,
        default_loader="text",
    )

    with pytest.raises(RuntimeError, match="load failed"):
        service.ingest("pepper.html", "Pepper")

    source_repo.update_status.assert_called_once_with(3, KNOWLEDGE_SOURCE_STATUS_FAILED)


def test_graph_ingestion_service_propagates_already_graph_ingested() -> None:
    pipeline = MagicMock()
    pipeline.load_documents.return_value = [
        KnowledgeDocument("text", {"source_uri": "pepper.html"}),
    ]
    extractor = MagicMock()
    extractor.extract.return_value = ExtractedCropKnowledge(crop_name="Pepper")
    graph_store = MagicMock()
    graph_store.count_by_source_uri.return_value = 1
    source_repo = MagicMock()
    source_repo.find_by_origin_url.return_value = ExistingSourceInfo(
        source_id=1,
        status=KNOWLEDGE_SOURCE_STATUS_GRAPH_INDEXED,
        crop_names=["Pepper"],
    )

    service = GraphIngestionService(
        pipeline=pipeline,
        extractor=extractor,
        graph_store=graph_store,
        source_repository=source_repo,
        default_loader="text",
    )
    with pytest.raises(SourceAlreadyGraphIngestedError):
        service.ingest("pepper.html", "Pepper")


def test_graph_ingestion_service_saves_json_artifact(tmp_path) -> None:
    pipeline = MagicMock()
    pipeline.load_documents.return_value = [
        KnowledgeDocument("Crop document text.", {"source_uri": "pepper.html"}),
    ]
    extractor = MagicMock()
    extractor.extract.return_value = ExtractedCropKnowledge(
        crop_name="Pepper",
        scientific_name="Piper nigrum",
    )
    graph_store = MagicMock()
    source_repo = MagicMock()
    source_repo.find_by_origin_url.return_value = None
    source_repo.create_pending.return_value = 5

    json_path = tmp_path / "graph_json" / "pepper.json"
    service = GraphIngestionService(
        pipeline=pipeline,
        extractor=extractor,
        graph_store=graph_store,
        source_repository=source_repo,
        default_loader="html_plain",
    )

    result = service.ingest(
        "pepper.html",
        "Pepper",
        loader="html_plain",
        artifacts=GraphIngestArtifacts(json_output_path=json_path),
    )

    assert json_path.is_file()
    assert result.json_path == json_path
    saved = json_path.read_text(encoding="utf-8")
    assert "Piper nigrum" in saved


def test_graph_ingestion_service_merges_html_persist_for_web_url(tmp_path) -> None:
    pipeline = MagicMock()
    pipeline.load_documents.return_value = [
        KnowledgeDocument("web text", {"source_uri": "https://example.com/crop"}),
    ]
    extractor = MagicMock()
    extractor.extract.return_value = ExtractedCropKnowledge(crop_name="Crop")
    source_repo = MagicMock()
    source_repo.find_by_origin_url.return_value = None
    source_repo.create_pending.return_value = 1

    html_path = tmp_path / "graph_html" / "example.html"
    service = GraphIngestionService(
        pipeline=pipeline,
        extractor=extractor,
        graph_store=MagicMock(),
        source_repository=source_repo,
        default_loader="doa_hordi",
    )

    service.ingest(
        "https://example.com/crop",
        "Crop",
        loader="doa_hordi",
        extract_options=ExtractOptions(timeout_seconds=99),
        artifacts=GraphIngestArtifacts(html_output_path=html_path),
    )

    call_kwargs = pipeline.load_documents.call_args.kwargs
    opts = call_kwargs["extract_options"]
    assert opts.persist_raw is True
    assert opts.raw_output_path == html_path
    assert opts.timeout_seconds == 99
