from __future__ import annotations

from typing import Protocol

from app.domains.graph.schemas import ExtractedCropKnowledge


class GraphExtractionService(Protocol):
    def extract(
        self,
        text: str,
        *,
        manifest_crop_name: str | None,
        source_uri: str,
    ) -> ExtractedCropKnowledge: ...


class GraphWriteRepository(Protocol):
    def upsert_crop(
        self,
        extracted: ExtractedCropKnowledge,
        *,
        source_uri: str,
        manifest_crop_name: str | None = None,
    ) -> None: ...

    def delete_by_source_uri(self, source_uri: str) -> int: ...

    def count_by_source_uri(self, source_uri: str) -> int: ...

    def clear_graph(self) -> int: ...
