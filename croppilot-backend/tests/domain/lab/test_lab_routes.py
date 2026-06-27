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

SAMPLE_DOCUMENTS = [
    {
        "text": (
            "Introduction\n\nThis is an introduction.\n\n"
            "Cultivation\n\nPepper grows in tropical climates.\n\n"
            "Diseases\n\nPepper can suffer from various diseases.\n"
        ),
        "metadata": {"source_uri": "test", "media_type": "text/plain"},
    }
]


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
        embedding_backend="bge_small",
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
    assert "file" in body["source_types"]
    assert "web_url" in body["source_types"]
    loader_names = [loader["name"] for loader in body["loaders"]]
    assert "text" in loader_names
    assert "docling" in loader_names
    assert "html_plain" in loader_names
    assert "dea_gov_lk" in loader_names
    assert "dea_gov_lk_si" in loader_names
    assert "doa_hordi" in loader_names
    assert "web" not in loader_names
    assert "web_md" not in loader_names
    chunker_names = [chunker["name"] for chunker in body["chunkers"]]
    assert "section" in chunker_names
    assert "recursive" in chunker_names
    assert "dea_gov_lk" in chunker_names
    assert "dea_gov_lk_si" in chunker_names
    assert "doa_hordi" in chunker_names
    assert "dea_hybrid" in chunker_names
    assert "manual" in chunker_names
    assert "bge_small" in body["embedders"]
    assert "e5_multilingual" in body["embedders"]


# ---------- load ----------

