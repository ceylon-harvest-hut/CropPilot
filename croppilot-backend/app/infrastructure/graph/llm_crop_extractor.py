from __future__ import annotations

from app.domains.graph.data import ExtractedCropKnowledge
from app.domains.graph.schemas import CropDataExtraction
from app.infrastructure.graph.prompts import (
    CROP_EXTRACTION_HUMAN_TEMPLATE,
    CROP_EXTRACTION_SYSTEM_PROMPT,
)
from app.shared.llm.client import LlmClient
from app.shared.llm.retry import invoke_with_retry


def to_extracted_crop_knowledge(
    data: CropDataExtraction,
    *,
    crop_tag: str,
) -> ExtractedCropKnowledge:
    return ExtractedCropKnowledge(
        crop_name=crop_tag,
        scientific_name=data.scientific_name,
        growing_areas=list(data.growing_areas),
        growing_seasons=list(data.growing_seasons),
        varieties=list(data.varieties),
        soil_types=list(data.soil_types),
        altitude_min_m=data.altitude_min_m,
        altitude_max_m=data.altitude_max_m,
        temp_min_c=data.temp_min_c,
        temp_max_c=data.temp_max_c,
        rainfall_min_mm=data.rainfall_min_mm,
        rainfall_max_mm=data.rainfall_max_mm,
        ph_min=data.ph_min,
        ph_max=data.ph_max,
        pit_length_cm=data.pit_length_cm,
        pit_width_cm=data.pit_width_cm,
        row_distance_cm=data.row_distance_cm,
        plant_distance_cm=data.plant_distance_cm,
        fertilizer_schedule=list(data.fertilizer_schedule),
        pests=list(data.pests),
        diseases=list(data.diseases),
        expected_harvest_kg_per_ha=data.expected_harvest_kg_per_ha,
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
        crop_tag: str,
        source_uri: str,
    ) -> ExtractedCropKnowledge:
        del source_uri  # reserved for future provenance-aware prompts
        messages = [
            ("system", CROP_EXTRACTION_SYSTEM_PROMPT),
            ("human", CROP_EXTRACTION_HUMAN_TEMPLATE),
        ]
        data = invoke_with_retry(
            lambda: self._client.structured_invoke(
                messages,
                CropDataExtraction,
                variables={"document_text": text},
            ),
            self._client,
            max_retries=self._max_retries,
            default_backoff=self._retry_backoff,
        )
        return to_extracted_crop_knowledge(data, crop_tag=crop_tag)
