"""Backend-agnostic retriever: embeds a question and delegates to the vector search port."""

from __future__ import annotations

from app.domains.inference.data import RetrievedChunk
from app.domains.inference.repositories import QueryEmbeddingService
from app.domains.vector.repositories import VectorSearchRepository


class EmbeddingRetriever:
    """Implements RetrieverRepository by composing an embedder with a VectorSearchRepository.

    No dependency on any concrete vector-store implementation.
    """

    def __init__(
        self,
        embedder: QueryEmbeddingService,
        store: VectorSearchRepository,
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
