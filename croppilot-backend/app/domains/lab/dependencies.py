from fastapi import Depends
from sqlalchemy.orm import Session

from app.infrastructure.config import Settings, get_settings
from app.infrastructure.repositories.db import get_db


def get_db_session(db: Session = Depends(get_db)) -> Session:
    return db


def get_lab_settings(settings: Settings = Depends(get_settings)) -> Settings:
    return settings
