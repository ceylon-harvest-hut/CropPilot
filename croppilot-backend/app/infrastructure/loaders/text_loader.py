from pathlib import Path

from app.domains.ingestion.loader import LoadedDocument
from app.infrastructure.extractors.text_extractor import TextFileExtractor


class TextDocumentLoader:
    def supports(self, source_uri: str) -> bool:
        return Path(source_uri).suffix.lower() == ".txt"

    def load(self, source_uri: str) -> LoadedDocument:
        text = TextFileExtractor().read(source_uri)
        return LoadedDocument(
            text=text,
            source_uri=source_uri,
            media_type="text/plain",
        )