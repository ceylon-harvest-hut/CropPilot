import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.domains.ingestion.models import Crop, CropKnowledgeSource, KnowledgeSource
from app.infrastructure.repositories.db import (
    Base,
    KNOWLEDGE_SOURCE_STATUS_INDEXED,
    KNOWLEDGE_SOURCE_STATUS_PENDING,
    KNOWLEDGE_SOURCE_STATUS_PROCESSING,
)
from app.infrastructure.repositories.knowledge_source_repo import SqlKnowledgeSourceRepository


@pytest.fixture
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def repository(db_session: Session) -> SqlKnowledgeSourceRepository:
    return SqlKnowledgeSourceRepository(db_session)


def test_create_pending_creates_crop_source_and_link(
    repository: SqlKnowledgeSourceRepository,
    db_session: Session,
) -> None:
    source_id = repository.create_pending(
        origin_url="tests/fixtures/pepper.txt",
        crop_name="Pepper",
    )

    source = db_session.get(KnowledgeSource, source_id)
    crop = db_session.query(Crop).filter_by(name="Pepper").one()
    links = db_session.query(CropKnowledgeSource).all()

    assert source is not None
    assert source.status == KNOWLEDGE_SOURCE_STATUS_PENDING
    assert crop.name == "Pepper"
    assert len(links) == 1
    assert links[0].crop_id == crop.id
    assert links[0].knowledge_source_id == source_id


def test_create_pending_reuses_existing_crop(
    repository: SqlKnowledgeSourceRepository,
    db_session: Session,
) -> None:
    repository.create_pending("file:///a.txt", "Pepper")
    repository.create_pending("file:///b.txt", "Pepper")

    assert db_session.query(Crop).count() == 1
    assert db_session.query(KnowledgeSource).count() == 2


def test_update_status(repository: SqlKnowledgeSourceRepository, db_session: Session) -> None:
    source_id = repository.create_pending("file:///a.txt", "Pepper")

    repository.update_status(source_id, KNOWLEDGE_SOURCE_STATUS_PROCESSING)
    repository.update_status(source_id, KNOWLEDGE_SOURCE_STATUS_INDEXED)

    source = db_session.get(KnowledgeSource, source_id)
    assert source is not None
    assert source.status == KNOWLEDGE_SOURCE_STATUS_INDEXED
