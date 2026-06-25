from __future__ import annotations

from typing import Protocol

from app.domains.ingestion.data import KnowledgeChunk


class EmbeddingService(Protocol):
    def embed(self, chunks: list[KnowledgeChunk]) -> list[KnowledgeChunk]: ...


class VectorStoreRepository(Protocol):
    def upsert(self, chunks: list[KnowledgeChunk], source_uri: str) -> None: ...


class KnowledgeSourceRepository(Protocol):
    def create_pending(self, origin_url: str, crop_name: str) -> int: ...

    def update_status(self, source_id: int, status: str) -> None: ...
