from __future__ import annotations

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.infrastructure.llm.prompt_catalog import (
    DEFAULT_ASK_TEMPLATE,
    get_prompt_template,
    list_template_names,
)


def _build_chains(model) -> dict[str, object]:
    chains: dict[str, object] = {}
    for name in list_template_names():
        prompt = ChatPromptTemplate.from_template(get_prompt_template(name))
        chains[name] = prompt | model | StrOutputParser()
    return chains


class GeminiLlmService:
    def __init__(
        self,
        model_name: str,
        api_key: str,
        temperature: float = 0.2,
    ) -> None:
        from langchain_google_genai import ChatGoogleGenerativeAI

        self._chains = _build_chains(
            ChatGoogleGenerativeAI(
                model=model_name,
                api_key=api_key,
                temperature=temperature,
            )
        )

    def generate(
        self,
        question: str,
        context: str,
        template: str = DEFAULT_ASK_TEMPLATE,
    ) -> str:
        chain = self._chains[template]
        return chain.invoke({"question": question, "context": context})


class OllamaLlmService:
    def __init__(self, model_name: str) -> None:
        from langchain_ollama import ChatOllama

        self._chains = _build_chains(ChatOllama(model=model_name))

    def generate(
        self,
        question: str,
        context: str,
        template: str = DEFAULT_ASK_TEMPLATE,
    ) -> str:
        chain = self._chains[template]
        return chain.invoke({"question": question, "context": context})


class OpenAILlmService:
    def __init__(self, model_name: str, api_key: str | None = None) -> None:
        from langchain_openai import ChatOpenAI

        kwargs = {"model": model_name}
        if api_key is not None:
            kwargs["api_key"] = api_key
        self._chains = _build_chains(ChatOpenAI(**kwargs))

    def generate(
        self,
        question: str,
        context: str,
        template: str = DEFAULT_ASK_TEMPLATE,
    ) -> str:
        chain = self._chains[template]
        return chain.invoke({"question": question, "context": context})
