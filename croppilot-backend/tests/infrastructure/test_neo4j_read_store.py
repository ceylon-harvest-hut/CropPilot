from unittest.mock import MagicMock

from app.domains.debug.graph_data import GraphCropDetail, GraphCropSummary
from app.infrastructure.graph.neo4j_read_store import Neo4jGraphReadStore


class _FakeRecord(dict):
    def get(self, key, default=None):
        return super().get(key, default)


class _FakeResult:
    def __init__(self, records):
        self._records = records

    def __iter__(self):
        return iter(self._records)

    def single(self):
        if not self._records:
            return None
        return self._records[0]


def _make_session(run_side_effect):
    session = MagicMock()
    session.run.side_effect = run_side_effect
    return session


def test_list_crop_summaries_aggregates_by_name() -> None:
    driver = MagicMock()
    session = MagicMock()
    driver.session.return_value.__enter__.return_value = session
    session.run.return_value = _FakeResult(
        [
            _FakeRecord(name="Cabbage", node_count=2, source_uris=["a.html", "b.html"]),
            _FakeRecord(name="Pepper", node_count=1, source_uris=["pepper.html"]),
        ]
    )

    store = Neo4jGraphReadStore(driver)
    summaries = store.list_crop_summaries()

    assert summaries == [
        GraphCropSummary(name="Cabbage", node_count=2, source_uris=["a.html", "b.html"]),
        GraphCropSummary(name="Pepper", node_count=1, source_uris=["pepper.html"]),
    ]
    query = session.run.call_args.args[0]
    assert "MATCH (c:Crop)" in query
    assert "count(c)" in query


def test_get_crop_detail_builds_nodes_with_relationships() -> None:
    def run_side_effect(query, **kwargs):
        if "WHERE c.name = $name" in query:
            return _FakeResult(
                [
                    _FakeRecord(
                        source_uri="cabbage.html",
                        props={
                            "name": "Cabbage",
                            "scientific_name": "Brassica oleracea",
                            "row_distance_cm": 60,
                        },
                    )
                ]
            )
        if "SUITABLE_IN" in query:
            return _FakeResult([_FakeRecord(items=["Matale", "Kandy"])])
        if "CULTIVATED_DURING" in query:
            return _FakeResult([_FakeRecord(items=["Yala"])])
        if "HAS_VARIETY" in query:
            return _FakeResult([_FakeRecord(items=["Green"])])
        if "THRIVES_IN" in query:
            return _FakeResult([_FakeRecord(items=["Loam"])])
        if "REQUIRES" in query:
            return _FakeResult(
                [
                    _FakeRecord(
                        items=[
                            {
                                "fertilizer": "Urea",
                                "apply_start_weeks_after_planting": 2.0,
                                "repeat_count": 1,
                                "repeat_interval_weeks": None,
                                "quantity_kg_per_ha": 50.0,
                            }
                        ]
                    )
                ]
            )
        if "HARMED_BY" in query:
            return _FakeResult(
                [
                    _FakeRecord(
                        items=[{"name": "Aphid", "impact": "Leaf curl", "solution": "Spray"}]
                    )
                ]
            )
        if "INFECTED_BY" in query:
            return _FakeResult(
                [
                    _FakeRecord(
                        items=[
                            {
                                "name": "Black rot",
                                "causal_agent": "Xanthomonas",
                                "impact": "Wilting",
                                "solution": "Rotate",
                            }
                        ]
                    )
                ]
            )
        raise AssertionError(f"Unexpected query: {query}")

    driver = MagicMock()
    session = _make_session(run_side_effect)
    driver.session.return_value.__enter__.return_value = session

    store = Neo4jGraphReadStore(driver)
    detail = store.get_crop_detail("Cabbage")

    assert detail.name == "Cabbage"
    assert len(detail.nodes) == 1
    node = detail.nodes[0]
    assert node.source_uri == "cabbage.html"
    assert node.scientific_name == "Brassica oleracea"
    assert node.row_distance_cm == 60.0
    assert node.growing_areas == ["Matale", "Kandy"]
    assert node.growing_seasons == ["Yala"]
    assert node.varieties == ["Green"]
    assert node.soil_types == ["Loam"]
    assert len(node.fertilizer_schedule) == 1
    assert node.fertilizer_schedule[0].fertilizer == "Urea"
    assert len(node.pests) == 1
    assert node.pests[0].name == "Aphid"
    assert len(node.diseases) == 1
    assert node.diseases[0].causal_agent == "Xanthomonas"


def test_get_crop_detail_returns_multiple_nodes_for_same_name() -> None:
    def run_side_effect(query, **kwargs):
        if "WHERE c.name = $name" in query:
            return _FakeResult(
                [
                    _FakeRecord(source_uri="a.html", props={"name": "Cabbage"}),
                    _FakeRecord(source_uri="b.html", props={"name": "Cabbage"}),
                ]
            )
        return _FakeResult([_FakeRecord(items=[])])

    driver = MagicMock()
    session = _make_session(run_side_effect)
    driver.session.return_value.__enter__.return_value = session

    store = Neo4jGraphReadStore(driver)
    detail = store.get_crop_detail("Cabbage")

    assert detail.name == "Cabbage"
    assert len(detail.nodes) == 2
    assert {node.source_uri for node in detail.nodes} == {"a.html", "b.html"}
    assert all(node.name == "Cabbage" for node in detail.nodes)
