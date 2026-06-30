from __future__ import annotations

from typing import Any

from langchain_core.tools import StructuredTool

_SPACING_TOOL_DESCRIPTION = (
    "Fetches planting spacing requirements for a specific crop from the database "
    "and automatically calculates the total number of plants needed for a given land area."
)


def calculate_crop_density_and_spacing(
    driver: Any,
    crop_name: str,
    land_area_hectares: float,
) -> str:
    normalized_crop = crop_name.strip().title()
    query = """
    MATCH (c:Crop {name: $name})
    RETURN c.name AS name, c.row_distance_cm AS row_dist, c.plant_distance_cm AS plant_dist
    """
    with driver.session() as session:
        result = session.run(query, {"name": normalized_crop})
        record = result.single()

    if not record:
        return f"Error: Crop '{crop_name}' could not be found."

    row_dist_cm = record["row_dist"]
    plant_dist_cm = record["plant_dist"]

    if not row_dist_cm or not plant_dist_cm:
        return f"The crop '{normalized_crop}' exists, but spacing metrics are missing."

    total_area_m2 = land_area_hectares * 10000
    area_per_plant_m2 = (row_dist_cm / 100.0) * (plant_dist_cm / 100.0)
    total_plants_needed = int(total_area_m2 // area_per_plant_m2)

    return (
        f"Crop: {normalized_crop}. Spacing: {row_dist_cm}x{plant_dist_cm}cm. "
        f"Needs {total_plants_needed:,} plants."
    )


def build_spacing_langchain_tool(driver: Any) -> StructuredTool:
    def _run(crop_name: str, land_area_hectares: float) -> str:
        return calculate_crop_density_and_spacing(
            driver,
            crop_name=crop_name,
            land_area_hectares=land_area_hectares,
        )

    return StructuredTool.from_function(
        func=_run,
        name="calculate_crop_density_and_spacing",
        description=_SPACING_TOOL_DESCRIPTION,
    )
