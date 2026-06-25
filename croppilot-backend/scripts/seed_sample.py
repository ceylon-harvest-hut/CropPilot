#!/usr/bin/env python3
"""Populate Chroma + SQLite with tests/fixtures/pepper.txt."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.infrastructure.config import get_settings
from app.infrastructure.factories import build_ingestion_service
from app.infrastructure.repositories.db import Base, init_db

SAMPLE_FILE = REPO_ROOT / "tests" / "fixtures" / "pepper.txt"
CROP_NAME = "Pepper"


def main() -> None:
    if not SAMPLE_FILE.is_file():
        raise FileNotFoundError(f"Sample file not found: {SAMPLE_FILE}")

    settings = get_settings()
    init_db()

    engine = create_engine(settings.database_url)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()

    try:
        service = build_ingestion_service(settings, session)
        result = service.ingest(str(SAMPLE_FILE), crop_tag=CROP_NAME)
        print("Ingest complete:")
        print(f"  source_id:   {result.source_id}")
        print(f"  chunk_count: {result.chunk_count}")
        print(f"  status:      {result.status}")
        print(f"  chroma_dir:  {settings.chroma_persist_dir}")
        print(f"  database:    {settings.database_url}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
