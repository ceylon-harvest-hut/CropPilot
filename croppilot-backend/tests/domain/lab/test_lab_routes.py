from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.infrastructure.config import Settings, get_settings
from app.infrastructure.repositories.db import Base, get_db
from app.main import app

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures"
PEPPER_FILE = str(FIXTURES_DIR / "pepper.txt")


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    settings = Settings(
        default_chunker="section",
        embedding_backend="fast",
        chroma_persist_dir=str(tmp_path / "chroma"),
    )

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = lambda: settings

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


# ---------- options ----------

def test_options_returns_all_components(client: TestClient) -> None:
    response = client.get("/api/v1/lab/options")
    assert response.status_code == 200
    body = response.json()
    assert "text" in body["loaders"]
    assert "section" in body["chunkers"]
    assert "recursive" in body["chunkers"]
    assert "fast" in body["embedders"]


# ---------- load ----------

def test_load_text_file(client: TestClient) -> None:
    response = client.post(
        "/api/v1/lab/load",
        json={"source_uri": PEPPER_FILE, "loader": "text"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["media_type"] == "text/plain"
    assert body["char_count"] > 0
    assert body["line_count"] > 0
    assert len(body["text"]) == body["char_count"]


def test_load_unknown_loader_returns_422(client: TestClient) -> None:
    response = client.post(
        "/api/v1/lab/load",
        json={"source_uri": PEPPER_FILE, "loader": "pdf"},
    )
    assert response.status_code == 422


def test_load_missing_file_returns_404(client: TestClient) -> None:
    response = client.post(
        "/api/v1/lab/load",
        json={"source_uri": "/nonexistent/path/file.txt", "loader": "text"},
    )
    assert response.status_code == 404


# ---------- chunk ----------

SAMPLE_TEXT = """Introduction

This is an introduction.

Cultivation

Pepper grows in tropical climates.

Diseases

Pepper can suffer from various diseases.
"""


def test_chunk_section_strategy(client: TestClient) -> None:
    response = client.post(
        "/api/v1/lab/chunk",
        json={"text": SAMPLE_TEXT, "crop_name": "Pepper", "chunker": "section"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["chunk_count"] >= 2
    for i, chunk in enumerate(body["chunks"]):
        assert chunk["index"] == i
        assert chunk["section_name"]
        assert chunk["char_count"] == len(chunk["text"])


def test_chunk_recursive_strategy(client: TestClient) -> None:
    response = client.post(
        "/api/v1/lab/chunk",
        json={
            "text": SAMPLE_TEXT * 10,
            "crop_name": "Pepper",
            "chunker": "recursive",
            "chunk_size": 100,
            "chunk_overlap": 10,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["chunk_count"] >= 2


def test_chunk_unknown_chunker_returns_422(client: TestClient) -> None:
    response = client.post(
        "/api/v1/lab/chunk",
        json={"text": SAMPLE_TEXT, "crop_name": "Pepper", "chunker": "unknown"},
    )
    assert response.status_code == 422


def test_chunk_is_stateless_no_db_writes(client: TestClient) -> None:
    """Chunking endpoint must not write to the database."""
    client.post(
        "/api/v1/lab/chunk",
        json={"text": SAMPLE_TEXT, "crop_name": "Pepper", "chunker": "section"},
    )
    # verify nothing was saved — debug/sources should be empty
    sources_response = client.get("/api/v1/debug/sources")
    assert sources_response.status_code == 200
    assert sources_response.json()["total"] == 0


# ---------- commit ----------

def test_commit_saves_to_db(client: TestClient, tmp_path: Path) -> None:
    chunks_response = client.post(
        "/api/v1/lab/chunk",
        json={"text": SAMPLE_TEXT, "crop_name": "Pepper", "chunker": "section"},
    )
    chunks = chunks_response.json()["chunks"]

    response = client.post(
        "/api/v1/lab/commit",
        json={
            "source_uri": PEPPER_FILE,
            "crop_name": "Pepper",
            "chunks": chunks,
            "embedder": "fast",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "INDEXED"
    assert body["chunk_count"] == len(chunks)
    assert body["source_id"] > 0


def test_commit_empty_chunks_returns_422(client: TestClient) -> None:
    response = client.post(
        "/api/v1/lab/commit",
        json={
            "source_uri": PEPPER_FILE,
            "crop_name": "Pepper",
            "chunks": [],
            "embedder": "fast",
        },
    )
    assert response.status_code == 422


def test_full_lab_flow(client: TestClient) -> None:
    """End-to-end: load → chunk → commit."""
    load_resp = client.post(
        "/api/v1/lab/load",
        json={"source_uri": PEPPER_FILE, "loader": "text"},
    )
    assert load_resp.status_code == 200
    text = load_resp.json()["text"]

    chunk_resp = client.post(
        "/api/v1/lab/chunk",
        json={"text": text, "crop_name": "Pepper", "chunker": "section"},
    )
    assert chunk_resp.status_code == 200
    chunks = chunk_resp.json()["chunks"]
    assert len(chunks) > 0

    commit_resp = client.post(
        "/api/v1/lab/commit",
        json={
            "source_uri": PEPPER_FILE,
            "crop_name": "Pepper",
            "chunks": chunks,
            "embedder": "fast",
        },
    )
    assert commit_resp.status_code == 201
    assert commit_resp.json()["chunk_count"] == len(chunks)
