import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.repositories.db import Base, KNOWLEDGE_SOURCE_STATUS_INDEXED
from app.infrastructure.repositories.debug_catalog_repo import SqlDebugCatalogRepository
from app.infrastructure.repositories.knowledge_source_repo import SqlKnowledgeSourceRepository


@pytest.fixture
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def seeded_session(db_session: Session) -> Session:
    ingest_repo = SqlKnowledgeSourceRepository(db_session)
    source_id = ingest_repo.create_pending("pepper.txt", "Pepper")
    ingest_repo.update_status(source_id, KNOWLEDGE_SOURCE_STATUS_INDEXED)
    ingest_repo.create_pending("tomato.txt", "Tomato")
    return db_session


def test_list_crops_returns_all(seeded_session: Session) -> None:
    repo = SqlDebugCatalogRepository(seeded_session)
    crops = repo.list_crops()
    names = [c.name for c in crops]
    assert "Pepper" in names
    assert "Tomato" in names


def test_list_crops_fields(seeded_session: Session) -> None:
    repo = SqlDebugCatalogRepository(seeded_session)
    crops = repo.list_crops()
    for crop in crops:
        assert crop.crop_id > 0
        assert crop.name
        assert crop.botanical_name is None


def test_list_sources_returns_all(seeded_session: Session) -> None:
    repo = SqlDebugCatalogRepository(seeded_session)
    sources, total = repo.list_sources(crop_name=None, status=None)
    assert len(sources) == 2
    assert total == 2


def test_list_sources_pagination(seeded_session: Session) -> None:
    repo = SqlDebugCatalogRepository(seeded_session)
    page1, total = repo.list_sources(limit=1, offset=0)
    page2, _ = repo.list_sources(limit=1, offset=1)
    assert total == 2
    assert len(page1) == 1
    assert len(page2) == 1
    assert page1[0].source_id != page2[0].source_id


def test_list_sources_filter_by_crop(seeded_session: Session) -> None:
    repo = SqlDebugCatalogRepository(seeded_session)
    sources, total = repo.list_sources(crop_name="Pepper", status=None)
    assert len(sources) == 1
    assert total == 1
    assert sources[0].origin_url == "pepper.txt"
    assert "Pepper" in sources[0].crop_names


def test_list_sources_filter_by_status(seeded_session: Session) -> None:
    repo = SqlDebugCatalogRepository(seeded_session)
    indexed, indexed_total = repo.list_sources(crop_name=None, status="INDEXED")
    pending, pending_total = repo.list_sources(crop_name=None, status="PENDING")
    assert len(indexed) == 1
    assert indexed_total == 1
    assert indexed[0].origin_url == "pepper.txt"
    assert len(pending) == 1
    assert pending_total == 1
    assert pending[0].origin_url == "tomato.txt"


def test_list_sources_includes_crop_names(seeded_session: Session) -> None:
    repo = SqlDebugCatalogRepository(seeded_session)
    sources, _ = repo.list_sources(crop_name=None, status=None)
    source_map = {s.origin_url: s for s in sources}
    assert "Pepper" in source_map["pepper.txt"].crop_names
    assert "Tomato" in source_map["tomato.txt"].crop_names


def test_list_indexed_crops_excludes_pending(seeded_session: Session) -> None:
    """Only crops with at least one INDEXED source should be returned."""
    repo = SqlDebugCatalogRepository(seeded_session)
    crops = repo.list_indexed_crops()
    names = [c.name for c in crops]
    # Pepper has an INDEXED source; Tomato is still PENDING
    assert "Pepper" in names
    assert "Tomato" not in names


def test_list_indexed_crops_returns_distinct(seeded_session: Session) -> None:
    """A crop with multiple indexed sources should appear only once."""
    ingest_repo = SqlKnowledgeSourceRepository(seeded_session)
    source2 = ingest_repo.create_pending("pepper2.txt", "Pepper")
    ingest_repo.update_status(source2, KNOWLEDGE_SOURCE_STATUS_INDEXED)

    repo = SqlDebugCatalogRepository(seeded_session)
    crops = repo.list_indexed_crops()
    pepper_entries = [c for c in crops if c.name == "Pepper"]
    assert len(pepper_entries) == 1


def test_list_indexed_crops_ordered_by_name(seeded_session: Session) -> None:
    """Results should be alphabetically ordered."""
    ingest_repo = SqlKnowledgeSourceRepository(seeded_session)
    source_t = ingest_repo.create_pending("tomato2.txt", "Tomato")
    ingest_repo.update_status(source_t, KNOWLEDGE_SOURCE_STATUS_INDEXED)

    repo = SqlDebugCatalogRepository(seeded_session)
    crops = repo.list_indexed_crops()
    names = [c.name for c in crops]
    assert names == sorted(names)
