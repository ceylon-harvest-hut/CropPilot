import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./croppilot.db")

# Column length constraints
CROP_NAME_MAX_LENGTH = 50
CROP_BOTANICAL_NAME_MAX_LENGTH = 100
KNOWLEDGE_SOURCE_ORIGIN_URL_MAX_LENGTH = 255
KNOWLEDGE_SOURCE_STATUS_MAX_LENGTH = 20

# Knowledge source status values
KNOWLEDGE_SOURCE_STATUS_PENDING = "PENDING"
KNOWLEDGE_SOURCE_STATUS_PROCESSING = "PROCESSING"
KNOWLEDGE_SOURCE_STATUS_INDEXED = "INDEXED"
KNOWLEDGE_SOURCE_STATUS_GRAPH_INDEXED = "GRAPH_INDEXED"
KNOWLEDGE_SOURCE_STATUS_FAILED = "FAILED"

Base = declarative_base()

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app.domains.ingestion import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
