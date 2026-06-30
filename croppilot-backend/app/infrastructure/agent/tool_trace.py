from __future__ import annotations

from typing import Any

from app.domains.agent.data import ToolCallRecord


def _tool_call_args(tool_call: dict[str, Any]) -> dict[str, object]:
    args = tool_call.get("args")
    if args is None:
        args = tool_call.get("arguments")
    if args is None:
        return {}
    return dict(args)


def records_from_tool_round(
    tool_calls: list[dict[str, Any]],
    results: list[str],
) -> list[ToolCallRecord]:
    records: list[ToolCallRecord] = []
    for tool_call, result in zip(tool_calls, results, strict=True):
        records.append(
            ToolCallRecord(
                name=str(tool_call.get("name", "")),
                arguments=_tool_call_args(tool_call),
                result=result,
            )
        )
    return records
