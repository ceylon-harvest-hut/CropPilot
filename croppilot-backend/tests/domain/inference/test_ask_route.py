from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.domains.inference.data import AnswerResult, RetrievedChunk
from app.domains.inference.dependencies import get_inference_service
from app.domains.inference.service import InferenceService
from app.main import app


@pytest.fixture
def client() -> TestClient:
    mock_service = MagicMock(spec=InferenceService)
    mock_service.ask.return_value = AnswerResult(
        text="Pepper is a tropical crop.",
        sources=[
            RetrievedChunk(
                chunk_id="chunk-1",
                text_content="Pepper thrives in tropical climates with high humidity.",
                section_name="Introduction",
                crop_tag="Pepper",
            )
        ],
    )

    app.dependency_overrides[get_inference_service] = lambda: mock_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_ask_endpoint_returns_200(client: TestClient) -> None:
    response = client.post(
        "/api/v1/ask",
        json={"question": "What is pepper?", "crop_name": "Pepper"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "Pepper is a tropical crop."
    assert len(body["sources"]) == 1
    assert body["sources"][0]["chunk_id"] == "chunk-1"
    assert body["sources"][0]["section_name"] == "Introduction"
    assert "Pepper thrives" in body["sources"][0]["text_preview"]


def test_ask_endpoint_without_crop_name(client: TestClient) -> None:
    response = client.post(
        "/api/v1/ask",
        json={"question": "What crops grow in tropical climates?"},
    )

    assert response.status_code == 200
    assert "answer" in response.json()


def test_ask_endpoint_rejects_missing_question(client: TestClient) -> None:
    response = client.post(
        "/api/v1/ask",
        json={"crop_name": "Pepper"},
    )

    assert response.status_code == 422
