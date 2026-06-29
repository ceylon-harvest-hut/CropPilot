from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.domains.inference.data import AnswerResult
from app.domains.inference.dependencies import get_inference_service
from app.domains.inference.references import ReferenceDocument
from app.domains.inference.service import InferenceService
from app.main import app


@pytest.fixture
def client() -> TestClient:
    mock_service = MagicMock(spec=InferenceService)
    mock_service.ask.return_value = AnswerResult(
        text="Pepper is a tropical crop widely cultivated in Sri Lanka.",
        references=[
            ReferenceDocument(
                source_uri="https://dea.gov.lk/pepper/",
                crop_name="Pepper",
                title="Pepper",
                excerpt="Pepper varieties include…",
                source_type="web_url",
            )
        ],
    )

    app.dependency_overrides[get_inference_service] = lambda: mock_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_ask_templates_endpoint_returns_options() -> None:
    with TestClient(app) as test_client:
        response = test_client.get("/api/v1/ask/templates")

    assert response.status_code == 200
    body = response.json()
    assert body["default_template"] == "context_only"
    names = [item["name"] for item in body["templates"]]
    assert "context_only" in names
    assert "hybrid" in names


def test_ask_endpoint_returns_200(client: TestClient) -> None:
    response = client.post(
        "/api/v1/ask",
        json={"question": "What is pepper?", "crop_name": "Pepper"},
    )

    assert response.status_code == 200
    body = response.json()
    assert "Pepper is a tropical crop" in body["answer"]
    assert body["template"] == "context_only"
    assert len(body["references"]) == 1
    ref = body["references"][0]
    assert ref["source_uri"] == "https://dea.gov.lk/pepper/"
    assert ref["title"] == "Pepper"
    assert ref["source_type"] == "web_url"
    assert "sections" not in ref
    assert "Pepper varieties" in ref["excerpt"]


def test_ask_endpoint_accepts_hybrid_template(client: TestClient) -> None:
    mock_service = app.dependency_overrides[get_inference_service]()
    response = client.post(
        "/api/v1/ask",
        json={"question": "What is pepper?", "crop_name": "Pepper", "template": "hybrid"},
    )

    assert response.status_code == 200
    assert response.json()["template"] == "hybrid"
    mock_service.ask.assert_called_once_with(
        "What is pepper?",
        crop_tag="Pepper",
        template="hybrid",
    )


def test_ask_endpoint_without_crop_name_returns_422(client: TestClient) -> None:
    """crop_name is now required — omitting it must return 422."""
    response = client.post(
        "/api/v1/ask",
        json={"question": "What crops grow in tropical climates?"},
    )
    assert response.status_code == 422


def test_ask_endpoint_blank_crop_name_returns_422(client: TestClient) -> None:
    """Blank (whitespace-only) crop_name must be rejected."""
    response = client.post(
        "/api/v1/ask",
        json={"question": "What is pepper?", "crop_name": "   "},
    )
    assert response.status_code == 422


def test_ask_endpoint_rejects_missing_question(client: TestClient) -> None:
    response = client.post(
        "/api/v1/ask",
        json={"crop_name": "Pepper"},
    )

    assert response.status_code == 422


def test_ask_endpoint_rejects_unknown_template(client: TestClient) -> None:
    response = client.post(
        "/api/v1/ask",
        json={"question": "What is pepper?", "crop_name": "Pepper", "template": "unknown"},
    )

    assert response.status_code == 422
