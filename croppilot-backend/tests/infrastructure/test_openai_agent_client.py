from unittest.mock import MagicMock, patch

from app.domains.agent.data import AgentAnswerResult
from app.infrastructure.agent.openai_agent_client import OpenAIAgentClient
from langchain_core.tools import StructuredTool


@patch("langchain_openai.ChatOpenAI")
@patch("app.infrastructure.agent.openai_agent_client.LangChainAgentClient")
def test_openai_agent_client_delegates_to_langchain_client(
    mock_langchain_client_cls: MagicMock,
    mock_chat_cls: MagicMock,
) -> None:
    tool = StructuredTool.from_function(
        func=lambda crop_name, land_area_hectares: "ok",
        name="calculate_crop_density_and_spacing",
        description="Spacing calculator",
    )
    inner = MagicMock()
    inner.ask.return_value = AgentAnswerResult(answer="OpenAI answer", tools_used=[])
    mock_langchain_client_cls.return_value = inner

    client = OpenAIAgentClient(
        api_key="test-key",
        model="gpt-4o-mini",
        tools=[tool],
    )
    result = client.ask("How many plants?")

    mock_chat_cls.assert_called_once()
    mock_langchain_client_cls.assert_called_once()
    inner.ask.assert_called_once_with("How many plants?")
    assert result.answer == "OpenAI answer"
