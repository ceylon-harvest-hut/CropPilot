from __future__ import annotations

from dataclasses import dataclass

from app.domains.ingestion.data import KnowledgeChunk
from app.domains.ingestion.repositories import KnowledgeSourceRepository, VectorStoreRepository
from app.infrastructure.repositories.db import (
    KNOWLEDGE_SOURCE_STATUS_INDEXED,
    KNOWLEDGE_SOURCE_STATUS_PROCESSING,
)


class SourceAlreadyIngestedError(Exception):
    def __init__(
        self,
        source_id: int,
        chunk_count: int,
        status: str,
        crop_names: list[str],
    ) -> None:
        self.source_id = source_id
        self.chunk_count = chunk_count
        self.status = status
        self.crop_names = crop_names
        super().__init__(f"Source already ingested: {source_id}")


@dataclass
class PersistResult:
    source_id: int
    chunk_count: int
    status: str
    replaced: bool = False
    previous_chunk_count: int = 0


def persist_knowledge_chunks(
    *,
    source_uri: str,
    crop_name: str,
    chunks: list[KnowledgeChunk],
    vector_store: VectorStoreRepository,
    source_repository: KnowledgeSourceRepository,
    replace_existing: bool,
) -> PersistResult:
    existing = source_repository.find_by_origin_url(source_uri)
    previous_chunk_count = 0
    replaced = False

    if existing is not None:
        previous_chunk_count = vector_store.count_by_source_uri(source_uri)
        if not replace_existing:
            raise SourceAlreadyIngestedError(
                source_id=existing.source_id,
                chunk_count=previous_chunk_count,
                status=existing.status,
                crop_names=existing.crop_names,
            )
        vector_store.delete_by_source_uri(source_uri)
        replaced = True
        source_id = source_repository.prepare_for_reingest(source_uri, crop_name)
    else:
        source_id = source_repository.create_pending(source_uri, crop_name)

    source_repository.update_status(source_id, KNOWLEDGE_SOURCE_STATUS_PROCESSING)
    vector_store.upsert(chunks, source_uri=source_uri)
    source_repository.update_status(source_id, KNOWLEDGE_SOURCE_STATUS_INDEXED)

    return PersistResult(
        source_id=source_id,
        chunk_count=len(chunks),
        status=KNOWLEDGE_SOURCE_STATUS_INDEXED,
        replaced=replaced,
        previous_chunk_count=previous_chunk_count,
    )
