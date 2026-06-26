from __future__ import annotations

from abc import ABC, abstractmethod

from app.domains.ingestion.content import ExtractOptions, RawContent


class ContentExtractor(ABC):
    """Acquire raw bytes from a URI. Does not parse content."""

    name: str

    @abstractmethod
    def supports(self, source_uri: str, source_type: str) -> bool: ...

    @abstractmethod
    def extract(
        self,
        source_uri: str,
        source_type: str,
        options: ExtractOptions | None = None,
    ) -> RawContent: ...
