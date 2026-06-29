from __future__ import annotations

from typing import TypeVar

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.infrastructure.llm.gemini_api_errors import interpret_gemini_api_error
from app.infrastructure.llm.prompt_catalog import (
    DEFAULT_ASK_TEMPLATE,
    get_prompt_template,
    list_template_names,
)
from app.shared.llm.errors import LlmApiErrorInfo

T = TypeVar("T")


def _build_chains(model) -> dict[str, object]:
    chains: dict[str, object] = {}
    for name in list_template_names():
        prompt = ChatPromptTemplate.from_template(get_prompt_template(name))
        chains[name] = prompt | model | StrOutputParser()
    return chains


def _default_error_info(exc: BaseException) -> LlmApiErrorInfo:
    return LlmApiErrorInfo(retryable=False, reason=str(exc))


class GeminiLlmClient:
    def __init__(
        self,
        model_name: str,
        api_key: str,
        temperature: float = 0.2,
    ) -> None:
        from langchain_google_genai import ChatGoogleGenerativeAI

        self._model = ChatGoogleGenerativeAI(
            model=model_name,
            api_key=api_key,
            temperature=temperature,
        )
        self._chains = _build_chains(self._model)

    def generate(
        self,
        question: str,
        context: str,
        template: str = DEFAULT_ASK_TEMPLATE,
    ) -> str:
        chain = self._chains[template]
        return chain.invoke({"question": question, "context": context})

    def structured_invoke(
        self,
        messages: list[tuple[str, str]],
        schema: type[T],
        *,
        variables: dict[str, object] | None = None,
    ) -> T:
        structured_llm = self._model.with_structured_output(schema)
        prompt = ChatPromptTemplate.from_messages(messages)
        chain = prompt | structured_llm
        return chain.invoke(variables or {})

    def interpret_api_error(self, exc: BaseException) -> LlmApiErrorInfo:
        return interpret_gemini_api_error(exc)


class OllamaLlmClient:
    def __init__(self, model_name: str) -> None:
        from langchain_ollama import ChatOllama

        self._model = ChatOllama(model=model_name)
        self._chains = _build_chains(self._model)

    def generate(
        self,
        question: str,
        context: str,
        template: str = DEFAULT_ASK_TEMPLATE,
    ) -> str:
        chain = self._chains[template]
        return chain.invoke({"question": question, "context": context})

    def structured_invoke(
        self,
        messages: list[tuple[str, str]],
        schema: type[T],
        *,
        variables: dict[str, object] | None = None,
    ) -> T:
        structured_llm = self._model.with_structured_output(schema)
        prompt = ChatPromptTemplate.from_messages(messages)
        chain = prompt | structured_llm
        return chain.invoke(variables or {})

    def interpret_api_error(self, exc: BaseException) -> LlmApiErrorInfo:
        return _default_error_info(exc)


class OpenAILlmClient:
    def __init__(self, model_name: str, api_key: str | None = None) -> None:
        from langchain_openai import ChatOpenAI

        kwargs = {"model": model_name}
        if api_key is not None:
            kwargs["api_key"] = api_key
        self._model = ChatOpenAI(**kwargs)
        self._chains = _build_chains(self._model)

    def generate(
        self,
        question: str,
        context: str,
        template: str = DEFAULT_ASK_TEMPLATE,
    ) -> str:
        chain = self._chains[template]
        return chain.invoke({"question": question, "context": context})

    def structured_invoke(
        self,
        messages: list[tuple[str, str]],
        schema: type[T],
        *,
        variables: dict[str, object] | None = None,
    ) -> T:
        structured_llm = self._model.with_structured_output(schema)
        prompt = ChatPromptTemplate.from_messages(messages)
        chain = prompt | structured_llm
        return chain.invoke(variables or {})

    def interpret_api_error(self, exc: BaseException) -> LlmApiErrorInfo:
        return _default_error_info(exc)


# Backward-compatible aliases
GeminiLlmService = GeminiLlmClient
OllamaLlmService = OllamaLlmClient
OpenAILlmService = OpenAILlmClient
