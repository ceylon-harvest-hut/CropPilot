from pathlib import Path

import pytest

from app.domains.ingestion.data import ChunkEmbedding, ChunkMetadata, KnowledgeChunk
from app.infrastructure.repositories.chroma_store import ChromaVectorStore


@pytest.fixture
def store(tmp_path: Path) -> ChromaVectorStore:
    s = ChromaVectorStore(persist_directory=str(tmp_path / "chroma"))

    chunks = [
        KnowledgeChunk(
            chunk_id="cp-1",
            text_content="Pepper is cultivated in tropical climates.",
            metadata=ChunkMetadata(section_name="Introduction", page_number=0, crop_tag="Pepper"),
        ),
        KnowledgeChunk(
            chunk_id="cp-2",
            text_content="Black pepper grows on vines and needs high humidity.",
            metadata=ChunkMetadata(section_name="Cultivation", page_number=1, crop_tag="Pepper"),
        ),
        KnowledgeChunk(
            chunk_id="tm-1",
            text_content="Tomato is a warm-season vegetable crop.",
            metadata=ChunkMetadata(section_name="Introduction", page_number=0, crop_tag="Tomato"),
        ),
    ]
    for i, chunk in enumerate(chunks):
        chunk.update_embedding(ChunkEmbedding(vector=[float(i), float(i + 1), float(i + 2)]))

    s.upsert(chunks[:2], source_uri="pepper.txt")
    s.upsert(chunks[2:], source_uri="tomato.txt")
    return s


def test_list_all_returns_all_chunks(store: ChromaVectorStore) -> None:
    chunks, total = store.list_chunks()
    assert total == 3
    assert len(chunks) == 3


def test_list_filter_by_crop_tag(store: ChromaVectorStore) -> None:
    chunks, total = store.list_chunks(crop_tag="Pepper")
    assert all(c.crop_tag == "Pepper" for c in chunks)
    assert len(chunks) == 2


def test_list_filter_by_source_uri(store: ChromaVectorStore) -> None:
    chunks, _ = store.list_chunks(source_uri="tomato.txt")
    assert len(chunks) == 1
    assert chunks[0].chunk_id == "tm-1"


def test_list_filter_by_both(store: ChromaVectorStore) -> None:
    chunks, _ = store.list_chunks(crop_tag="Pepper", source_uri="pepper.txt")
    assert len(chunks) == 2


def test_list_respects_limit(store: ChromaVectorStore) -> None:
    chunks, total = store.list_chunks(limit=2)
    assert len(chunks) == 2
    assert total == 3


def test_list_chunk_text_preview_is_truncated(store: ChromaVectorStore) -> None:
    long_text = "x" * 300
    from app.domains.ingestion.data import KnowledgeChunk, ChunkMetadata, ChunkEmbedding
    chunk = KnowledgeChunk(
        chunk_id="long-1",
        text_content=long_text,
        metadata=ChunkMetadata(section_name="Test", page_number=0, crop_tag="Test"),
    )
    chunk.update_embedding(ChunkEmbedding(vector=[9.0, 10.0, 11.0]))
    store.upsert([chunk], source_uri="test.txt")

    chunks, _ = store.list_chunks(crop_tag="Test")
    assert len(chunks[0].text_preview) == 150


def test_list_stored_chunk_fields(store: ChromaVectorStore) -> None:
    chunks, _ = store.list_chunks(crop_tag="Pepper", limit=1)
    c = chunks[0]
    assert c.chunk_id
    assert c.crop_tag == "Pepper"
    assert c.source_uri == "pepper.txt"
    assert c.section_name
    assert isinstance(c.page_number, int)
    assert c.text_preview
