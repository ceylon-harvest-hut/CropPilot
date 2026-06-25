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

    def override_get_settings() -> Settings:
        return settings

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = override_get_settings

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_ingest_endpoint(client: TestClient) -> None:
    response = client.post(
        "/api/v1/ingest",
        json={
            "source_uri": str(FIXTURES_DIR / "pepper.txt"),
            "crop_name": "Pepper",
        },
    )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "INDEXED"
    assert body["chunk_count"] >= 10
    assert body["source_id"] > 0
