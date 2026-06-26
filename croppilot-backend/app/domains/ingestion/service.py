from __future__ import annotations

from app.domains.ingestion.chunker import BaseChunker
from app.domains.ingestion.data import IngestResult
from app.domains.ingestion.persistence import SourceAlreadyIngestedError, persist_knowledge_chunks
from app.domains.ingestion.repositories import (
    ChunkEmbeddingService,
    KnowledgeSourceRepository,
    VectorStoreRepository,
)
from app.domains.ingestion.source_types import infer_source_type
from app.infrastructure.loaders.registry import DocumentLoaderRegistry
from app.infrastructure.repositories.db import KNOWLEDGE_SOURCE_STATUS_FAILED


class IngestionService:
    def __init__(
        self,
        loader_registry: DocumentLoaderRegistry,
        chunker: BaseChunker,
        embedder: ChunkEmbeddingService,
        vector_store: VectorStoreRepository,
        source_repository: KnowledgeSourceRepository,
        default_loader: str,
    ) -> None:
        self._loaders = loader_registry
        self._chunker = chunker
        self._embedder = embedder
        self._vector_store = vector_store
        self._source_repository = source_repository
        self._default_loader = default_loader

    def ingest(
        self,
        source_uri: str,
        crop_tag: str,
        *,
        source_type: str | None = None,
        loader: str | None = None,
        replace_existing: bool = False,
    ) -> IngestResult:
        resolved_source_type = source_type or infer_source_type(source_uri)
        resolved_loader = loader or self._default_loader

        try:
            document_loader = self._loaders.resolve(
                resolved_loader,
                source_uri,
                resolved_source_type,
            )
            documents = document_loader.load(source_uri, resolved_source_type)
            chunks = self._chunker.chunk(documents, crop_tag=crop_tag)
            chunks = self._embedder.embed(chunks)

            result = persist_knowledge_chunks(
                source_uri=source_uri,
                crop_name=crop_tag,
                chunks=chunks,
                vector_store=self._vector_store,
                source_repository=self._source_repository,
                replace_existing=replace_existing,
            )
            return IngestResult(
                source_id=result.source_id,
                chunk_count=result.chunk_count,
                status=result.status,
            )
        except SourceAlreadyIngestedError:
            raise
        except Exception:
            existing = self._source_repository.find_by_origin_url(source_uri)
            if existing is not None:
                self._source_repository.update_status(existing.source_id, KNOWLEDGE_SOURCE_STATUS_FAILED)
            raise
