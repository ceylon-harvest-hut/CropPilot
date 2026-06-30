from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from app.domains.agent.data import AgentAnswerResult


class AgentClient(Protocol):
    def ask(self, question: str, tools: list[Callable[..., object]]) -> AgentAnswerResult: ...


class AgentService:
    def __init__(self, client: AgentClient, tools: list[Callable[..., object]]) -> None:
        self._client = client
        self._tools = tools

    def ask(self, question: str) -> AgentAnswerResult:
        return self._client.ask(question, self._tools)
