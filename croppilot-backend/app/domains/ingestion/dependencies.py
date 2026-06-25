from fastapi import Depends
from sqlalchemy.orm import Session

from app.domains.ingestion.service import IngestionService
from app.infrastructure.config import Settings, get_settings
from app.infrastructure.factories import build_ingestion_service
from app.infrastructure.repositories.db import get_db


def get_ingestion_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> IngestionService:
    return build_ingestion_service(settings, db)
