from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.domains.agent.data import AgentAnswerResult, ToolCallRecord
from app.domains.agent.dependencies import get_agent_service
from app.domains.agent.service import AgentService
from app.main import app


@pytest.fixture
def client() -> TestClient:
    mock_service = MagicMock(spec=AgentService)
    mock_service.ask.return_value = AgentAnswerResult(
        answer="You can fit about 2,500 cabbage plants on 0.5 hectares.",
        tools_used=[
            ToolCallRecord(
                name="calculate_crop_density_and_spacing",
                arguments={"crop_name": "Cabbage", "land_area_hectares": 0.5},
                result="Needs 2,500 plants.",
            )
        ],
    )

    app.dependency_overrides[get_agent_service] = lambda: mock_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_ask_agent_endpoint_returns_200(client: TestClient) -> None:
    response = client.post(
        "/api/v1/ask-agent",
        json={"question": "How many cabbage plants for 0.5 ha?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert "2,500" in body["answer"]
    assert len(body["tools_used"]) == 1
    tool = body["tools_used"][0]
    assert tool["name"] == "calculate_crop_density_and_spacing"
    assert tool["arguments"]["crop_name"] == "Cabbage"
    assert "2,500" in tool["result"]


def test_ask_agent_endpoint_rejects_blank_question(client: TestClient) -> None:
    response = client.post(
        "/api/v1/ask-agent",
        json={"question": "   "},
    )

    assert response.status_code == 422


def test_ask_agent_endpoint_rejects_missing_question(client: TestClient) -> None:
    response = client.post("/api/v1/ask-agent", json={})

    assert response.status_code == 422
