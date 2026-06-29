from __future__ import annotations

from app.shared.document.content import ExtractOptions, RawContent
from app.shared.document.extractor import ContentExtractor
from app.infrastructure.extractors.file_extractor import FileExtractor
from app.infrastructure.extractors.http_extractor import HttpExtractor


def build_all_extractors() -> list[ContentExtractor]:
    return [HttpExtractor(), FileExtractor()]


class ExtractorRegistry:
    def __init__(self, extractors: list[ContentExtractor]) -> None:
        self._extractors = extractors

    def resolve(self, source_uri: str, source_type: str) -> ContentExtractor:
        for extractor in self._extractors:
            if extractor.supports(source_uri, source_type):
                return extractor
        raise ValueError(
            f"No extractor found for source_type={source_type!r}, uri={source_uri!r}"
        )

    def extract(
        self,
        source_uri: str,
        source_type: str,
        options: ExtractOptions | None = None,
    ) -> RawContent:
        extractor = self.resolve(source_uri, source_type)
        return extractor.extract(source_uri, source_type, options)
