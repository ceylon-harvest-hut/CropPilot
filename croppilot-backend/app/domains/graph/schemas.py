from typing import List, Optional

from pydantic import BaseModel, Field


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


class Pest(BaseModel):
    name: str = Field(description="Common name of the pest, insect, or vector")
    impact: str = Field(
        description="Description of feeding damage, specific symptoms, or visible signs of infestation on the plant"
    )
    solution: str = Field(
        description="Agronomic, physical, or chemical control methods and insecticide recommendations"
    )


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


class CropDataExtraction(BaseModel):
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
