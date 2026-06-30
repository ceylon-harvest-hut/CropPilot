from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from google import genai
from google.genai import types

from app.domains.agent.data import AgentAnswerResult, ToolCallRecord
from app.infrastructure.agent.prompts import AGENT_SYSTEM_PROMPT


def _normalize_arguments(args: Any) -> dict[str, object]:
    if args is None:
        return {}
    if isinstance(args, dict):
        return dict(args)
    if hasattr(args, "items"):
        return dict(args)
    return {"value": args}


def _normalize_result(response: Any) -> str:
    if response is None:
        return ""
    if isinstance(response, str):
        return response
    if isinstance(response, dict):
        if "result" in response:
            return str(response["result"])
        return json.dumps(response, ensure_ascii=False)
    return str(response)


def extract_tools_used(response: Any) -> list[ToolCallRecord]:
    tools_used: list[ToolCallRecord] = []
    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        return tools_used

    content = getattr(candidates[0], "content", None)
    parts = getattr(content, "parts", None) or []

    pending: dict[str, ToolCallRecord] = {}
    for part in parts:
        function_call = getattr(part, "function_call", None)
        if function_call is not None:
            name = str(function_call.name or "")
            pending[name] = ToolCallRecord(
                name=name,
                arguments=_normalize_arguments(function_call.args),
                result="",
            )

        function_response = getattr(part, "function_response", None)
        if function_response is not None:
            name = str(function_response.name or "")
            result = _normalize_result(function_response.response)
            if name in pending:
                pending[name].result = result
            else:
                pending[name] = ToolCallRecord(
                    name=name,
                    arguments={},
                    result=result,
                )

    tools_used.extend(pending.values())
    return tools_used


class GeminiAgentClient:
    def __init__(self, *, api_key: str, model: str) -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model

    def ask(
        self,
        question: str,
        tools: list[Callable[..., object]],
    ) -> AgentAnswerResult:
        response = self._client.models.generate_content(
            model=self._model,
            contents=question,
            config=types.GenerateContentConfig(
                system_instruction=AGENT_SYSTEM_PROMPT,
                tools=tools,
                temperature=0.0,
            ),
        )
        answer = response.text or ""
        return AgentAnswerResult(
            answer=answer,
            tools_used=extract_tools_used(response),
        )
