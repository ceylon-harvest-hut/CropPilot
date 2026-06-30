from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.domains.debug.graph_data import (
    GraphCropDetail,
    GraphCropNode,
    GraphCropSummary,
    GraphFertilizerRecord,
    GraphPestRecord,
)
from app.domains.debug.dependencies import get_graph_read_catalog
from app.infrastructure.config import Settings, get_settings
from app.main import app


def _mock_graph_catalog(
    summaries: list[GraphCropSummary] | None = None,
    detail: GraphCropDetail | None = None,
    *,
    list_raises: Exception | None = None,
    detail_raises: Exception | None = None,
) -> MagicMock:
    catalog = MagicMock()
    if list_raises is not None:
        catalog.list_crop_summaries.side_effect = list_raises
    else:
        catalog.list_crop_summaries.return_value = summaries or []
    if detail_raises is not None:
        catalog.get_crop_detail.side_effect = detail_raises
    else:
        catalog.get_crop_detail.return_value = detail or GraphCropDetail(name="", nodes=[])
    return catalog


@pytest.fixture
def client() -> TestClient:
    settings = Settings(debug_enabled=True)
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_list_graph_crops_returns_200(client: TestClient) -> None:
    summaries = [
        GraphCropSummary(name="Cabbage", node_count=2, source_uris=["a.html", "b.html"]),
        GraphCropSummary(name="Pepper", node_count=1, source_uris=["pepper.html"]),
    ]
    app.dependency_overrides[get_graph_read_catalog] = lambda: _mock_graph_catalog(summaries)

    response = client.get("/api/v1/debug/graph/crops")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["crops"][0]["name"] == "Cabbage"
    assert body["crops"][0]["node_count"] == 2
    assert body["crops"][0]["source_uris"] == ["a.html", "b.html"]

    app.dependency_overrides.pop(get_graph_read_catalog, None)


def test_get_graph_crop_detail_returns_200(client: TestClient) -> None:
    node = GraphCropNode(
        source_uri="pepper.html",
        name="Pepper",
        scientific_name="Capsicum annuum",
        row_distance_cm=45.0,
        growing_areas=["Matale"],
        growing_seasons=["Maha"],
        varieties=["MI-2"],
        soil_types=["Sandy loam"],
        fertilizer_schedule=[
            GraphFertilizerRecord(fertilizer="Urea", quantity_kg_per_ha=25.0)
        ],
        pests=[GraphPestRecord(name="Thrips", impact="Leaf damage")],
    )
    detail = GraphCropDetail(name="Pepper", nodes=[node])
    catalog = _mock_graph_catalog(detail=detail)
    app.dependency_overrides[get_graph_read_catalog] = lambda: catalog

    response = client.get("/api/v1/debug/graph/crops/Pepper")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Pepper"
    assert len(body["nodes"]) == 1
    assert body["nodes"][0]["source_uri"] == "pepper.html"
    assert body["nodes"][0]["growing_areas"] == ["Matale"]
    assert body["nodes"][0]["fertilizer_schedule"][0]["fertilizer"] == "Urea"
    catalog.get_crop_detail.assert_called_once_with("Pepper")

    app.dependency_overrides.pop(get_graph_read_catalog, None)


def test_get_graph_crop_detail_unknown_name_returns_empty_nodes(client: TestClient) -> None:
    catalog = _mock_graph_catalog(detail=GraphCropDetail(name="Unknown", nodes=[]))
    app.dependency_overrides[get_graph_read_catalog] = lambda: catalog

    response = client.get("/api/v1/debug/graph/crops/Unknown")

    assert response.status_code == 200
    assert response.json() == {"name": "Unknown", "nodes": []}

    app.dependency_overrides.pop(get_graph_read_catalog, None)


def test_graph_debug_disabled_returns_404() -> None:
    settings = Settings(debug_enabled=False)
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as c:
        assert c.get("/api/v1/debug/graph/crops").status_code == 404
        assert c.get("/api/v1/debug/graph/crops/Pepper").status_code == 404
    app.dependency_overrides.clear()


def test_graph_read_failure_returns_503(client: TestClient) -> None:
    app.dependency_overrides[get_graph_read_catalog] = lambda: _mock_graph_catalog(
        list_raises=RuntimeError("Neo4j down")
    )

    response = client.get("/api/v1/debug/graph/crops")

    assert response.status_code == 503
    assert "Graph read failed" in response.json()["detail"]

    app.dependency_overrides.pop(get_graph_read_catalog, None)
