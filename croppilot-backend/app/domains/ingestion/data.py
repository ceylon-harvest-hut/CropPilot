from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional
from uuid import uuid4


@dataclass(frozen=True)
class ChunkMetadata:
    """Immutable value object for hybrid vector filtering context."""

    section_name: str
    page_number: int
    crop_tag: str


@dataclass(frozen=True)
class ChunkEmbedding:
    """Immutable value object holding vector coordinates."""

    vector: List[float]


@dataclass
class IngestResult:
    """Domain result of a completed ingestion run."""

    source_id: int
    chunk_count: int
    status: str


@dataclass
class KnowledgeChunk:
    """Domain object representing a text slice with optional embedding."""

    text_content: str
    metadata: ChunkMetadata
    chunk_id: str = field(default_factory=lambda: str(uuid4()))
    embedding: Optional[ChunkEmbedding] = None

    def update_embedding(self, embedding: ChunkEmbedding) -> None:
        """Assign vector coordinates safely to this chunk."""
        self.embedding = embedding
