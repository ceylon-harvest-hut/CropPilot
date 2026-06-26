from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.domains.ingestion.data import KnowledgeChunk


class ChunkEmbeddingService(Protocol):
    def embed(self, chunks: list[KnowledgeChunk]) -> list[KnowledgeChunk]: ...


class VectorStoreRepository(Protocol):
    def upsert(self, chunks: list[KnowledgeChunk], source_uri: str) -> None: ...

    def count_by_source_uri(self, source_uri: str) -> int: ...

    def delete_by_source_uri(self, source_uri: str) -> int: ...


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
