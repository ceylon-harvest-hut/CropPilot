"""Run extract → load → chunk → embed → persist for a single manifest entry."""

from __future__ import annotations

from dataclasses import dataclass

from app.domains.ingestion.chunker import BaseChunker
from app.domains.ingestion.content import ExtractOptions
from app.domains.ingestion.persistence import SourceAlreadyIngestedError, persist_knowledge_chunks
from app.domains.ingestion.pipeline import DocumentPipeline
from app.domains.ingestion.repositories import (
    ChunkEmbeddingService,
    KnowledgeSourceRepository,
    VectorStoreRepository,
)
from app.infrastructure.ingestion.batch_manifest import ManifestEntry
from app.infrastructure.repositories.db import KNOWLEDGE_SOURCE_STATUS_FAILED


@dataclass(frozen=True)
class BatchIngestItemResult:
    source_uri: str
    crop_name: str
    outcome: str  # ok | skipped | error
    source_id: int | None = None
    chunk_count: int = 0
    message: str = ""


def ingest_manifest_entry(
    entry: ManifestEntry,
    *,
    pipeline: DocumentPipeline,
    loader: str,
    chunker: BaseChunker,
    embedder: ChunkEmbeddingService,
    vector_store: VectorStoreRepository,
    source_repository: KnowledgeSourceRepository,
    replace_existing: bool = False,
    skip_existing: bool = False,
    extract_options: ExtractOptions | None = None,
) -> BatchIngestItemResult:
    source_type = entry.resolved_source_type()

    if skip_existing and not replace_existing:
        existing = source_repository.find_by_origin_url(entry.source_uri)
        if existing is not None:
            return BatchIngestItemResult(
                source_uri=entry.source_uri,
                crop_name=entry.crop_name,
                outcome="skipped",
                source_id=existing.source_id,
                chunk_count=vector_store.count_by_source_uri(entry.source_uri),
                message="already ingested",
            )

    try:
        documents = pipeline.load_documents(
            entry.source_uri,
            source_type,
            loader,
            extract_options=extract_options,
        )
        chunks = chunker.chunk(documents, crop_tag=entry.crop_name)
        chunks = embedder.embed(chunks)

        result = persist_knowledge_chunks(
            source_uri=entry.source_uri,
            crop_name=entry.crop_name,
            chunks=chunks,
            vector_store=vector_store,
            source_repository=source_repository,
            replace_existing=replace_existing,
        )
        return BatchIngestItemResult(
            source_uri=entry.source_uri,
            crop_name=entry.crop_name,
            outcome="ok",
            source_id=result.source_id,
            chunk_count=result.chunk_count,
            message="replaced" if result.replaced else "indexed",
        )
    except SourceAlreadyIngestedError as exc:
        if skip_existing:
            return BatchIngestItemResult(
                source_uri=entry.source_uri,
                crop_name=entry.crop_name,
                outcome="skipped",
                source_id=exc.source_id,
                chunk_count=exc.chunk_count,
                message="already ingested",
            )
        return BatchIngestItemResult(
            source_uri=entry.source_uri,
            crop_name=entry.crop_name,
            outcome="error",
            message=str(exc),
        )
    except Exception as exc:
        existing = source_repository.find_by_origin_url(entry.source_uri)
        if existing is not None:
            source_repository.update_status(existing.source_id, KNOWLEDGE_SOURCE_STATUS_FAILED)
        return BatchIngestItemResult(
            source_uri=entry.source_uri,
            crop_name=entry.crop_name,
            outcome="error",
            message=str(exc),
        )
