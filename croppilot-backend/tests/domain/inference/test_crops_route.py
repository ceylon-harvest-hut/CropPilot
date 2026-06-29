"""Tests for GET /api/v1/crops (indexed crops only, no debug guard)."""

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.domains.debug.data import CropRecord
from app.domains.debug.dependencies import get_source_catalog
from app.main import app


def _mock_catalog(crops: list[CropRecord]) -> MagicMock:
    catalog = MagicMock()
    catalog.list_indexed_crops.return_value = crops
    return catalog


def test_crops_endpoint_returns_indexed_crops() -> None:
    crops = [
        CropRecord(crop_id=1, name="Pepper", botanical_name="Piper nigrum"),
        CropRecord(crop_id=2, name="ගෝවා", botanical_name=None),
    ]
    app.dependency_overrides[get_source_catalog] = lambda: _mock_catalog(crops)

    with TestClient(app) as client:
        response = client.get("/api/v1/crops")

    app.dependency_overrides.pop(get_source_catalog, None)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    names = [c["name"] for c in body["crops"]]
    assert "Pepper" in names
    assert "ගෝවා" in names


def test_crops_endpoint_returns_empty_when_nothing_indexed() -> None:
    app.dependency_overrides[get_source_catalog] = lambda: _mock_catalog([])

    with TestClient(app) as client:
        response = client.get("/api/v1/crops")

    app.dependency_overrides.pop(get_source_catalog, None)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 0
    assert body["crops"] == []


def test_crops_endpoint_has_no_debug_guard() -> None:
    """GET /crops must be accessible regardless of debug_enabled."""
    from app.infrastructure.config import Settings, get_settings

    settings = Settings(debug_enabled=False)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_source_catalog] = lambda: _mock_catalog([])

    with TestClient(app) as client:
        response = client.get("/api/v1/crops")

    app.dependency_overrides.clear()

    assert response.status_code == 200


def test_crops_response_includes_botanical_name() -> None:
    crops = [CropRecord(crop_id=1, name="Pepper", botanical_name="Piper nigrum")]
    app.dependency_overrides[get_source_catalog] = lambda: _mock_catalog(crops)

    with TestClient(app) as client:
        response = client.get("/api/v1/crops")

    app.dependency_overrides.pop(get_source_catalog, None)

    item = response.json()["crops"][0]
    assert item["botanical_name"] == "Piper nigrum"


def test_crops_response_allows_null_botanical_name() -> None:
    crops = [CropRecord(crop_id=2, name="ගෝවා", botanical_name=None)]
    app.dependency_overrides[get_source_catalog] = lambda: _mock_catalog(crops)

    with TestClient(app) as client:
        response = client.get("/api/v1/crops")

    app.dependency_overrides.pop(get_source_catalog, None)

    item = response.json()["crops"][0]
    assert item["botanical_name"] is None
