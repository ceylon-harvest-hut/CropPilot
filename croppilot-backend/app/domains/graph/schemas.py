from typing import List, Optional, Literal

from pydantic import BaseModel, Field, field_validator

def normalize_string(v: str) -> str:
    if isinstance(v, str):
        return v.strip().title()
    return v

def normalize_string_list(v: List[str]) -> List[str]:
    if isinstance(v, list):
        return [normalize_string(item) for item in v if isinstance(item, str)]
    return v


class FertilizerStep(BaseModel):
    fertilizer: str = Field(description="Name of the fertilizer, e.g., Urea, MOP, TSP")
    apply_start_weeks_after_planting: float = Field(
        description="Weeks or days after planting to apply"
    )
    repeat_count: int = Field(description="Number of times this application is repeated")
    repeat_interval_weeks: float = Field(
        description="Interval between repetitions in weeks"
    )
    quantity_kg_per_ha: float = Field(
        description="Quantity required per hectare. If given in acres, convert to hectares (1 ha = 2.47 acres)"
    )

    @field_validator("fertilizer")
    @classmethod
    def clean_fertilizer(cls, v: str) -> str:
        return normalize_string(v)


class Pest(BaseModel):
    name: str = Field(description="Common name of the pest, insect, or vector")
    impact: str = Field(
        description="Description of feeding damage, specific symptoms, or visible signs of infestation on the plant"
    )
    solution: str = Field(
        description="Agronomic, physical, or chemical control methods and insecticide recommendations"
    )

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        return normalize_string(v)


class Disease(BaseModel):
    name: str = Field(description="Common name of the disease")
    causal_agent: Optional[str] = Field(
        None,
        description="The underlying fungal, bacterial, or viral pathogen if explicitly specified",
    )
    impact: str = Field(description="Foliage, stem, or root symptoms indicating infection")
    solution: str = Field(
        description="Field management practices, soil sterilization, sanitation, or chemical fungicide recommendations"
    )

    @field_validator("name", "causal_agent")
    @classmethod
    def clean_disease_fields(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return normalize_string(v)


class ExtractedCropKnowledge(BaseModel):
    name: str = Field(description="Common English name of the crop")
    scientific_name: Optional[str] = Field(None, description="Scientific/Botanical name")
    growing_areas: List[str] = Field(
        default_factory=list,
        description="Suitable agro-ecological zones, regions, or specific administrative districts in Sri Lanka",
    )
    growing_seasons: List[str] = Field(
        default_factory=list,
        description="Suitable seasons, e.g., Yala, Maha, Year-round",
    )
    varieties: List[str] = Field(
        default_factory=list,
        description="Recommended crop varieties or cultivars",
    )
    soil_types: List[str] = Field(
        default_factory=list,
        description="Suitable soil types, e.g., Red Yellow Podzolic, Regosol, Alluvial",
    )
    altitude_min_m: Optional[float] = Field(None, description="Minimum suitable altitude in meters")
    altitude_max_m: Optional[float] = Field(None, description="Maximum suitable altitude in meters")
    temp_min_c: Optional[float] = Field(None, description="Minimum temperature tolerance in Celsius")
    temp_max_c: Optional[float] = Field(None, description="Maximum temperature tolerance in Celsius")
    rainfall_min_mm: Optional[float] = Field(None, description="Minimum annual rainfall in mm")
    rainfall_max_mm: Optional[float] = Field(None, description="Maximum annual rainfall in mm")
    ph_min: Optional[float] = Field(None, description="Minimum soil pH requirement")
    ph_max: Optional[float] = Field(None, description="Maximum soil pH requirement")
    pit_length_cm: Optional[float] = Field(None, description="Length of planting pit in centimeters")
    pit_width_cm: Optional[float] = Field(None, description="Width of planting pit in centimeters")
    row_distance_cm: Optional[float] = Field(None, description="Distance between rows in centimeters")
    plant_distance_cm: Optional[float] = Field(
        None, description="Distance between individual plants in centimeters"
    )
    fertilizer_schedule: List[FertilizerStep] = Field(default_factory=list)
    pests: List[Pest] = Field(
        default_factory=list,
        description="List of distinct harmful insects, bugs, mites, or borers affecting the crop",
    )
    diseases: List[Disease] = Field(
        default_factory=list,
        description="List of distinct bacterial, fungal, or viral conditions affecting the crop",
    )
    expected_harvest_kg_per_ha: Optional[float] = Field(
        None, description="Expected average yield in kg per hectare"
    )
    # Standardize to int for clean math, filtering, and API rendering
    days_to_maturity: Optional[int] = Field(
        None, 
        description="The typical number of days from field establishment (transplanting or direct sowing) to harvest.",
    )
    
    # Optional but highly useful for crops started in nursery beds
    nursery_period_days: Optional[int] = Field(
        None,
        description="Number of days the seedling spends in the nursery before transplanting.",
    )

    # --- Seed & Material Requirements ---
    seed_amount_per_ha: Optional[float] = Field(
        None,
        description="The normalized mathematical average weight or count of planting material required per hectare.",
    )
    seed_metric_type: Optional[Literal["weight", "count", "vines", "suckers"]] = Field(
        None,
        description="The agronomic classification of the propagation unit (e.g., weight for seeds, vines for sweet potato, suckers for banana)."
    )

    @field_validator("name")
    @classmethod
    def clean_crop_name(cls, v: str) -> str:
        return normalize_string(v)

    @field_validator("growing_areas", "growing_seasons", "varieties", "soil_types")
    @classmethod
    def clean_lists(cls, v: List[str]) -> List[str]:
        return normalize_string_list(v)
