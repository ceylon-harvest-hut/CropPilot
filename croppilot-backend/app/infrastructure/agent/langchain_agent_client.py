from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import StructuredTool

from app.domains.agent.data import AgentAnswerResult, ToolCallRecord
from app.infrastructure.agent.prompts import AGENT_SYSTEM_PROMPT
from app.infrastructure.agent.tool_trace import records_from_tool_round


def _content_to_str(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and "text" in block:
                parts.append(str(block["text"]))
            else:
                text = getattr(block, "text", None)
                if text is not None:
                    parts.append(str(text))
        return "".join(parts)
    return str(content)


class LangChainAgentClient:
    """LangChain tool-calling loop shared by Gemini and OpenAI agent clients.

    Future: chat model construction may be shared with RAG LlmClient factories.
    """

    def __init__(
        self,
        model: BaseChatModel,
        tools: list[StructuredTool],
        *,
        max_tool_rounds: int = 5,
    ) -> None:
        self._bound = model.bind_tools(tools)
        self._tools_by_name = {tool.name: tool for tool in tools}
        self._max_tool_rounds = max_tool_rounds

    def ask(self, question: str) -> AgentAnswerResult:
        messages: list[SystemMessage | HumanMessage | AIMessage | ToolMessage] = [
            SystemMessage(content=AGENT_SYSTEM_PROMPT),
            HumanMessage(content=question),
        ]
        tools_used: list[ToolCallRecord] = []

        for _ in range(self._max_tool_rounds):
            ai_msg = self._bound.invoke(messages)
            if not isinstance(ai_msg, AIMessage):
                raise TypeError(f"Expected AIMessage, got {type(ai_msg)!r}")

            if not ai_msg.tool_calls:
                return AgentAnswerResult(
                    answer=_content_to_str(ai_msg.content),
                    tools_used=tools_used,
                )

            messages.append(ai_msg)
            round_results: list[str] = []
            for tool_call in ai_msg.tool_calls:
                name = str(tool_call["name"])
                args = tool_call.get("args") or tool_call.get("arguments") or {}
                tool = self._tools_by_name[name]
                result = str(tool.invoke(args))
                round_results.append(result)
                messages.append(
                    ToolMessage(content=result, tool_call_id=tool_call["id"])
                )

            tools_used.extend(records_from_tool_round(ai_msg.tool_calls, round_results))

        raise RuntimeError(f"Ask agent exceeded max tool rounds ({self._max_tool_rounds})")
