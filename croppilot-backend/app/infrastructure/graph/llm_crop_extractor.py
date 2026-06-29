from __future__ import annotations

from app.domains.graph.schemas import ExtractedCropKnowledge
from app.infrastructure.graph.prompts import (
    CROP_EXTRACTION_HUMAN_TEMPLATE,
    CROP_EXTRACTION_SYSTEM_PROMPT,
)
from app.shared.llm.client import LlmClient
from app.shared.llm.retry import invoke_with_retry


def _manifest_hint(manifest_crop_name: str | None) -> str:
    if not manifest_crop_name:
        return ""
    return (
        "Listed crop (hint only, use document text as source of truth): "
        f"{manifest_crop_name}\n\n"
    )


class LlmCropGraphExtractor:
    def __init__(
        self,
        client: LlmClient,
        *,
        max_retries: int = 5,
        retry_backoff: float = 30.0,
    ) -> None:
        self._client = client
        self._max_retries = max_retries
        self._retry_backoff = retry_backoff

    def extract(
        self,
        text: str,
        *,
        manifest_crop_name: str | None = None,
        source_uri: str,
    ) -> ExtractedCropKnowledge:
        del source_uri  # reserved for future provenance-aware prompts
        messages = [
            ("system", CROP_EXTRACTION_SYSTEM_PROMPT),
            ("human", CROP_EXTRACTION_HUMAN_TEMPLATE),
        ]
        return invoke_with_retry(
            lambda: self._client.structured_invoke(
                messages,
                ExtractedCropKnowledge,
                variables={
                    "document_text": text,
                    "manifest_hint": _manifest_hint(manifest_crop_name),
                },
            ),
            self._client,
            max_retries=self._max_retries,
            default_backoff=self._retry_backoff,
        )
