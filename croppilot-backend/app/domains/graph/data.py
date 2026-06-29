from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from app.domains.graph.schemas import Disease, FertilizerStep, Pest


@dataclass(frozen=True)
class GraphIngestArtifacts:
    """Optional on-disk artifacts produced during graph ingestion."""

    html_output_path: Path | None = None
    json_output_path: Path | None = None


@dataclass
class ExtractedCropKnowledge:
    crop_name: str
    scientific_name: str | None = None
    growing_areas: list[str] = field(default_factory=list)
    growing_seasons: list[str] = field(default_factory=list)
    varieties: list[str] = field(default_factory=list)
    soil_types: list[str] = field(default_factory=list)
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
    fertilizer_schedule: list[FertilizerStep] = field(default_factory=list)
    pests: list[Pest] = field(default_factory=list)
    diseases: list[Disease] = field(default_factory=list)
    expected_harvest_kg_per_ha: float | None = None


@dataclass
class GraphIngestResult:
    source_id: int
    crop_name: str
    status: str
    replaced: bool = False
    html_path: Path | None = None
    json_path: Path | None = None
