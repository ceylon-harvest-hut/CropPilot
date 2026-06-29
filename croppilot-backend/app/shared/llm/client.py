from __future__ import annotations

from typing import Protocol, TypeVar

from app.shared.llm.errors import LlmApiErrorInfo

T = TypeVar("T")


class LlmClient(Protocol):
    def generate(
        self,
        question: str,
        context: str,
        template: str = "context_only",
    ) -> str: ...

    def structured_invoke(
        self,
        messages: list[tuple[str, str]],
        schema: type[T],
        *,
        variables: dict[str, object] | None = None,
    ) -> T: ...

    def interpret_api_error(self, exc: BaseException) -> LlmApiErrorInfo: ...
