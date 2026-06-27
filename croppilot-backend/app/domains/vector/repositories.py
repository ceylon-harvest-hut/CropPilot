"""Vector storage domain protocols.

These ports describe the operations that any vector backend must support.
``ChromaVectorStore`` is the only implementation today; future backends only
need to satisfy these interfaces and be wired in ``factories.build_vector_store``.
"""

from __future__ import annotations

from typing import Protocol

from app.domains.debug.data import StoredChunk
from app.domains.inference.data import RetrievedChunk
from app.domains.ingestion.data import KnowledgeChunk


class VectorWriteRepository(Protocol):
    """Write side: chunk persistence and lifecycle management."""

    def upsert(self, chunks: list[KnowledgeChunk], source_uri: str) -> None: ...

    def count_by_source_uri(self, source_uri: str) -> int: ...

    def delete_by_source_uri(self, source_uri: str) -> int: ...

    def count(self) -> int: ...


class VectorSearchRepository(Protocol):
    """Read side: embedding-based similarity search."""

    def search(
        self,
        query_embedding: list[float],
        crop_tag: str | None,
        k: int = 3,
    ) -> list[RetrievedChunk]: ...


class KnowledgeVectorRepository(VectorWriteRepository, VectorSearchRepository, Protocol):
    """Composite port: write + search + listing, used as the factory return type.

    Also satisfies ``ChunkCatalogRepository`` from the debug domain because it
    exposes ``list_chunks``.
    """

    def list_chunks(
        self,
        crop_tag: str | None,
        source_uri: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[StoredChunk], int]: ...
