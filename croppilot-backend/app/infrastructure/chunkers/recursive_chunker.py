from __future__ import annotations

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.domains.ingestion.data import ChunkMetadata, KnowledgeChunk


class RecursiveChunkingStrategy:
    def __init__(self, chunk_size: int, chunk_overlap: int) -> None:
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def split(self, text: str, crop_tag: str) -> list[KnowledgeChunk]:
        parts = self._splitter.split_text(text)
        return [
            KnowledgeChunk(
                text_content=part,
                metadata=ChunkMetadata(
                    section_name=f"chunk_{index}",
                    page_number=0,
                    crop_tag=crop_tag,
                ),
            )
            for index, part in enumerate(parts)
        ]