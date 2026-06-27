from __future__ import annotations

from app.domains.inference.data import AnswerResult
from app.domains.inference.references import build_rag_context
from app.domains.inference.repositories import LlmService, RetrieverRepository


class InferenceService:
    def __init__(
        self,
        retriever: RetrieverRepository,
        llm: LlmService,
        top_k: int = 3,
    ) -> None:
        self._retriever = retriever
        self._llm = llm
        self._top_k = top_k

    def ask(
        self,
        question: str,
        crop_tag: str | None = None,
        template: str = "context_only",
    ) -> AnswerResult:
        chunks = self._retriever.search(question, crop_tag=crop_tag, k=self._top_k)
        context, references = build_rag_context(chunks)
        text = self._llm.generate(question, context, template=template)
        return AnswerResult(text=text, references=references)
