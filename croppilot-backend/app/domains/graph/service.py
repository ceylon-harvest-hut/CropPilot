from __future__ import annotations

from pathlib import Path

from app.domains.graph.artifacts import copy_file_html_to_artifact, save_extraction_json
from app.domains.graph.data import GraphIngestArtifacts, GraphIngestResult
from app.domains.graph.persistence import SourceAlreadyGraphIngestedError, persist_crop_graph
from app.domains.graph.repositories import GraphExtractionService, GraphWriteRepository
from app.domains.graph.text import prepare_extraction_text
from app.domains.ingestion.repositories import KnowledgeSourceRepository
from app.shared.document.content import ExtractOptions
from app.shared.document.pipeline import DocumentPipeline
from app.shared.document.source_types import SOURCE_TYPE_FILE, SOURCE_TYPE_WEB_URL, infer_source_type
from app.infrastructure.repositories.db import KNOWLEDGE_SOURCE_STATUS_FAILED


class GraphIngestionService:
    def __init__(
        self,
        pipeline: DocumentPipeline,
        extractor: GraphExtractionService,
        graph_store: GraphWriteRepository,
        source_repository: KnowledgeSourceRepository,
        default_loader: str,
    ) -> None:
        self._pipeline = pipeline
        self._extractor = extractor
        self._graph_store = graph_store
        self._source_repository = source_repository
        self._default_loader = default_loader

    def ingest(
        self,
        source_uri: str,
        manifest_crop_name: str | None = None,
        *,
        source_type: str | None = None,
        loader: str | None = None,
        replace_existing: bool = False,
        extract_options: ExtractOptions | None = None,
        artifacts: GraphIngestArtifacts | None = None,
    ) -> GraphIngestResult:
        resolved_source_type = source_type or infer_source_type(source_uri)
        resolved_loader = loader or self._default_loader
        resolved_extract_options = _merge_extract_options(
            extract_options,
            source_type=resolved_source_type,
            html_output_path=artifacts.html_output_path if artifacts else None,
        )

        saved_html_path: Path | None = None
        saved_json_path: Path | None = None

        try:
            documents = self._pipeline.load_documents(
                source_uri,
                resolved_source_type,
                resolved_loader,
                extract_options=resolved_extract_options,
            )
            if (
                artifacts
                and artifacts.html_output_path is not None
                and resolved_source_type == SOURCE_TYPE_FILE
            ):
                if copy_file_html_to_artifact(source_uri, artifacts.html_output_path):
                    saved_html_path = artifacts.html_output_path
            elif (
                artifacts
                and artifacts.html_output_path is not None
                and resolved_source_type == SOURCE_TYPE_WEB_URL
                and artifacts.html_output_path.is_file()
            ):
                saved_html_path = artifacts.html_output_path

            text = prepare_extraction_text(documents)
            extracted = self._extractor.extract(
                text,
                manifest_crop_name=manifest_crop_name,
                source_uri=source_uri,
            )

            if artifacts and artifacts.json_output_path is not None:
                save_extraction_json(extracted, artifacts.json_output_path)
                saved_json_path = artifacts.json_output_path

            result = persist_crop_graph(
                source_uri=source_uri,
                extracted=extracted,
                graph_store=self._graph_store,
                source_repository=self._source_repository,
                replace_existing=replace_existing,
                manifest_crop_name=manifest_crop_name,
            )
            return GraphIngestResult(
                source_id=result.source_id,
                crop_name=result.crop_name,
                status=result.status,
                replaced=result.replaced,
                html_path=saved_html_path,
                json_path=saved_json_path,
            )
        except SourceAlreadyGraphIngestedError:
            raise
        except Exception:
            existing = self._source_repository.find_by_origin_url(source_uri)
            if existing is not None:
                self._source_repository.update_status(
                    existing.source_id, KNOWLEDGE_SOURCE_STATUS_FAILED
                )
            raise

    def clear_graph_database(self) -> int:
        clear = getattr(self._graph_store, "clear_graph", None)
        if not callable(clear):
            raise NotImplementedError("Graph store does not support clear_graph()")
        return clear()

    def close(self) -> None:
        close = getattr(self._graph_store, "close", None)
        if callable(close):
            close()


def _merge_extract_options(
    extract_options: ExtractOptions | None,
    *,
    source_type: str,
    html_output_path: Path | None,
) -> ExtractOptions | None:
    if html_output_path is None or source_type != SOURCE_TYPE_WEB_URL:
        return extract_options

    base = extract_options or ExtractOptions()
    return ExtractOptions(
        timeout_seconds=base.timeout_seconds,
        max_bytes=base.max_bytes,
        persist_raw=True,
        raw_output_path=html_output_path,
    )
