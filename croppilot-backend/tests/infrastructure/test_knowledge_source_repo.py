import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.domains.ingestion.models import Crop, CropKnowledgeSource, KnowledgeSource
from app.infrastructure.repositories.db import (
    Base,
    KNOWLEDGE_SOURCE_STATUS_GRAPH_INDEXED,
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


def test_find_by_origin_url_returns_none_when_missing(
    repository: SqlKnowledgeSourceRepository,
) -> None:
    assert repository.find_by_origin_url("missing.txt") is None


def test_find_by_origin_url_returns_existing_source(
    repository: SqlKnowledgeSourceRepository,
) -> None:
    source_id = repository.create_pending("tests/fixtures/pepper.txt", "Pepper")

    existing = repository.find_by_origin_url("tests/fixtures/pepper.txt")

    assert existing is not None
    assert existing.source_id == source_id
    assert existing.status == KNOWLEDGE_SOURCE_STATUS_PENDING
    assert existing.crop_names == ["Pepper"]


def test_prepare_for_reingest_reuses_source_row(
    repository: SqlKnowledgeSourceRepository,
    db_session: Session,
) -> None:
    source_id = repository.create_pending("tests/fixtures/pepper.txt", "Pepper")
    repository.update_status(source_id, KNOWLEDGE_SOURCE_STATUS_INDEXED)

    reused_id = repository.prepare_for_reingest("tests/fixtures/pepper.txt", "Pepper")

    assert reused_id == source_id
    assert db_session.query(KnowledgeSource).count() == 1
    source = db_session.get(KnowledgeSource, reused_id)
    assert source is not None
    assert source.status == KNOWLEDGE_SOURCE_STATUS_PENDING


def test_prepare_for_reingest_adds_crop_link_for_new_crop(
    repository: SqlKnowledgeSourceRepository,
    db_session: Session,
) -> None:
    source_id = repository.create_pending("tests/fixtures/pepper.txt", "Pepper")

    reused_id = repository.prepare_for_reingest("tests/fixtures/pepper.txt", "Tomato")

    assert reused_id == source_id
    assert db_session.query(Crop).count() == 2
    assert db_session.query(CropKnowledgeSource).count() == 2


def test_ensure_crop_link_adds_missing_crop_link(
    repository: SqlKnowledgeSourceRepository,
    db_session: Session,
) -> None:
    source_id = repository.create_pending("tests/fixtures/pepper.txt", "Pepper")

    repository.ensure_crop_link(source_id, "Tomato")

    assert db_session.query(Crop).count() == 2
    assert db_session.query(CropKnowledgeSource).count() == 2
    links = db_session.query(CropKnowledgeSource).all()
    linked_crops = {db_session.get(Crop, link.crop_id).name for link in links}
    assert linked_crops == {"Pepper", "Tomato"}


def test_ensure_crop_link_is_idempotent(
    repository: SqlKnowledgeSourceRepository,
    db_session: Session,
) -> None:
    source_id = repository.create_pending("tests/fixtures/pepper.txt", "Pepper")

    repository.ensure_crop_link(source_id, "Pepper")
    repository.ensure_crop_link(source_id, "Pepper")

    assert db_session.query(Crop).count() == 1
    assert db_session.query(CropKnowledgeSource).count() == 1


def test_reset_graph_indexed_sources_only_affects_graph_indexed(
    repository: SqlKnowledgeSourceRepository,
    db_session: Session,
) -> None:
    graph_id = repository.create_pending("https://example.com/a", "Crop A")
    vector_id = repository.create_pending("https://example.com/b", "Crop B")
    pending_id = repository.create_pending("https://example.com/c", "Crop C")
    repository.update_status(graph_id, KNOWLEDGE_SOURCE_STATUS_GRAPH_INDEXED)
    repository.update_status(vector_id, KNOWLEDGE_SOURCE_STATUS_INDEXED)

    reset_count = repository.reset_graph_indexed_sources()

    assert reset_count == 1
    assert db_session.get(KnowledgeSource, graph_id).status == KNOWLEDGE_SOURCE_STATUS_PENDING
    assert db_session.get(KnowledgeSource, vector_id).status == KNOWLEDGE_SOURCE_STATUS_INDEXED
    assert db_session.get(KnowledgeSource, pending_id).status == KNOWLEDGE_SOURCE_STATUS_PENDING
