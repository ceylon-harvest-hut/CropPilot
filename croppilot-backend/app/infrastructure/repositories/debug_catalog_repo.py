from __future__ import annotations

from sqlalchemy.orm import Session

from app.domains.debug.data import CropRecord, SourceRecord
from app.domains.ingestion.models import Crop, CropKnowledgeSource, KnowledgeSource
from app.infrastructure.repositories.db import KNOWLEDGE_SOURCE_STATUS_INDEXED


class SqlDebugCatalogRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_sources(
        self,
        crop_name: str | None = None,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[SourceRecord], int]:
        query = self._session.query(KnowledgeSource)

        if status:
            query = query.filter(KnowledgeSource.status == status)

        if crop_name:
            query = (
                query.join(
                    CropKnowledgeSource,
                    KnowledgeSource.id == CropKnowledgeSource.knowledge_source_id,
                )
                .join(Crop, CropKnowledgeSource.crop_id == Crop.id)
                .filter(Crop.name == crop_name)
            )

        total = query.count()
        sources = (
            query.order_by(KnowledgeSource.id)
            .offset(offset)
            .limit(limit)
            .all()
        )

        records = []
        for source in sources:
            names = [link.crop.name for link in source.crop_links]
            records.append(
                SourceRecord(
                    source_id=source.id,
                    origin_url=source.origin_url,
                    status=source.status,
                    crop_names=names,
                )
            )

        return records, total

    def list_crops(self) -> list[CropRecord]:
        crops = self._session.query(Crop).all()
        return [
            CropRecord(
                crop_id=crop.id,
                name=crop.name,
                botanical_name=crop.botanical_name,
            )
            for crop in crops
        ]

    def list_indexed_crops(self) -> list[CropRecord]:
        """Return crops that have at least one INDEXED knowledge source."""
        crops = (
            self._session.query(Crop)
            .join(CropKnowledgeSource, Crop.id == CropKnowledgeSource.crop_id)
            .join(
                KnowledgeSource,
                CropKnowledgeSource.knowledge_source_id == KnowledgeSource.id,
            )
            .filter(KnowledgeSource.status == KNOWLEDGE_SOURCE_STATUS_INDEXED)
            .distinct()
            .order_by(Crop.name)
            .all()
        )
        return [
            CropRecord(
                crop_id=crop.id,
                name=crop.name,
                botanical_name=crop.botanical_name,
            )
            for crop in crops
        ]
