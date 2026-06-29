"""Two-stage chunker for DeaGovLkLoader output.

Stage 1 — ``DeaGovLkChunker``: section boundaries and bold-header splits.
Stage 2 — recursive splitting with overlap on prose blocks that exceed
``max_chunk_size``.  Markdown tables are never split.
"""

from __future__ import annotations

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.domains.ingestion.chunker import BaseChunker
from app.domains.ingestion.data import KnowledgeChunk
from app.shared.document.loader import KnowledgeDocument
from app.infrastructure.chunkers.dea_gov_lk_chunker import (
    LONG_SECTION_THRESHOLD,
    DeaGovLkChunker,
)
from app.infrastructure.chunkers.dea_markdown import partition_prose_and_tables

DEFAULT_HYBRID_MAX_CHUNK_SIZE = 800


class DeaHybridChunker(BaseChunker):
    """DEA semantic chunking followed by size-limited recursive prose splits."""

    name = "dea_hybrid"

    def __init__(
        self,
        max_chunk_size: int = DEFAULT_HYBRID_MAX_CHUNK_SIZE,
        chunk_overlap: int = 50,
        long_section_threshold: int = LONG_SECTION_THRESHOLD,
    ) -> None:
        self._max_chunk_size = max_chunk_size
        self._dea = DeaGovLkChunker(long_section_threshold=long_section_threshold)
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=max_chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def chunk(
        self,
        documents: list[KnowledgeDocument],
        crop_tag: str,
    ) -> list[KnowledgeChunk]:
        initial = self._dea.chunk(documents, crop_tag)
        result: list[KnowledgeChunk] = []
        for chunk in initial:
            result.extend(_split_oversized_chunk(chunk, self._splitter, self._max_chunk_size))
        return result


def _split_oversized_chunk(
    chunk: KnowledgeChunk,
    splitter: RecursiveCharacterTextSplitter,
    max_chunk_size: int,
) -> list[KnowledgeChunk]:
    section = chunk.metadata.get("section_name", "")
    blocks = partition_prose_and_tables(chunk.text_content)
    if not blocks:
        return []

    output: list[KnowledgeChunk] = []
    part_num = 0

    for kind, block in blocks:
        if kind == "table":
            output.append(_clone_chunk(chunk, block, section))
            continue

        if len(block) <= max_chunk_size:
            output.append(_clone_chunk(chunk, block, section))
            continue

        parts = splitter.split_text(block)
        if len(parts) == 1:
            output.append(_clone_chunk(chunk, parts[0], section))
            continue

        for part in parts:
            part_num += 1
            output.append(_clone_chunk(chunk, part, f"{section} (part {part_num})"))

    return output


def _clone_chunk(source: KnowledgeChunk, text: str, section_name: str) -> KnowledgeChunk:
    return KnowledgeChunk(
        text_content=text.strip(),
        metadata={**source.metadata, "section_name": section_name},
    )
