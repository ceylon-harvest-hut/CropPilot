from pathlib import Path

import pytest

from app.domains.ingestion.data import ChunkEmbedding, ChunkMetadata, KnowledgeChunk
from app.infrastructure.repositories.chroma_store import ChromaVectorStore


@pytest.fixture
def vector_store(tmp_path: Path) -> ChromaVectorStore:
    return ChromaVectorStore(persist_directory=str(tmp_path / "chroma"))


def _sample_chunk(text: str, chunk_id: str) -> KnowledgeChunk:
    chunk = KnowledgeChunk(
        chunk_id=chunk_id,
        text_content=text,
        metadata=ChunkMetadata(section_name="History", page_number=0, crop_tag="Pepper"),
    )
    chunk.update_embedding(ChunkEmbedding(vector=[0.1, 0.2, 0.3]))
    return chunk


def test_upsert_stores_chunks(vector_store: ChromaVectorStore) -> None:
    chunks = [
        _sample_chunk("Pepper is a spice.", "chunk-1"),
        _sample_chunk("Spacing is 2.4m x 2.4m.", "chunk-2"),
    ]

    vector_store.upsert(chunks, source_uri="tests/fixtures/pepper.txt")

    assert vector_store.count() == 2


def test_upsert_requires_embeddings(vector_store: ChromaVectorStore) -> None:
    chunk = KnowledgeChunk(
        text_content="Missing embedding.",
        metadata=ChunkMetadata(section_name="History", page_number=0, crop_tag="Pepper"),
    )

    with pytest.raises(ValueError, match="missing an embedding"):
        vector_store.upsert([chunk], source_uri="tests/fixtures/pepper.txt")