def test_load_text_file(client: TestClient) -> None:
    response = client.post(
        "/api/v1/lab/load",
        json={"source_uri": PEPPER_FILE, "source_type": "file", "loader": "text"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["media_type"] == "text/plain"
    assert body["char_count"] > 0
    assert body["line_count"] > 0
    # documents list is non-empty and combined char count matches
    assert len(body["documents"]) >= 1
    combined = "\n\n".join(d["text"] for d in body["documents"])
    assert len(combined) == body["char_count"]


def test_load_unknown_loader_returns_422(client: TestClient) -> None:
    response = client.post(
        "/api/v1/lab/load",
        json={"source_uri": PEPPER_FILE, "loader": "pdf", "source_type": "file"},
    )
    assert response.status_code == 422


def test_load_loader_media_type_mismatch_returns_422(client: TestClient) -> None:
    """html_plain loader does not support text/plain from a .txt file."""
    response = client.post(
        "/api/v1/lab/load",
        json={
            "source_uri": PEPPER_FILE,
            "source_type": "file",
            "loader": "html_plain",
        },
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["loader"] == "html_plain"
    assert "text/plain" in detail["media_type"]


def test_load_file_path_with_web_source_type_returns_422(client: TestClient) -> None:
    response = client.post(
        "/api/v1/lab/load",
        json={
            "source_uri": PEPPER_FILE,
            "source_type": "web_url",
            "loader": "html_plain",
        },
    )
    assert response.status_code == 422


def test_load_missing_file_returns_404(client: TestClient) -> None:
    response = client.post(
        "/api/v1/lab/load",
        json={"source_uri": "/nonexistent/path/file.txt", "loader": "text", "source_type": "file"},
    )
    assert response.status_code == 404


# ---------- chunk ----------

def test_chunk_section_strategy(client: TestClient) -> None:
    response = client.post(
        "/api/v1/lab/chunk",
        json={"documents": SAMPLE_DOCUMENTS, "crop_name": "Pepper", "chunker": "section"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["chunk_count"] >= 2
    for i, chunk in enumerate(body["chunks"]):
        assert chunk["index"] == i
        assert chunk["section_name"]
        assert chunk["char_count"] == len(chunk["text"])


def test_chunk_recursive_strategy(client: TestClient) -> None:
    big_doc = dict(SAMPLE_DOCUMENTS[0])
    big_doc = {**big_doc, "text": big_doc["text"] * 10}
    response = client.post(
        "/api/v1/lab/chunk",
        json={
            "documents": [big_doc],
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
        json={"documents": SAMPLE_DOCUMENTS, "crop_name": "Pepper", "chunker": "unknown"},
    )
    assert response.status_code == 422


def test_chunk_is_stateless_no_db_writes(client: TestClient) -> None:
    """Chunking endpoint must not write to the database."""
    client.post(
        "/api/v1/lab/chunk",
        json={"documents": SAMPLE_DOCUMENTS, "crop_name": "Pepper", "chunker": "section"},
    )
    sources_response = client.get("/api/v1/debug/sources")
    assert sources_response.status_code == 200
    assert sources_response.json()["total"] == 0


# ---------- commit ----------

@pytest.mark.slow
def test_commit_saves_to_db(client: TestClient, tmp_path: Path) -> None:
    chunks_response = client.post(
        "/api/v1/lab/chunk",
        json={"documents": SAMPLE_DOCUMENTS, "crop_name": "Pepper", "chunker": "section"},
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


@pytest.mark.slow
def test_full_lab_flow(client: TestClient) -> None:
    """End-to-end: load → chunk → commit."""
    load_resp = client.post(
        "/api/v1/lab/load",
        json={"source_uri": PEPPER_FILE, "source_type": "file", "loader": "text"},
    )
    assert load_resp.status_code == 200
    documents = load_resp.json()["documents"]
    assert len(documents) >= 1

    chunk_resp = client.post(
        "/api/v1/lab/chunk",
        json={"documents": documents, "crop_name": "Pepper", "chunker": "section"},
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


def _commit_chunks(client: TestClient, chunks: list[dict], *, replace_existing: bool = False) -> dict:
    response = client.post(
        "/api/v1/lab/commit",
        json={
            "source_uri": PEPPER_FILE,
            "crop_name": "Pepper",
            "chunks": chunks,
            "embedder": "fast",
            "replace_existing": replace_existing,
        },
    )
    return response


@pytest.mark.slow
def test_source_exists_before_and_after_commit(client: TestClient) -> None:
    missing = client.get("/api/v1/lab/sources/exists", params={"source_uri": PEPPER_FILE})
    assert missing.status_code == 200
    assert missing.json()["exists"] is False

    chunks = client.post(
        "/api/v1/lab/chunk",
        json={"documents": SAMPLE_DOCUMENTS, "crop_name": "Pepper", "chunker": "section"},
    ).json()["chunks"]
    _commit_chunks(client, chunks)

    found = client.get("/api/v1/lab/sources/exists", params={"source_uri": PEPPER_FILE})
    assert found.status_code == 200
    body = found.json()
    assert body["exists"] is True
    assert body["source_id"] > 0
    assert body["chunk_count"] == len(chunks)
    assert body["status"] == "INDEXED"
    assert "Pepper" in body["crop_names"]


@pytest.mark.slow
def test_commit_duplicate_without_replace_returns_409(client: TestClient) -> None:
    chunks = client.post(
        "/api/v1/lab/chunk",
        json={"documents": SAMPLE_DOCUMENTS, "crop_name": "Pepper", "chunker": "section"},
    ).json()["chunks"]
    first = _commit_chunks(client, chunks)
    assert first.status_code == 201

    second = _commit_chunks(client, chunks)
    assert second.status_code == 409
    detail = second.json()["detail"]
    assert detail["source_id"] > 0
    assert detail["chunk_count"] == len(chunks)


@pytest.mark.slow
def test_commit_replace_existing_succeeds(client: TestClient) -> None:
    chunks = client.post(
        "/api/v1/lab/chunk",
        json={"documents": SAMPLE_DOCUMENTS, "crop_name": "Pepper", "chunker": "section"},
    ).json()["chunks"]
    first = _commit_chunks(client, chunks)
    assert first.status_code == 201
    first_source_id = first.json()["source_id"]

    smaller_chunks = chunks[:1]
    replaced = _commit_chunks(client, smaller_chunks, replace_existing=True)
    assert replaced.status_code == 201
    body = replaced.json()
    assert body["replaced"] is True
    assert body["previous_chunk_count"] == len(chunks)
    assert body["chunk_count"] == 1
    assert body["source_id"] == first_source_id

    found = client.get("/api/v1/lab/sources/exists", params={"source_uri": PEPPER_FILE})
    assert found.json()["chunk_count"] == 1
