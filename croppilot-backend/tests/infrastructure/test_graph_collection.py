from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.domains.graph.data import ExtractedCropKnowledge, GraphIngestResult
from app.domains.graph.schemas import Pest
from app.infrastructure.graph.graph_collection import (
    GRAPH_MANIFEST_FILENAME,
    entry_id_from_source_uri,
    graph_manifest_path,
    load_graph_manifest,
    record_graph_manifest_error,
    record_graph_manifest_success,
    resolve_graph_artifacts,
)
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


def test_entry_id_from_source_uri_web() -> None:
    url = "https://doa.gov.lk/sinhala-hordi-crop-cabbage/"
    assert entry_id_from_source_uri(url) == "doa-gov-lk-sinhala-hordi-crop-cabbage"


def test_resolve_graph_artifacts_paths(tmp_path: Path) -> None:
    url = "https://doa.gov.lk/sinhala-hordi-crop-cabbage/"
    artifacts = resolve_graph_artifacts(tmp_path, url)
    assert artifacts.html_output_path == tmp_path / "graph_html" / "doa-gov-lk-sinhala-hordi-crop-cabbage.html"
    assert artifacts.json_output_path == tmp_path / "graph_json" / "doa-gov-lk-sinhala-hordi-crop-cabbage.json"


def test_record_graph_manifest_success_writes_manifest(tmp_path: Path) -> None:
    url = "https://doa.gov.lk/sinhala-hordi-crop-cabbage/"
    artifacts = resolve_graph_artifacts(tmp_path, url)
    artifacts.json_output_path.parent.mkdir(parents=True)
    artifacts.json_output_path.write_text("{}", encoding="utf-8")

    record_graph_manifest_success(
        tmp_path,
        source_uri=url,
        crop_name="ගෝවා",
        loader="doa_hordi",
        html_path=artifacts.html_output_path,
        json_path=artifacts.json_output_path,
        source_id=7,
        graph_status=KNOWLEDGE_SOURCE_STATUS_GRAPH_INDEXED,
    )

    manifest = load_graph_manifest(graph_manifest_path(tmp_path))
    assert manifest["version"] == 1
    assert len(manifest["entries"]) == 1
    entry = manifest["entries"][0]
    assert entry["url"] == url
    assert entry["crop_name"] == "ගෝවා"
    assert entry["status"] == "ok"
    assert entry["source_id"] == 7
    assert entry["json_path"].startswith("graph_json/")


def test_record_graph_manifest_error_includes_json_when_present(tmp_path: Path) -> None:
    url = "https://doa.gov.lk/sinhala-hordi-crop-cabbage/"
    artifacts = resolve_graph_artifacts(tmp_path, url)
    artifacts.json_output_path.parent.mkdir(parents=True)
    artifacts.json_output_path.write_text('{"crop_name": "ගෝවා"}', encoding="utf-8")

    record_graph_manifest_error(
        tmp_path,
        source_uri=url,
        crop_name="ගෝවා",
        loader="doa_hordi",
        error="neo4j down",
        json_path=artifacts.json_output_path,
    )

    manifest = load_graph_manifest(graph_manifest_path(tmp_path))
    entry = manifest["entries"][0]
    assert entry["status"] == "error"
    assert entry["error"] == "neo4j down"
    assert entry["json_path"].endswith(".json")


def test_ingest_graph_manifest_entry_records_manifest_on_success(
    tmp_path: Path,
    source_repository,
) -> None:
    service = MagicMock()
    json_path = resolve_graph_artifacts(tmp_path, "https://doa.gov.lk/cabbage/").json_output_path
    service.ingest.return_value = GraphIngestResult(
        source_id=3,
        crop_name="ගෝවා",
        status=KNOWLEDGE_SOURCE_STATUS_GRAPH_INDEXED,
        json_path=json_path,
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
        collection_dir=tmp_path,
        save_artifacts=True,
    )

    assert result.outcome == "ok"
    manifest = json.loads((tmp_path / GRAPH_MANIFEST_FILENAME).read_text(encoding="utf-8"))
    assert manifest["entries"][0]["source_id"] == 3


def test_extracted_crop_knowledge_serializes_nested_models() -> None:
    from app.domains.graph.serialization import extracted_crop_knowledge_to_dict

    extracted = ExtractedCropKnowledge(
        crop_name="Pepper",
        pests=[Pest(name="Aphid", impact="leaf curl", solution="soap spray")],
    )
    payload = extracted_crop_knowledge_to_dict(extracted)
    assert payload["crop_name"] == "Pepper"
    assert payload["pests"][0]["name"] == "Aphid"
