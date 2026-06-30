from __future__ import annotations

from langchain_core.tools import StructuredTool

from app.domains.agent.data import AgentAnswerResult
from app.infrastructure.agent.langchain_agent_client import LangChainAgentClient


class OpenAIAgentClient:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        tools: list[StructuredTool],
    ) -> None:
        from langchain_openai import ChatOpenAI

        chat_model = ChatOpenAI(
            model=model,
            api_key=api_key,
            temperature=0.0,
        )
        self._client = LangChainAgentClient(chat_model, tools)

    def ask(self, question: str) -> AgentAnswerResult:
        return self._client.ask(question)
