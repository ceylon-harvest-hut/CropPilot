from unittest.mock import MagicMock, patch

from app.domains.agent.data import AgentAnswerResult
from app.infrastructure.agent.gemini_agent_client import (
    GeminiAgentClient,
    extract_tools_used,
)


def _make_response(*, text: str, parts: list) -> MagicMock:
    response = MagicMock()
    response.text = text
    candidate = MagicMock()
    content = MagicMock()
    content.parts = parts
    candidate.content = content
    response.candidates = [candidate]
    return response


def test_extract_tools_used_parses_function_call_and_response() -> None:
    call_part = MagicMock()
    call_part.function_call = MagicMock()
    call_part.function_call.name = "calculate_crop_density_and_spacing"
    call_part.function_call.args = {
        "crop_name": "Cabbage",
        "land_area_hectares": 0.5,
    }
    call_part.function_response = None

    response_part = MagicMock()
    response_part.function_call = None
    response_part.function_response = MagicMock()
    response_part.function_response.name = "calculate_crop_density_and_spacing"
    response_part.function_response.response = "Needs 2,500 plants."

    tools_used = extract_tools_used(
        _make_response(text="You can fit about 2,500 plants.", parts=[call_part, response_part])
    )

    assert len(tools_used) == 1
    assert tools_used[0].name == "calculate_crop_density_and_spacing"
    assert tools_used[0].arguments["crop_name"] == "Cabbage"
    assert tools_used[0].result == "Needs 2,500 plants."


@patch("app.infrastructure.agent.gemini_agent_client.genai.Client")
def test_gemini_agent_client_returns_answer_and_tools(mock_client_cls: MagicMock) -> None:
    call_part = MagicMock()
    call_part.function_call = MagicMock()
    call_part.function_call.name = "calculate_crop_density_and_spacing"
    call_part.function_call.args = {
        "crop_name": "Cabbage",
        "land_area_hectares": 0.5,
    }
    call_part.function_response = None
    response_part = MagicMock()
    response_part.function_call = None
    response_part.function_response = MagicMock()
    response_part.function_response.name = "calculate_crop_density_and_spacing"
    response_part.function_response.response = "Needs 2,500 plants."

    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.models.generate_content.return_value = _make_response(
        text="You can fit about 2,500 cabbage plants.",
        parts=[call_part, response_part],
    )

    client = GeminiAgentClient(api_key="test-key", model="models/gemini-2.5-flash")

    def dummy_tool(crop_name: str, land_area_hectares: float) -> str:
        return "ok"

    result = client.ask("How many cabbage plants for 0.5 ha?", [dummy_tool])

    assert isinstance(result, AgentAnswerResult)
    assert "2,500" in result.answer
    assert len(result.tools_used) == 1
    mock_client.models.generate_content.assert_called_once()
