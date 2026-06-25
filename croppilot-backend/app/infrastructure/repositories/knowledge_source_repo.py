from __future__ import annotations

from sqlalchemy.orm import Session

from app.domains.ingestion.models import Crop, CropKnowledgeSource, KnowledgeSource
from app.infrastructure.repositories.db import KNOWLEDGE_SOURCE_STATUS_PENDING


class SqlKnowledgeSourceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_pending(self, origin_url: str, crop_name: str) -> int:
        crop = self._session.query(Crop).filter_by(name=crop_name).one_or_none()
        if crop is None:
            crop = Crop(name=crop_name)
            self._session.add(crop)
            self._session.flush()

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

    def update_status(self, source_id: int, status: str) -> None:
        source = self._session.get(KnowledgeSource, source_id)
        if source is None:
            raise ValueError(f"KnowledgeSource not found: {source_id}")

        source.status = status
        self._session.commit()
