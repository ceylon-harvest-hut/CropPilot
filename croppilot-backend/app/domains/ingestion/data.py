from __future__ import annotations

from typing import Any
from uuid import uuid4


class ChunkEmbedding:
    """Holds vector coordinates for a chunk."""

    def __init__(self, vector: list[float]) -> None:
        self.vector = vector


class KnowledgeChunk:
    """Domain object representing a text slice with optional embedding.

    Required metadata keys: crop_tag, section_name, page_number.
    """

    def __init__(
        self,
        text_content: str,
        metadata: dict[str, Any],
        chunk_id: str | None = None,
        embedding: ChunkEmbedding | None = None,
    ) -> None:
        self.text_content = text_content
        self.metadata = metadata
        self.chunk_id = chunk_id or str(uuid4())
        self.embedding = embedding

    def update_embedding(self, embedding: ChunkEmbedding) -> None:
        self.embedding = embedding

    @classmethod
    def from_payload(cls, text: str, metadata: dict[str, Any]) -> KnowledgeChunk:
        """Rehydrate from a lab API JSON payload."""
        return cls(text_content=text, metadata=metadata)


class IngestResult:
    """Domain result of a completed ingestion run."""

    def __init__(self, source_id: int, chunk_count: int, status: str) -> None:
        self.source_id = source_id
        self.chunk_count = chunk_count
        self.status = status
