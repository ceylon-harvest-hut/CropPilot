from __future__ import annotations

from pathlib import Path

from app.domains.ingestion.loader import DocumentLoader, KnowledgeDocument

_DOCLING_EXTENSIONS = {".pdf", ".html", ".htm", ".docx", ".pptx"}


class DoclingDocumentLoader(DocumentLoader):
    def supports(self, source_uri: str) -> bool:
        return Path(source_uri).suffix.lower() in _DOCLING_EXTENSIONS

    def load(self, source_uri: str) -> list[KnowledgeDocument]:
        from langchain_docling import DoclingLoader  # noqa: PLC0415
        from langchain_docling.loader import ExportType  # noqa: PLC0415

        raw_docs = DoclingLoader(
            file_path=source_uri,
            export_type=ExportType.MARKDOWN,
        ).load()
        return [
            KnowledgeDocument(
                text=doc.page_content.strip(),
                metadata={"source_uri": source_uri, **doc.metadata},
            )
            for doc in raw_docs
            if doc.page_content.strip()
        ]
