from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StoredChunk:
    chunk_id: str
    crop_tag: str
    source_uri: str
    section_name: str
    page_number: int
    text_preview: str


@dataclass(frozen=True)
class SourceRecord:
    source_id: int
    origin_url: str
    status: str
    crop_names: list[str]


@dataclass(frozen=True)
class CropRecord:
    crop_id: int
    name: str
    botanical_name: str | None
