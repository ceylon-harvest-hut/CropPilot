from __future__ import annotations

from abc import ABC, abstractmethod

from app.domains.ingestion.data import KnowledgeChunk


class BaseEmbedder(ABC):
    """Shared embedding contract for ingestion and retrieval."""

    @abstractmethod
    def embed(self, chunks: list[KnowledgeChunk]) -> list[KnowledgeChunk]: ...

    @abstractmethod
    def embed_text(self, text: str) -> list[float]: ...
