from __future__ import annotations

from app.domains.graph.data import ExtractedCropKnowledge

MERGE_CROP_CYPHER = """
MERGE (c:Crop {source_uri: $source_uri})
SET c.name = $name,
    c.crop_name = $crop_name,
    c.scientific_name = $scientific_name,
    c.altitude_min_m = $altitude_min_m,
    c.altitude_max_m = $altitude_max_m,
    c.temp_min_c = $temp_min_c,
    c.temp_max_c = $temp_max_c,
    c.rainfall_min_mm = $rainfall_min_mm,
    c.rainfall_max_mm = $rainfall_max_mm,
    c.ph_min = $ph_min,
    c.ph_max = $ph_max,
    c.pit_length_cm = $pit_length_cm,
    c.pit_width_cm = $pit_width_cm,
    c.row_distance_cm = $row_distance_cm,
    c.plant_distance_cm = $plant_distance_cm,
    c.expected_harvest_kg_per_ha = $expected_harvest_kg_per_ha,
    c.days_to_maturity = $days_to_maturity,
    c.nursery_period_days = $nursery_period_days,
    c.seed_amount_per_ha = $seed_amount_per_ha,
    c.seed_metric_type = $seed_metric_type
"""

MERGE_GROWING_AREAS_CYPHER = """
MATCH (c:Crop {source_uri: $source_uri})
UNWIND $items AS area_name
MERGE (a:GrowingArea {name: area_name})
MERGE (c)-[:SUITABLE_IN]->(a)
"""

MERGE_SEASONS_CYPHER = """
MATCH (c:Crop {source_uri: $source_uri})
UNWIND $items AS season_name
MERGE (gs:Season {name: season_name})
MERGE (c)-[:CULTIVATED_DURING]->(gs)
"""

MERGE_VARIETIES_CYPHER = """
MATCH (c:Crop {source_uri: $source_uri})
UNWIND $items AS var_name
MERGE (v:Variety {name: var_name})
MERGE (c)-[:HAS_VARIETY]->(v)
"""

MERGE_SOILS_CYPHER = """
MATCH (c:Crop {source_uri: $source_uri})
UNWIND $items AS soil_name
MERGE (s:SoilProfile {type: soil_name})
MERGE (c)-[:THRIVES_IN]->(s)
"""

MERGE_FERTILIZER_CYPHER = """
MATCH (c:Crop {source_uri: $source_uri})
UNWIND $items AS fert_data
MERGE (f:Fertilizer {name: fert_data.fertilizer})
SET f.quantity_kg_per_ha = fert_data.quantity_kg_per_ha
MERGE (c)-[:REQUIRES {
    apply_start_weeks_after_planting: fert_data.apply_start_weeks_after_planting,
    repeat_count: fert_data.repeat_count,
    repeat_interval_weeks: fert_data.repeat_interval_weeks,
    quantity_kg_per_ha: fert_data.quantity_kg_per_ha
}]->(f)
"""

MERGE_PESTS_CYPHER = """
MATCH (c:Crop {source_uri: $source_uri})
UNWIND $items AS pest_data
MERGE (p:Pest {name: pest_data.name})
SET p.impact = pest_data.impact,
    p.solution = pest_data.solution
MERGE (c)-[:HARMED_BY]->(p)
"""

MERGE_DISEASES_CYPHER = """
MATCH (c:Crop {source_uri: $source_uri})
UNWIND $items AS disease_data
MERGE (d:Disease {name: disease_data.name})
SET d.causal_agent = disease_data.causal_agent,
    d.impact = disease_data.impact,
    d.solution = disease_data.solution
MERGE (c)-[:INFECTED_BY]->(d)
"""

DELETE_BY_SOURCE_URI_CYPHER = """
MATCH (c:Crop {source_uri: $source_uri})
DETACH DELETE c
"""

CLEAR_GRAPH_CYPHER = """
MATCH (n)
DETACH DELETE n
"""


def _run_write(session, query: str, **params) -> None:
    """Execute a write query and consume the result so the transaction commits."""
    result = session.run(query, **params)
    result.consume()


