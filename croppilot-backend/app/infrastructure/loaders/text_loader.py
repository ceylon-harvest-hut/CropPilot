from pathlib import Path

from app.domains.ingestion.loader import DocumentLoader, KnowledgeDocument
from app.domains.ingestion.source_types import SOURCE_TYPE_FILE
from app.infrastructure.extractors.text_extractor import TextFileExtractor


class TextDocumentLoader(DocumentLoader):
    name = "text"

    def supported_source_types(self) -> frozenset[str]:
        return frozenset({SOURCE_TYPE_FILE})

    def supports(self, source_uri: str, source_type: str) -> bool:
        if source_type != SOURCE_TYPE_FILE:
            return False
        return Path(source_uri).suffix.lower() == ".txt"

    def load(self, source_uri: str, source_type: str) -> list[KnowledgeDocument]:
        text = TextFileExtractor().read(source_uri)
        return [
            KnowledgeDocument(
                text=text,
                metadata={
                    "source_uri": source_uri,
                    "source_type": source_type,
                    "loader": self.name,
                    "media_type": "text/plain",
                },
            )
        ]
