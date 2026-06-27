from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import pytest

from app.domains.ingestion.chunker import BaseChunker
from app.domains.ingestion.service import IngestionService
from app.infrastructure.config import Settings
from app.infrastructure.factories import build_ingestion_service
from app.infrastructure.repositories.db import Base


def test_build_chunker_section() -> None:
    from app.infrastructure.factories import build_chunker

    chunker = build_chunker(Settings(default_chunker="section"))
    assert isinstance(chunker, BaseChunker)


def test_build_chunker_recursive() -> None:
    from app.infrastructure.factories import build_chunker

    chunker = build_chunker(Settings(default_chunker="recursive"))
    assert isinstance(chunker, BaseChunker)


@pytest.mark.slow
def test_build_ingestion_service() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()

    service = build_ingestion_service(Settings(), session)
    assert isinstance(service, IngestionService)