def _scalar_params(
    extracted: ExtractedCropKnowledge,
    *,
    source_uri: str,
    crop_tag: str,
) -> dict:
    return {
        "source_uri": source_uri,
        "crop_name": crop_tag,
        "name": extracted.crop_name,
        "scientific_name": extracted.scientific_name,
        "altitude_min_m": extracted.altitude_min_m,
        "altitude_max_m": extracted.altitude_max_m,
        "temp_min_c": extracted.temp_min_c,
        "temp_max_c": extracted.temp_max_c,
        "rainfall_min_mm": extracted.rainfall_min_mm,
        "rainfall_max_mm": extracted.rainfall_max_mm,
        "ph_min": extracted.ph_min,
        "ph_max": extracted.ph_max,
        "pit_length_cm": extracted.pit_length_cm,
        "pit_width_cm": extracted.pit_width_cm,
        "row_distance_cm": extracted.row_distance_cm,
        "plant_distance_cm": extracted.plant_distance_cm,
        "expected_harvest_kg_per_ha": extracted.expected_harvest_kg_per_ha,
        "days_to_maturity": extracted.days_to_maturity,
        "nursery_period_days": extracted.nursery_period_days,
        "seed_amount_per_ha": extracted.seed_amount_per_ha,
        "seed_metric_type": extracted.seed_metric_type,
    }


class Neo4jGraphStore:
    def __init__(self, driver) -> None:
        self._driver = driver

    def close(self) -> None:
        self._driver.close()

    def upsert_crop(
        self,
        extracted: ExtractedCropKnowledge,
        *,
        source_uri: str,
        crop_tag: str,
    ) -> None:
        params = _scalar_params(extracted, source_uri=source_uri, crop_tag=crop_tag)
        with self._driver.session() as session:
            _run_write(session, MERGE_CROP_CYPHER, **params)
            uri_param = {"source_uri": source_uri}

            if extracted.growing_areas:
                _run_write(
                    session,
                    MERGE_GROWING_AREAS_CYPHER,
                    items=extracted.growing_areas,
                    **uri_param,
                )
            if extracted.growing_seasons:
                _run_write(
                    session,
                    MERGE_SEASONS_CYPHER,
                    items=extracted.growing_seasons,
                    **uri_param,
                )
            if extracted.varieties:
                _run_write(
                    session,
                    MERGE_VARIETIES_CYPHER,
                    items=extracted.varieties,
                    **uri_param,
                )
            if extracted.soil_types:
                _run_write(
                    session,
                    MERGE_SOILS_CYPHER,
                    items=extracted.soil_types,
                    **uri_param,
                )
            if extracted.fertilizer_schedule:
                _run_write(
                    session,
                    MERGE_FERTILIZER_CYPHER,
                    items=[step.model_dump() for step in extracted.fertilizer_schedule],
                    **uri_param,
                )
            if extracted.pests:
                _run_write(
                    session,
                    MERGE_PESTS_CYPHER,
                    items=[pest.model_dump() for pest in extracted.pests],
                    **uri_param,
                )
            if extracted.diseases:
                _run_write(
                    session,
                    MERGE_DISEASES_CYPHER,
                    items=[disease.model_dump() for disease in extracted.diseases],
                    **uri_param,
                )

    def delete_by_source_uri(self, source_uri: str) -> int:
        with self._driver.session() as session:
            result = session.run(DELETE_BY_SOURCE_URI_CYPHER, source_uri=source_uri)
            summary = result.consume()
            return summary.counters.nodes_deleted

    def count_by_source_uri(self, source_uri: str) -> int:
        with self._driver.session() as session:
            result = session.run(
                "MATCH (c:Crop {source_uri: $source_uri}) RETURN count(c) AS n",
                source_uri=source_uri,
            )
            record = result.single()
            return int(record["n"]) if record else 0

    def clear_graph(self) -> int:
        with self._driver.session() as session:
            result = session.run(CLEAR_GRAPH_CYPHER)
            summary = result.consume()
            return summary.counters.nodes_deleted
