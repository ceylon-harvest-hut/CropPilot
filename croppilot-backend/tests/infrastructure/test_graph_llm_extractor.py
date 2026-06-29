from unittest.mock import MagicMock

from app.domains.graph.schemas import ExtractedCropKnowledge, Pest
from app.infrastructure.graph.llm_crop_extractor import LlmCropGraphExtractor
from app.shared.llm.errors import LlmApiErrorInfo


def test_llm_crop_extractor_invokes_client() -> None:
    client = MagicMock()
    client.structured_invoke.return_value = ExtractedCropKnowledge(name="Pepper")
    extractor = LlmCropGraphExtractor(client, max_retries=0, retry_backoff=0.0)

    result = extractor.extract(
        "doc text",
        manifest_crop_name="Pepper",
        source_uri="pepper.html",
    )

    client.structured_invoke.assert_called_once()
    call_kwargs = client.structured_invoke.call_args
    assert call_kwargs.kwargs["variables"]["document_text"] == "doc text"
    assert "Pepper" in call_kwargs.kwargs["variables"]["manifest_hint"]
    assert result.name == "Pepper"


def test_llm_crop_extractor_omits_hint_when_manifest_crop_name_missing() -> None:
    client = MagicMock()
    client.structured_invoke.return_value = ExtractedCropKnowledge(name="Pepper")
    extractor = LlmCropGraphExtractor(client, max_retries=0, retry_backoff=0.0)

    extractor.extract("doc text", manifest_crop_name=None, source_uri="pepper.html")

    call_kwargs = client.structured_invoke.call_args
    assert call_kwargs.kwargs["variables"]["manifest_hint"] == ""


def test_llm_crop_extractor_retries_on_retryable_error() -> None:
    client = MagicMock()
    client.interpret_api_error.return_value = LlmApiErrorInfo(
        retryable=True,
        retry_after_seconds=0.0,
        code="RESOURCE_EXHAUSTED",
    )
    client.structured_invoke.side_effect = [
        RuntimeError("rate limited"),
        ExtractedCropKnowledge(name="Pepper"),
    ]
    extractor = LlmCropGraphExtractor(client, max_retries=2, retry_backoff=0.0)

    result = extractor.extract(
        "doc text",
        manifest_crop_name="Pepper",
        source_uri="pepper.html",
    )

    assert client.structured_invoke.call_count == 2
    assert result.name == "Pepper"
