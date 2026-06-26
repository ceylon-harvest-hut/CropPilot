from __future__ import annotations

from typing import Protocol

from app.domains.debug.data import CropRecord, SourceRecord, StoredChunk


class ChunkCatalogRepository(Protocol):
    def list_chunks(
        self,
        crop_tag: str | None,
        source_uri: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[StoredChunk], int]: ...


class SourceCatalogRepository(Protocol):
    def list_sources(
        self,
        crop_name: str | None,
        status: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[SourceRecord], int]: ...

    def list_crops(self) -> list[CropRecord]: ...
