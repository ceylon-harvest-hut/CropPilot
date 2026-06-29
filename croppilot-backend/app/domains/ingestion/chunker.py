from __future__ import annotations

from abc import ABC, abstractmethod

from app.domains.ingestion.data import KnowledgeChunk
from app.shared.document.loader import KnowledgeDocument


class BaseChunker(ABC):
    @abstractmethod
    def chunk(
        self,
        documents: list[KnowledgeDocument],
        crop_tag: str,
    ) -> list[KnowledgeChunk]: ...
