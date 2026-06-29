from __future__ import annotations

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.domains.ingestion.chunker import BaseChunker
from app.domains.ingestion.data import KnowledgeChunk
from app.shared.document.loader import KnowledgeDocument


class RecursiveChunker(BaseChunker):
    """Split each document using LangChain's RecursiveCharacterTextSplitter.

    Page number is inherited from the document's ``page`` metadata key.
    """

    def __init__(self, chunk_size: int, chunk_overlap: int) -> None:
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def chunk(
        self,
        documents: list[KnowledgeDocument],
        crop_tag: str,
    ) -> list[KnowledgeChunk]:
        chunks: list[KnowledgeChunk] = []
        for doc in documents:
            page = int(doc.metadata.get("page", 0))
            parts = self._splitter.split_text(doc.text)
            for i, part in enumerate(parts):
                chunks.append(
                    KnowledgeChunk(
                        text_content=part,
                        metadata={
                            "crop_tag": crop_tag,
                            "section_name": f"chunk_{i}",
                            "page_number": page,
                        },
                    )
                )
        return chunks
