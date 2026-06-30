from functools import lru_cache

from fastapi import Depends
from sqlalchemy.orm import Session

from app.domains.debug.graph_repositories import GraphReadRepository
from app.domains.debug.repositories import ChunkCatalogRepository, SourceCatalogRepository
from app.infrastructure.config import Settings, get_settings
from app.infrastructure.factories import (
    build_chunk_catalog,
    build_graph_read_store,
    build_source_catalog,
)
from app.infrastructure.repositories.db import get_db


def get_chunk_catalog(
    settings: Settings = Depends(get_settings),
) -> ChunkCatalogRepository:
    return build_chunk_catalog(settings)


def get_source_catalog(
    db: Session = Depends(get_db),
) -> SourceCatalogRepository:
    return build_source_catalog(db)


@lru_cache(maxsize=1)
def _get_cached_graph_read_catalog(
    neo4j_uri: str,
    neo4j_user: str,
    neo4j_password: str,
) -> GraphReadRepository:
    settings = get_settings()
    return build_graph_read_store(settings)


def get_graph_read_catalog(
    settings: Settings = Depends(get_settings),
) -> GraphReadRepository:
    return _get_cached_graph_read_catalog(
        neo4j_uri=settings.neo4j_uri,
        neo4j_user=settings.neo4j_user,
        neo4j_password=settings.neo4j_password,
    )
