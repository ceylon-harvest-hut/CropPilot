from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.domains.debug.data import CropRecord, SourceRecord, StoredChunk
from app.domains.debug.dependencies import get_chunk_catalog, get_source_catalog
from app.infrastructure.config import Settings, get_settings
from app.main import app

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures"


def _mock_chunk_catalog(chunks: list[StoredChunk], total: int) -> MagicMock:
    catalog = MagicMock()
    catalog.list_chunks.return_value = (chunks, total)
    return catalog


def _mock_source_catalog(
    sources: list[SourceRecord] | None = None,
    crops: list[CropRecord] | None = None,
    source_total: int | None = None,
) -> MagicMock:
    catalog = MagicMock()
    source_list = sources or []
    total = source_total if source_total is not None else len(source_list)
    catalog.list_sources.return_value = (source_list, total)
    catalog.list_crops.return_value = crops or []
    return catalog


@pytest.fixture
def client() -> TestClient:
    settings = Settings(debug_enabled=True)
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_list_chunks_returns_200(client: TestClient, tmp_path: Path) -> None:
    chunk = StoredChunk(
        chunk_id="c1",
        crop_tag="Pepper",
        source_uri="pepper.txt",
        section_name="Introduction",
        page_number=0,
        text_preview="Pepper is a tropical crop.",
    )
    app.dependency_overrides[get_chunk_catalog] = lambda: _mock_chunk_catalog([chunk], 1)

    response = client.get("/api/v1/debug/chunks")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["limit"] == 20
    assert body["offset"] == 0
    assert body["chunks"][0]["chunk_id"] == "c1"
    assert body["chunks"][0]["crop_tag"] == "Pepper"

    app.dependency_overrides.pop(get_chunk_catalog, None)


def test_list_chunks_passes_filters(client: TestClient) -> None:
    catalog = _mock_chunk_catalog([], 0)
    app.dependency_overrides[get_chunk_catalog] = lambda: catalog

    client.get("/api/v1/debug/chunks?crop_name=Pepper&source_uri=pepper.txt&limit=5&offset=10")

    catalog.list_chunks.assert_called_once_with(
        crop_tag="Pepper",
        source_uri="pepper.txt",
        limit=5,
        offset=10,
    )
    app.dependency_overrides.pop(get_chunk_catalog, None)


def test_list_sources_returns_200(client: TestClient) -> None:
    source = SourceRecord(
        source_id=1,
        origin_url="pepper.txt",
        status="INDEXED",
        crop_names=["Pepper"],
    )
    app.dependency_overrides[get_source_catalog] = lambda: _mock_source_catalog(sources=[source])

    response = client.get("/api/v1/debug/sources")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["limit"] == 20
    assert body["offset"] == 0
    assert body["sources"][0]["origin_url"] == "pepper.txt"

    app.dependency_overrides.pop(get_source_catalog, None)


def test_list_sources_passes_pagination(client: TestClient) -> None:
    catalog = _mock_source_catalog()
    app.dependency_overrides[get_source_catalog] = lambda: catalog

    client.get("/api/v1/debug/sources?crop_name=Pepper&limit=10&offset=5")

    catalog.list_sources.assert_called_once_with(
        crop_name="Pepper",
        status=None,
        limit=10,
        offset=5,
    )
    app.dependency_overrides.pop(get_source_catalog, None)


def test_list_crops_returns_200(client: TestClient) -> None:
    crop = CropRecord(crop_id=1, name="Pepper", botanical_name=None)
    app.dependency_overrides[get_source_catalog] = lambda: _mock_source_catalog(crops=[crop])

    response = client.get("/api/v1/debug/crops")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["crops"][0]["name"] == "Pepper"

    app.dependency_overrides.pop(get_source_catalog, None)


def test_debug_disabled_returns_404() -> None:
    settings = Settings(debug_enabled=False)
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as c:
        response = c.get("/api/v1/debug/chunks")
    app.dependency_overrides.clear()

    assert response.status_code == 404
