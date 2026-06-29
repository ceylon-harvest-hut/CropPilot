from __future__ import annotations

from typing import Protocol

from app.domains.graph.data import ExtractedCropKnowledge


class GraphExtractionService(Protocol):
    def extract(
        self,
        text: str,
        *,
        crop_tag: str,
        source_uri: str,
    ) -> ExtractedCropKnowledge: ...


class GraphWriteRepository(Protocol):
    def upsert_crop(
        self,
        extracted: ExtractedCropKnowledge,
        *,
        source_uri: str,
        crop_tag: str,
    ) -> None: ...

    def delete_by_source_uri(self, source_uri: str) -> int: ...

    def count_by_source_uri(self, source_uri: str) -> int: ...
