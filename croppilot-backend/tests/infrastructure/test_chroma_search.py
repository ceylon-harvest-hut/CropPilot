from pathlib import Path

import pytest

from app.domains.ingestion.data import ChunkEmbedding, ChunkMetadata, KnowledgeChunk
from app.infrastructure.repositories.chroma_store import ChromaVectorStore

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def store_with_chunks(tmp_path: Path) -> ChromaVectorStore:
    store = ChromaVectorStore(persist_directory=str(tmp_path / "chroma"))

    chunks = [
        KnowledgeChunk(
            chunk_id="chunk-pepper-1",
            text_content="Pepper is cultivated in tropical climates.",
            metadata=ChunkMetadata(section_name="Introduction", page_number=0, crop_tag="Pepper"),
        ),
        KnowledgeChunk(
            chunk_id="chunk-pepper-2",
            text_content="Black pepper grows on vines and needs high humidity.",
            metadata=ChunkMetadata(section_name="Cultivation", page_number=1, crop_tag="Pepper"),
        ),
        KnowledgeChunk(
            chunk_id="chunk-tomato-1",
            text_content="Tomato is a warm-season vegetable crop.",
            metadata=ChunkMetadata(section_name="Introduction", page_number=0, crop_tag="Tomato"),
        ),
    ]
    # Use a small deterministic embedding so Chroma can compute distances.
    for i, chunk in enumerate(chunks):
        chunk.update_embedding(ChunkEmbedding(vector=[float(i), float(i + 1), float(i + 2)]))

    store.upsert(chunks, source_uri="tests/fixtures/pepper.txt")
    return store


def test_search_returns_results(store_with_chunks: ChromaVectorStore) -> None:
    results = store_with_chunks.search(query_embedding=[0.0, 1.0, 2.0], crop_tag=None, k=2)
    assert len(results) == 2


def test_search_filters_by_crop_tag(store_with_chunks: ChromaVectorStore) -> None:
    results = store_with_chunks.search(query_embedding=[0.0, 1.0, 2.0], crop_tag="Pepper", k=3)
    assert all(r.crop_tag == "Pepper" for r in results)
    assert len(results) == 2


def test_search_result_fields(store_with_chunks: ChromaVectorStore) -> None:
    results = store_with_chunks.search(query_embedding=[0.0, 1.0, 2.0], crop_tag=None, k=1)
    chunk = results[0]
    assert chunk.chunk_id
    assert chunk.text_content
    assert chunk.section_name
    assert chunk.crop_tag
