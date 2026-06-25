from __future__ import annotations

from fastembed import TextEmbedding

from app.domains.ingestion.data import ChunkEmbedding, KnowledgeChunk
from app.infrastructure.llm.base_embedder import BaseEmbedder


class FastEmbedEmbeddingService(BaseEmbedder):
    def __init__(self) -> None:
        self._model = TextEmbedding()

    def embed(self, chunks: list[KnowledgeChunk]) -> list[KnowledgeChunk]:
        if not chunks:
            return chunks

        vectors = self._model.embed(chunk.text_content for chunk in chunks)
        for chunk, vector in zip(chunks, vectors):
            chunk.update_embedding(ChunkEmbedding(vector=vector.tolist()))

        return chunks

    def embed_text(self, text: str) -> list[float]:
        return list(self._model.embed([text]))[0].tolist()
