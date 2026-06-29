from unittest.mock import MagicMock

from app.domains.graph.data import ExtractedCropKnowledge
from app.infrastructure.graph.neo4j_store import Neo4jGraphStore


def test_neo4j_store_upsert_runs_scalar_and_relationship_queries() -> None:
    driver = MagicMock()
    session = MagicMock()
    driver.session.return_value.__enter__.return_value = session

    store = Neo4jGraphStore(driver)
    extracted = ExtractedCropKnowledge(
        crop_name="Pepper",
        growing_areas=["Matale"],
        pests=[],
    )
    store.upsert_crop(extracted, source_uri="pepper.html", crop_tag="Pepper")

    assert session.run.call_count >= 2
    first_query = session.run.call_args_list[0].args[0]
    assert "MERGE (c:Crop" in first_query


def test_neo4j_store_delete_and_count() -> None:
    driver = MagicMock()
    session = MagicMock()
    driver.session.return_value.__enter__.return_value = session
    summary = MagicMock()
    summary.counters.nodes_deleted = 2
    session.run.return_value.consume.return_value = summary
    session.run.return_value.single.return_value = {"n": 1}

    store = Neo4jGraphStore(driver)
    assert store.delete_by_source_uri("pepper.html") == 2
    assert store.count_by_source_uri("pepper.html") == 1
