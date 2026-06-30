from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ToolCallRecord:
    name: str
    arguments: dict[str, object]
    result: str


@dataclass
class AgentAnswerResult:
    answer: str
    tools_used: list[ToolCallRecord] = field(default_factory=list)
