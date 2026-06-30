from pydantic import BaseModel

from app.domains.ingestion.schemas import CropItemResponse, CropListResponse

__all__ = ["CropItemResponse", "CropListResponse"]


class ChunkItemResponse(BaseModel):
    chunk_id: str
    crop_tag: str
    source_uri: str
    section_name: str
    page_number: int
    text_preview: str


class ChunkListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    chunks: list[ChunkItemResponse]


class SourceItemResponse(BaseModel):
    source_id: int
    origin_url: str
    status: str
    crop_names: list[str]


class SourceListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    sources: list[SourceItemResponse]


class GraphCropSummaryResponse(BaseModel):
    name: str
    node_count: int
    source_uris: list[str]


class GraphCropListResponse(BaseModel):
    total: int
    crops: list[GraphCropSummaryResponse]


class GraphFertilizerResponse(BaseModel):
    fertilizer: str
    apply_start_weeks_after_planting: float | None = None
    repeat_count: int | None = None
    repeat_interval_weeks: float | None = None
    quantity_kg_per_ha: float | None = None


class GraphPestResponse(BaseModel):
    name: str
    impact: str | None = None
    solution: str | None = None


class GraphDiseaseResponse(BaseModel):
    name: str
    causal_agent: str | None = None
    impact: str | None = None
    solution: str | None = None


class GraphCropNodeResponse(BaseModel):
    source_uri: str
    name: str
    manifest_crop_name: str | None = None
    scientific_name: str | None = None
    altitude_min_m: float | None = None
    altitude_max_m: float | None = None
    temp_min_c: float | None = None
    temp_max_c: float | None = None
    rainfall_min_mm: float | None = None
    rainfall_max_mm: float | None = None
    ph_min: float | None = None
    ph_max: float | None = None
    pit_length_cm: float | None = None
    pit_width_cm: float | None = None
    row_distance_cm: float | None = None
    plant_distance_cm: float | None = None
    expected_harvest_kg_per_ha: float | None = None
    days_to_maturity: int | None = None
    nursery_period_days: int | None = None
    seed_amount_per_ha: float | None = None
    seed_metric_type: str | None = None
    growing_areas: list[str]
    growing_seasons: list[str]
    varieties: list[str]
    soil_types: list[str]
    fertilizer_schedule: list[GraphFertilizerResponse]
    pests: list[GraphPestResponse]
    diseases: list[GraphDiseaseResponse]


class GraphCropDetailResponse(BaseModel):
    name: str
    nodes: list[GraphCropNodeResponse]
