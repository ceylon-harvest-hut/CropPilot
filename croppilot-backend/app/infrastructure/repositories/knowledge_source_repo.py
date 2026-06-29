from __future__ import annotations

from sqlalchemy.orm import Session, joinedload

from app.domains.ingestion.models import Crop, CropKnowledgeSource, KnowledgeSource
from app.domains.ingestion.repositories import ExistingSourceInfo
from app.infrastructure.repositories.db import (
    KNOWLEDGE_SOURCE_STATUS_GRAPH_INDEXED,
    KNOWLEDGE_SOURCE_STATUS_PENDING,
)


class SqlKnowledgeSourceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_by_origin_url(self, origin_url: str) -> ExistingSourceInfo | None:
        source = (
            self._session.query(KnowledgeSource)
            .options(joinedload(KnowledgeSource.crop_links).joinedload(CropKnowledgeSource.crop))
            .filter_by(origin_url=origin_url)
            .one_or_none()
        )
        if source is None:
            return None

        crop_names = [link.crop.name for link in source.crop_links]
        return ExistingSourceInfo(
            source_id=source.id,
            status=source.status,
            crop_names=crop_names,
        )

    def create_pending(self, origin_url: str, crop_name: str) -> int:
        crop = self._get_or_create_crop(crop_name)

        source = KnowledgeSource(
            origin_url=origin_url,
            status=KNOWLEDGE_SOURCE_STATUS_PENDING,
        )
        self._session.add(source)
        self._session.flush()

        self._session.add(
            CropKnowledgeSource(crop_id=crop.id, knowledge_source_id=source.id)
        )
        self._session.commit()
        return source.id

    def prepare_for_reingest(self, origin_url: str, crop_name: str) -> int:
        crop = self._get_or_create_crop(crop_name)

        source = self._session.query(KnowledgeSource).filter_by(origin_url=origin_url).one()
        source.status = KNOWLEDGE_SOURCE_STATUS_PENDING
        self._session.flush()

        link = (
            self._session.query(CropKnowledgeSource)
            .filter_by(crop_id=crop.id, knowledge_source_id=source.id)
            .one_or_none()
        )
        if link is None:
            self._session.add(
                CropKnowledgeSource(crop_id=crop.id, knowledge_source_id=source.id)
            )

        self._session.commit()
        return source.id

    def update_status(self, source_id: int, status: str) -> None:
        source = self._session.get(KnowledgeSource, source_id)
        if source is None:
            raise ValueError(f"KnowledgeSource not found: {source_id}")

        source.status = status
        self._session.commit()

    def reset_graph_indexed_sources(self) -> int:
        sources = (
            self._session.query(KnowledgeSource)
            .filter_by(status=KNOWLEDGE_SOURCE_STATUS_GRAPH_INDEXED)
            .all()
        )
        for source in sources:
            source.status = KNOWLEDGE_SOURCE_STATUS_PENDING
        if sources:
            self._session.commit()
        return len(sources)

    def _get_or_create_crop(self, crop_name: str) -> Crop:
        crop = self._session.query(Crop).filter_by(name=crop_name).one_or_none()
        if crop is None:
            crop = Crop(name=crop_name)
            self._session.add(crop)
            self._session.flush()
        return crop
