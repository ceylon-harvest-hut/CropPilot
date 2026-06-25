from fastapi import Depends
from sqlalchemy.orm import Session

from app.domains.debug.repositories import ChunkCatalogRepository, SourceCatalogRepository
from app.infrastructure.config import Settings, get_settings
from app.infrastructure.factories import build_chunk_catalog, build_source_catalog
from app.infrastructure.repositories.db import get_db


def get_chunk_catalog(
    settings: Settings = Depends(get_settings),
) -> ChunkCatalogRepository:
    return build_chunk_catalog(settings)


def get_source_catalog(
    db: Session = Depends(get_db),
) -> SourceCatalogRepository:
    return build_source_catalog(db)
