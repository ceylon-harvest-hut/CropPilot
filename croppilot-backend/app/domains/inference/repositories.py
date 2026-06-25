from __future__ import annotations

from typing import Protocol

from app.domains.inference.data import RetrievedChunk


class QueryEmbeddingService(Protocol):
    def embed_text(self, text: str) -> list[float]: ...


class RetrieverRepository(Protocol):
    def search(
        self,
        question: str,
        crop_tag: str | None,
        k: int = 3,
    ) -> list[RetrievedChunk]: ...


class LlmService(Protocol):
    def generate(self, question: str, context: str) -> str: ...
