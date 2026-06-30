from unittest.mock import MagicMock

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import StructuredTool

from app.infrastructure.agent.langchain_agent_client import LangChainAgentClient


def _spacing_tool() -> StructuredTool:
    return StructuredTool.from_function(
        func=lambda crop_name, land_area_hectares: (
            f"Needs 2,500 plants for {crop_name} on {land_area_hectares} ha."
        ),
        name="calculate_crop_density_and_spacing",
        description="Spacing calculator",
    )


def test_langchain_agent_client_returns_direct_answer_without_tools() -> None:
    model = MagicMock()
    bound = MagicMock()
    model.bind_tools.return_value = bound
    bound.invoke.return_value = AIMessage(content="Direct answer without tools.")

    client = LangChainAgentClient(model, [_spacing_tool()])
    result = client.ask("Hello?")

    assert result.answer == "Direct answer without tools."
    assert result.tools_used == []
    bound.invoke.assert_called_once()


def test_langchain_agent_client_runs_tool_and_returns_final_answer() -> None:
    model = MagicMock()
    bound = MagicMock()
    model.bind_tools.return_value = bound
    bound.invoke.side_effect = [
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "calculate_crop_density_and_spacing",
                    "args": {"crop_name": "Cabbage", "land_area_hectares": 0.5},
                    "id": "call-1",
                    "type": "tool_call",
                }
            ],
        ),
        AIMessage(content="You can fit about 2,500 cabbage plants."),
    ]

    client = LangChainAgentClient(model, [_spacing_tool()])
    result = client.ask("How many cabbage plants for 0.5 ha?")

    assert "2,500" in result.answer
    assert len(result.tools_used) == 1
    assert result.tools_used[0].name == "calculate_crop_density_and_spacing"
    assert result.tools_used[0].arguments["crop_name"] == "Cabbage"
    assert "2,500 plants" in result.tools_used[0].result
    assert bound.invoke.call_count == 2
    second_messages = bound.invoke.call_args_list[1].args[0]
    assert any(isinstance(message, ToolMessage) for message in second_messages)
