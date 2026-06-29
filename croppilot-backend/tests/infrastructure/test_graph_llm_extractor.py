from unittest.mock import MagicMock

from app.domains.graph.schemas import CropDataExtraction, Pest
from app.infrastructure.graph.llm_crop_extractor import (
    LlmCropGraphExtractor,
    to_extracted_crop_knowledge,
)
from app.shared.llm.errors import LlmApiErrorInfo


def test_to_extracted_crop_knowledge_maps_fields() -> None:
    data = CropDataExtraction(
        name="Pepper",
        scientific_name="Piper nigrum",
        pests=[Pest(name="Aphid", impact="leaf curl", solution="spray")],
    )
    result = to_extracted_crop_knowledge(data, crop_tag="Pepper")
    assert result.crop_name == "Pepper"
    assert result.scientific_name == "Piper nigrum"
    assert len(result.pests) == 1


def test_llm_crop_extractor_invokes_client() -> None:
    client = MagicMock()
    client.structured_invoke.return_value = CropDataExtraction(name="Pepper")
    extractor = LlmCropGraphExtractor(client, max_retries=0, retry_backoff=0.0)

    result = extractor.extract("doc text", crop_tag="Pepper", source_uri="pepper.html")

    client.structured_invoke.assert_called_once()
    call_kwargs = client.structured_invoke.call_args
    assert call_kwargs.kwargs["variables"] == {"document_text": "doc text"}
    assert result.crop_name == "Pepper"


def test_llm_crop_extractor_retries_on_retryable_error() -> None:
    client = MagicMock()
    client.interpret_api_error.return_value = LlmApiErrorInfo(
        retryable=True,
        retry_after_seconds=0.0,
        code="RESOURCE_EXHAUSTED",
    )
    client.structured_invoke.side_effect = [
        RuntimeError("rate limited"),
        CropDataExtraction(name="Pepper"),
    ]
    extractor = LlmCropGraphExtractor(client, max_retries=2, retry_backoff=0.0)

    result = extractor.extract("doc text", crop_tag="Pepper", source_uri="pepper.html")

    assert client.structured_invoke.call_count == 2
    assert result.crop_name == "Pepper"
