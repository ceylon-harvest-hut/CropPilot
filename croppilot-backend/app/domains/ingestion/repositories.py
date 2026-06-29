from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.domains.ingestion.data import KnowledgeChunk
from app.domains.vector.repositories import VectorWriteRepository as VectorStoreRepository

__all__ = ["ChunkEmbeddingService", "VectorStoreRepository", "ExistingSourceInfo", "KnowledgeSourceRepository"]


class ChunkEmbeddingService(Protocol):
    def embed(self, chunks: list[KnowledgeChunk]) -> list[KnowledgeChunk]: ...


@dataclass
class ExistingSourceInfo:
    source_id: int
    status: str
    crop_names: list[str]


class KnowledgeSourceRepository(Protocol):
    def create_pending(self, origin_url: str, crop_name: str) -> int: ...

    def find_by_origin_url(self, origin_url: str) -> ExistingSourceInfo | None: ...

    def prepare_for_reingest(self, origin_url: str, crop_name: str) -> int: ...

    def update_status(self, source_id: int, status: str) -> None: ...

    def reset_graph_indexed_sources(self) -> int: ...
