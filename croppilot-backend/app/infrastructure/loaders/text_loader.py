from pathlib import Path

from app.domains.ingestion.loader import DocumentLoader, KnowledgeDocument
from app.infrastructure.extractors.text_extractor import TextFileExtractor


class TextDocumentLoader(DocumentLoader):
    def supports(self, source_uri: str) -> bool:
        return Path(source_uri).suffix.lower() == ".txt"

    def load(self, source_uri: str) -> list[KnowledgeDocument]:
        text = TextFileExtractor().read(source_uri)
        return [
            KnowledgeDocument(
                text=text,
                metadata={"source_uri": source_uri, "media_type": "text/plain"},
            )
        ]
