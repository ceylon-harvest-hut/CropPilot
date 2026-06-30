from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GraphCropSummary:
    name: str
    node_count: int
    source_uris: list[str]


@dataclass
class GraphFertilizerRecord:
    fertilizer: str
    apply_start_weeks_after_planting: float | None = None
    repeat_count: int | None = None
    repeat_interval_weeks: float | None = None
    quantity_kg_per_ha: float | None = None


@dataclass
class GraphPestRecord:
    name: str
    impact: str | None = None
    solution: str | None = None


@dataclass
class GraphDiseaseRecord:
    name: str
    causal_agent: str | None = None
    impact: str | None = None
    solution: str | None = None


@dataclass
class GraphCropNode:
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
    growing_areas: list[str] = field(default_factory=list)
    growing_seasons: list[str] = field(default_factory=list)
    varieties: list[str] = field(default_factory=list)
    soil_types: list[str] = field(default_factory=list)
    fertilizer_schedule: list[GraphFertilizerRecord] = field(default_factory=list)
    pests: list[GraphPestRecord] = field(default_factory=list)
    diseases: list[GraphDiseaseRecord] = field(default_factory=list)


@dataclass
class GraphCropDetail:
    name: str
    nodes: list[GraphCropNode]
