from __future__ import annotations

from pathlib import Path

from app.domains.ingestion.loader import DocumentLoader, KnowledgeDocument
from app.domains.ingestion.source_types import SOURCE_TYPE_FILE

_DOCLING_EXTENSIONS = {".pdf", ".html", ".htm", ".docx", ".pptx", ".txt"}


class DoclingDocumentLoader(DocumentLoader):
    name = "docling"

    def supported_source_types(self) -> frozenset[str]:
        return frozenset({SOURCE_TYPE_FILE})

    def supports(self, source_uri: str, source_type: str) -> bool:
        if source_type != SOURCE_TYPE_FILE:
            return False
        return Path(source_uri).suffix.lower() in _DOCLING_EXTENSIONS

    def load(self, source_uri: str, source_type: str) -> list[KnowledgeDocument]:
        from langchain_docling import DoclingLoader  # noqa: PLC0415
        from langchain_docling.loader import ExportType  # noqa: PLC0415

        raw_docs = DoclingLoader(
            file_path=source_uri,
            export_type=ExportType.MARKDOWN,
        ).load()
        return [
            KnowledgeDocument(
                text=doc.page_content.strip(),
                metadata={
                    "source_uri": source_uri,
                    "source_type": source_type,
                    "loader": self.name,
                    **doc.metadata,
                },
            )
            for doc in raw_docs
            if doc.page_content.strip()
        ]
