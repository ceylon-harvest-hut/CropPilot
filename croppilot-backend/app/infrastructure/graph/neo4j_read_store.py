from __future__ import annotations

from typing import Any

from app.domains.debug.graph_data import (
    GraphCropDetail,
    GraphCropNode,
    GraphCropSummary,
    GraphDiseaseRecord,
    GraphFertilizerRecord,
    GraphPestRecord,
)

LIST_CROP_SUMMARIES_CYPHER = """
MATCH (c:Crop)
RETURN c.name AS name, count(c) AS node_count, collect(c.source_uri) AS source_uris
ORDER BY name
"""

LIST_CROP_NODES_CYPHER = """
MATCH (c:Crop)
WHERE c.name = $name
RETURN c.source_uri AS source_uri, properties(c) AS props
ORDER BY c.source_uri
"""

GROWING_AREAS_CYPHER = """
MATCH (c:Crop {source_uri: $source_uri})-[:SUITABLE_IN]->(a:GrowingArea)
RETURN collect(DISTINCT a.name) AS items
"""

SEASONS_CYPHER = """
MATCH (c:Crop {source_uri: $source_uri})-[:CULTIVATED_DURING]->(s:Season)
RETURN collect(DISTINCT s.name) AS items
"""

VARIETIES_CYPHER = """
MATCH (c:Crop {source_uri: $source_uri})-[:HAS_VARIETY]->(v:Variety)
RETURN collect(DISTINCT v.name) AS items
"""

SOILS_CYPHER = """
MATCH (c:Crop {source_uri: $source_uri})-[:THRIVES_IN]->(s:SoilProfile)
RETURN collect(DISTINCT s.type) AS items
"""

FERTILIZERS_CYPHER = """
MATCH (c:Crop {source_uri: $source_uri})-[r:REQUIRES]->(f:Fertilizer)
RETURN collect({
    fertilizer: f.name,
    apply_start_weeks_after_planting: r.apply_start_weeks_after_planting,
    repeat_count: r.repeat_count,
    repeat_interval_weeks: r.repeat_interval_weeks,
    quantity_kg_per_ha: r.quantity_kg_per_ha
}) AS items
"""

PESTS_CYPHER = """
MATCH (c:Crop {source_uri: $source_uri})-[:HARMED_BY]->(p:Pest)
RETURN collect({
    name: p.name,
    impact: p.impact,
    solution: p.solution
}) AS items
"""

DISEASES_CYPHER = """
MATCH (c:Crop {source_uri: $source_uri})-[:INFECTED_BY]->(d:Disease)
RETURN collect({
    name: d.name,
    causal_agent: d.causal_agent,
    impact: d.impact,
    solution: d.solution
}) AS items
"""


def _optional_float(value: Any) -> float | None:
    return float(value) if value is not None else None


def _optional_int(value: Any) -> int | None:
    return int(value) if value is not None else None


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _collect_items(session, query: str, *, source_uri: str) -> list:
    record = session.run(query, source_uri=source_uri).single()
    if record is None:
        return []
    items = record.get("items") or []
    return [item for item in items if item is not None]


def _build_crop_node(session, source_uri: str, props: dict[str, Any]) -> GraphCropNode:
    fertilizers = [
        GraphFertilizerRecord(
            fertilizer=str(item.get("fertilizer", "")),
            apply_start_weeks_after_planting=_optional_float(
                item.get("apply_start_weeks_after_planting")
            ),
            repeat_count=_optional_int(item.get("repeat_count")),
            repeat_interval_weeks=_optional_float(item.get("repeat_interval_weeks")),
            quantity_kg_per_ha=_optional_float(item.get("quantity_kg_per_ha")),
        )
        for item in _collect_items(session, FERTILIZERS_CYPHER, source_uri=source_uri)
        if item.get("fertilizer")
    ]
    pests = [
        GraphPestRecord(
            name=str(item.get("name", "")),
            impact=_optional_str(item.get("impact")),
            solution=_optional_str(item.get("solution")),
        )
        for item in _collect_items(session, PESTS_CYPHER, source_uri=source_uri)
        if item.get("name")
    ]
    diseases = [
        GraphDiseaseRecord(
            name=str(item.get("name", "")),
            causal_agent=_optional_str(item.get("causal_agent")),
            impact=_optional_str(item.get("impact")),
            solution=_optional_str(item.get("solution")),
        )
        for item in _collect_items(session, DISEASES_CYPHER, source_uri=source_uri)
        if item.get("name")
    ]

    return GraphCropNode(
        source_uri=source_uri,
        name=str(props.get("name") or ""),
        manifest_crop_name=_optional_str(props.get("manifest_crop_name")),
        scientific_name=_optional_str(props.get("scientific_name")),
        altitude_min_m=_optional_float(props.get("altitude_min_m")),
        altitude_max_m=_optional_float(props.get("altitude_max_m")),
        temp_min_c=_optional_float(props.get("temp_min_c")),
        temp_max_c=_optional_float(props.get("temp_max_c")),
        rainfall_min_mm=_optional_float(props.get("rainfall_min_mm")),
        rainfall_max_mm=_optional_float(props.get("rainfall_max_mm")),
        ph_min=_optional_float(props.get("ph_min")),
        ph_max=_optional_float(props.get("ph_max")),
        pit_length_cm=_optional_float(props.get("pit_length_cm")),
        pit_width_cm=_optional_float(props.get("pit_width_cm")),
        row_distance_cm=_optional_float(props.get("row_distance_cm")),
        plant_distance_cm=_optional_float(props.get("plant_distance_cm")),
        expected_harvest_kg_per_ha=_optional_float(props.get("expected_harvest_kg_per_ha")),
        days_to_maturity=_optional_int(props.get("days_to_maturity")),
        nursery_period_days=_optional_int(props.get("nursery_period_days")),
        seed_amount_per_ha=_optional_float(props.get("seed_amount_per_ha")),
        seed_metric_type=_optional_str(props.get("seed_metric_type")),
        growing_areas=[
            str(item) for item in _collect_items(session, GROWING_AREAS_CYPHER, source_uri=source_uri)
        ],
        growing_seasons=[
            str(item) for item in _collect_items(session, SEASONS_CYPHER, source_uri=source_uri)
        ],
        varieties=[
            str(item) for item in _collect_items(session, VARIETIES_CYPHER, source_uri=source_uri)
        ],
        soil_types=[
            str(item) for item in _collect_items(session, SOILS_CYPHER, source_uri=source_uri)
        ],
        fertilizer_schedule=fertilizers,
        pests=pests,
        diseases=diseases,
    )


class Neo4jGraphReadStore:
    def __init__(self, driver) -> None:
        self._driver = driver

    def close(self) -> None:
        self._driver.close()

    def list_crop_summaries(self) -> list[GraphCropSummary]:
        with self._driver.session() as session:
            result = session.run(LIST_CROP_SUMMARIES_CYPHER)
            summaries: list[GraphCropSummary] = []
            for record in result:
                name = record.get("name")
                if not name:
                    continue
                summaries.append(
                    GraphCropSummary(
                        name=str(name),
                        node_count=int(record["node_count"]),
                        source_uris=[str(uri) for uri in record["source_uris"]],
                    )
                )
            return summaries

    def get_crop_detail(self, name: str) -> GraphCropDetail:
        with self._driver.session() as session:
            result = session.run(LIST_CROP_NODES_CYPHER, name=name)
            nodes = [
                _build_crop_node(session, str(record["source_uri"]), dict(record["props"]))
                for record in result
            ]
            return GraphCropDetail(name=name, nodes=nodes)
