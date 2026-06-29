"""Run extract → load → LLM extract → Neo4j persist for a single manifest entry."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.domains.graph.data import GraphIngestArtifacts
from app.domains.graph.persistence import SourceAlreadyGraphIngestedError
from app.domains.graph.service import GraphIngestionService
from app.domains.ingestion.repositories import KnowledgeSourceRepository
from app.infrastructure.graph.graph_collection import (
    ensure_graph_collection_dirs,
    record_graph_manifest_error,
    record_graph_manifest_success,
    resolve_graph_artifacts,
)
from app.infrastructure.ingestion.batch_manifest import ManifestEntry
from app.infrastructure.repositories.db import KNOWLEDGE_SOURCE_STATUS_GRAPH_INDEXED
from app.shared.document.content import ExtractOptions


@dataclass(frozen=True)
class BatchGraphIngestItemResult:
    source_uri: str
    crop_name: str
    outcome: str  # ok | skipped | error
    source_id: int | None = None
    message: str = ""
    replaced: bool = False
    html_path: str = ""
    json_path: str = ""


def ingest_graph_manifest_entry(
    entry: ManifestEntry,
    *,
    service: GraphIngestionService,
    source_repository: KnowledgeSourceRepository,
    loader: str,
    replace_existing: bool = False,
    skip_existing: bool = False,
    extract_options: ExtractOptions | None = None,
    collection_dir: Path | None = None,
    save_artifacts: bool = False,
) -> BatchGraphIngestItemResult:
    artifacts: GraphIngestArtifacts | None = None
    if save_artifacts and collection_dir is not None:
        ensure_graph_collection_dirs(collection_dir)
        artifacts = resolve_graph_artifacts(collection_dir, entry.source_uri)

    if skip_existing and not replace_existing:
        existing = source_repository.find_by_origin_url(entry.source_uri)
        if existing is not None and existing.status == KNOWLEDGE_SOURCE_STATUS_GRAPH_INDEXED:
            return BatchGraphIngestItemResult(
                source_uri=entry.source_uri,
                crop_name=entry.crop_name,
                outcome="skipped",
                source_id=existing.source_id,
                message="already graph-ingested",
            )

    try:
        result = service.ingest(
            entry.source_uri,
            entry.crop_name,
            source_type=entry.resolved_source_type(),
            loader=loader,
            replace_existing=replace_existing,
            extract_options=extract_options,
            artifacts=artifacts,
        )
        if save_artifacts and collection_dir is not None:
            record_graph_manifest_success(
                collection_dir,
                source_uri=entry.source_uri,
                crop_name=entry.crop_name,
                loader=loader,
                html_path=result.html_path,
                json_path=result.json_path,
                source_id=result.source_id,
                graph_status=result.status,
            )
        return BatchGraphIngestItemResult(
            source_uri=entry.source_uri,
            crop_name=entry.crop_name,
            outcome="ok",
            source_id=result.source_id,
            message="replaced" if result.replaced else "graph-indexed",
            replaced=result.replaced,
            html_path=str(result.html_path or ""),
            json_path=str(result.json_path or ""),
        )
    except SourceAlreadyGraphIngestedError as exc:
        if skip_existing:
            return BatchGraphIngestItemResult(
                source_uri=entry.source_uri,
                crop_name=entry.crop_name,
                outcome="skipped",
                source_id=exc.source_id,
                message="already graph-ingested",
            )
        return BatchGraphIngestItemResult(
            source_uri=entry.source_uri,
            crop_name=entry.crop_name,
            outcome="error",
            source_id=exc.source_id,
            message=str(exc),
        )
    except Exception as exc:
        if save_artifacts and collection_dir is not None and artifacts is not None:
            record_graph_manifest_error(
                collection_dir,
                source_uri=entry.source_uri,
                crop_name=entry.crop_name,
                loader=loader,
                error=str(exc),
                html_path=artifacts.html_output_path,
                json_path=artifacts.json_output_path,
            )
        return BatchGraphIngestItemResult(
            source_uri=entry.source_uri,
            crop_name=entry.crop_name,
            outcome="error",
            message=str(exc),
        )
