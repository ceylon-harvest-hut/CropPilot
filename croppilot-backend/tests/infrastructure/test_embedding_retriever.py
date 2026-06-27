"""Tests for EmbeddingRetriever with mocked ports."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.domains.inference.data import RetrievedChunk
from app.infrastructure.repositories.embedding_retriever import EmbeddingRetriever


def _make_chunk(n: int) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=f"c{n}",
        text_content=f"Chunk content {n}.",
        section_name="History",
        crop_tag="Pepper",
        source_uri="https://dea.gov.lk/pepper/",
    )


def test_retriever_embeds_question_and_calls_search() -> None:
    embedder = MagicMock()
    embedder.embed_text.return_value = [0.1, 0.2, 0.3]

    store = MagicMock()
    store.search.return_value = [_make_chunk(1), _make_chunk(2)]

    retriever = EmbeddingRetriever(embedder=embedder, store=store)
    results = retriever.search("What are pepper varieties?", crop_tag="Pepper", k=2)

    embedder.embed_text.assert_called_once_with("What are pepper varieties?")
    store.search.assert_called_once_with([0.1, 0.2, 0.3], crop_tag="Pepper", k=2)
    assert len(results) == 2
    assert results[0].chunk_id == "c1"


def test_retriever_passes_crop_tag_none() -> None:
    embedder = MagicMock()
    embedder.embed_text.return_value = [0.0]

    store = MagicMock()
    store.search.return_value = []

    retriever = EmbeddingRetriever(embedder=embedder, store=store)
    retriever.search("General question", crop_tag=None)

    store.search.assert_called_once_with([0.0], crop_tag=None, k=3)


def test_retriever_returns_retrieved_chunks() -> None:
    embedder = MagicMock()
    embedder.embed_text.return_value = [0.5]

    chunks = [_make_chunk(i) for i in range(3)]
    store = MagicMock()
    store.search.return_value = chunks

    retriever = EmbeddingRetriever(embedder=embedder, store=store)
    results = retriever.search("Question", crop_tag="Pepper")

    assert results == chunks
    assert all(isinstance(r, RetrievedChunk) for r in results)
