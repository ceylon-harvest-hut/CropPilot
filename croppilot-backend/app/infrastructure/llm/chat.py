from __future__ import annotations

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.infrastructure.llm.prompts import CROP_RAG_PROMPT


def _build_chain(model):
    prompt = ChatPromptTemplate.from_template(CROP_RAG_PROMPT)
    return prompt | model | StrOutputParser()


class GeminiLlmService:
    def __init__(self, model_name: str, temperature: float = 0.2) -> None:
        from langchain_google_genai import ChatGoogleGenerativeAI

        self._chain = _build_chain(
            ChatGoogleGenerativeAI(model=model_name, temperature=temperature)
        )

    def generate(self, question: str, context: str) -> str:
        return self._chain.invoke({"question": question, "context": context})


class OllamaLlmService:
    def __init__(self, model_name: str) -> None:
        from langchain_ollama import ChatOllama

        self._chain = _build_chain(ChatOllama(model=model_name))

    def generate(self, question: str, context: str) -> str:
        return self._chain.invoke({"question": question, "context": context})


class OpenAILlmService:
    def __init__(self, model_name: str) -> None:
        from langchain_openai import ChatOpenAI

        self._chain = _build_chain(ChatOpenAI(model=model_name))

    def generate(self, question: str, context: str) -> str:
        return self._chain.invoke({"question": question, "context": context})
