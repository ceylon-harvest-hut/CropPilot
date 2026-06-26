from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.domains.ingestion.persistence import SourceAlreadyIngestedError
from app.domains.ingestion.service import IngestionService
from app.infrastructure.config import Settings
from app.infrastructure.factories import (
    build_chunker,
    build_document_pipeline,
    build_embedder,
    build_vector_store,
)
from app.infrastructure.repositories.db import Base, KNOWLEDGE_SOURCE_STATUS_INDEXED
from app.infrastructure.repositories.knowledge_source_repo import SqlKnowledgeSourceRepository

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures"


@pytest.fixture
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def ingestion_service(tmp_path: Path, db_session: Session) -> IngestionService:
    settings = Settings(
        default_chunker="section",
        embedding_backend="fast",
        chroma_persist_dir=str(tmp_path / "chroma"),
    )
    return IngestionService(
        pipeline=build_document_pipeline(settings),
        chunker=build_chunker(settings),
        embedder=build_embedder(settings),
        vector_store=build_vector_store(settings),
        source_repository=SqlKnowledgeSourceRepository(db_session),
        default_loader=settings.default_loader,
    )


def test_ingest_pepper_txt(ingestion_service: IngestionService, db_session: Session) -> None:
    source_uri = str(FIXTURES_DIR / "pepper.txt")
    result = ingestion_service.ingest(source_uri, crop_tag="Pepper")

    assert result.chunk_count >= 10
    assert result.status == KNOWLEDGE_SOURCE_STATUS_INDEXED
    assert result.source_id > 0
    assert ingestion_service._vector_store.count() == result.chunk_count

    from app.domains.ingestion.models import KnowledgeSource

    source = db_session.get(KnowledgeSource, result.source_id)
    assert source is not None
    assert source.status == KNOWLEDGE_SOURCE_STATUS_INDEXED


def test_ingest_replace_existing_reuses_source_and_replaces_vectors(
    ingestion_service: IngestionService,
) -> None:
    source_uri = str(FIXTURES_DIR / "pepper.txt")
    first = ingestion_service.ingest(source_uri, crop_tag="Pepper")

    with pytest.raises(SourceAlreadyIngestedError):
        ingestion_service.ingest(source_uri, crop_tag="Pepper")

    second = ingestion_service.ingest(source_uri, crop_tag="Pepper", replace_existing=True)

    assert second.source_id == first.source_id
    assert ingestion_service._vector_store.count() == second.chunk_count
