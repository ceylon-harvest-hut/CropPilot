from __future__ import annotations

from app.domains.inference.data import RetrievedChunk
from app.domains.inference.repositories import QueryEmbeddingService
from app.infrastructure.repositories.chroma_store import ChromaVectorStore


class ChromaRetriever:
    """Implements RetrieverRepository by composing embedding + vector store."""

    def __init__(
        self,
        embedder: QueryEmbeddingService,
        store: ChromaVectorStore,
    ) -> None:
        self._embedder = embedder
        self._store = store

    def search(
        self,
        question: str,
        crop_tag: str | None,
        k: int = 3,
    ) -> list[RetrievedChunk]:
        vector = self._embedder.embed_text(question)
        return self._store.search(vector, crop_tag=crop_tag, k=k)
