from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievedChunk:
    """Immutable value object representing a chunk returned from the vector store."""

    chunk_id: str
    text_content: str
    section_name: str
    crop_tag: str


@dataclass
class AnswerResult:
    """Domain result of a completed RAG inference run."""

    text: str
    sources: list[RetrievedChunk]
