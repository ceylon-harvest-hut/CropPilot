from unittest.mock import MagicMock, patch

from app.domains.agent.data import AgentAnswerResult, ToolCallRecord
from app.infrastructure.agent.gemini_agent_client import GeminiAgentClient
from langchain_core.tools import StructuredTool


@patch("langchain_google_genai.ChatGoogleGenerativeAI")
@patch("app.infrastructure.agent.gemini_agent_client.LangChainAgentClient")
def test_gemini_agent_client_delegates_to_langchain_client(
    mock_langchain_client_cls: MagicMock,
    mock_chat_cls: MagicMock,
) -> None:
    tool = StructuredTool.from_function(
        func=lambda crop_name, land_area_hectares: "ok",
        name="calculate_crop_density_and_spacing",
        description="Spacing calculator",
    )
    inner = MagicMock()
    inner.ask.return_value = AgentAnswerResult(
        answer="Done",
        tools_used=[
            ToolCallRecord(
                name="calculate_crop_density_and_spacing",
                arguments={"crop_name": "Cabbage", "land_area_hectares": 0.5},
                result="ok",
            )
        ],
    )
    mock_langchain_client_cls.return_value = inner

    client = GeminiAgentClient(
        api_key="test-key",
        model="models/gemini-2.5-flash",
        tools=[tool],
    )
    result = client.ask("How many plants?")

    mock_chat_cls.assert_called_once()
    mock_langchain_client_cls.assert_called_once()
    inner.ask.assert_called_once_with("How many plants?")
    assert result.answer == "Done"
    assert len(result.tools_used) == 1
