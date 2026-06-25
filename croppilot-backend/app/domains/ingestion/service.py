from __future__ import annotations

from app.domains.ingestion.chunker import BaseChunker
from app.domains.ingestion.data import IngestResult
from app.domains.ingestion.repositories import (
    ChunkEmbeddingService,
    KnowledgeSourceRepository,
    VectorStoreRepository,
)
from app.infrastructure.loaders.registry import DocumentLoaderRegistry
from app.infrastructure.repositories.db import (
    KNOWLEDGE_SOURCE_STATUS_FAILED,
    KNOWLEDGE_SOURCE_STATUS_INDEXED,
    KNOWLEDGE_SOURCE_STATUS_PROCESSING,
)


class IngestionService:
    def __init__(
        self,
        loader_registry: DocumentLoaderRegistry,
        chunker: BaseChunker,
        embedder: ChunkEmbeddingService,
        vector_store: VectorStoreRepository,
        source_repository: KnowledgeSourceRepository,
    ) -> None:
        self._loaders = loader_registry
        self._chunker = chunker
        self._embedder = embedder
        self._vector_store = vector_store
        self._source_repository = source_repository

    def ingest(self, source_uri: str, crop_tag: str) -> IngestResult:
        source_id = self._source_repository.create_pending(source_uri, crop_tag)

        try:
            self._source_repository.update_status(source_id, KNOWLEDGE_SOURCE_STATUS_PROCESSING)

            documents = self._loaders.resolve(source_uri).load(source_uri)
            chunks = self._chunker.chunk(documents, crop_tag=crop_tag)
            chunks = self._embedder.embed(chunks)
            self._vector_store.upsert(chunks, source_uri=source_uri)

            self._source_repository.update_status(source_id, KNOWLEDGE_SOURCE_STATUS_INDEXED)
            return IngestResult(
                source_id=source_id,
                chunk_count=len(chunks),
                status=KNOWLEDGE_SOURCE_STATUS_INDEXED,
            )
        except Exception:
            self._source_repository.update_status(source_id, KNOWLEDGE_SOURCE_STATUS_FAILED)
            raise
