from __future__ import annotations

from typing import Protocol

from app.domains.agent.data import AgentAnswerResult


class AgentClient(Protocol):
    def ask(self, question: str) -> AgentAnswerResult: ...


class AgentService:
    def __init__(self, client: AgentClient) -> None:
        self._client = client

    def ask(self, question: str) -> AgentAnswerResult:
        return self._client.ask(question)
