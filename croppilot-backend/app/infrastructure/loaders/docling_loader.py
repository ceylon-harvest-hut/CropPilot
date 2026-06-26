from __future__ import annotations

import tempfile
from pathlib import Path

from app.domains.ingestion.content import LoaderOptions, RawContent
from app.domains.ingestion.loader import DocumentLoader, KnowledgeDocument
from app.infrastructure.loaders.docling_convert import docling_load_markdown
from app.infrastructure.loaders.persist import maybe_persist_output

_DOCLING_MEDIA_TYPES = frozenset({
    "text/html",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "text/plain",
    "text/markdown",
})

_DOCLING_EXTENSIONS = frozenset({
    ".pdf", ".html", ".htm", ".docx", ".pptx", ".txt", ".md", ".markdown",
})


class DoclingLoader(DocumentLoader):
    """Parse any Docling-supported format (PDF, HTML, DOCX, …) into Markdown documents."""

    name = "docling"

    def supported_media_types(self) -> frozenset[str]:
        return _DOCLING_MEDIA_TYPES

    def supported_extensions(self) -> frozenset[str]:
        return _DOCLING_EXTENSIONS

    def supports(self, raw: RawContent) -> bool:
        ext = Path(raw.source_uri).suffix.lower() if raw.source_uri else ""
        return raw.media_type in _DOCLING_MEDIA_TYPES or ext in _DOCLING_EXTENSIONS

    def load(
        self,
        raw: RawContent,
        options: LoaderOptions | None = None,
    ) -> list[KnowledgeDocument]:
        path, is_temp = self._resolve_path(raw, options)
        try:
            raw_docs = docling_load_markdown(str(path))
        finally:
            if is_temp:
                path.unlink(missing_ok=True)

        docs = [
            KnowledgeDocument(
                text=doc.page_content.strip(),
                metadata={
                    "source_uri": raw.source_uri,
                    "source_type": raw.source_type,
                    "loader": self.name,
                    "media_type": raw.media_type,
                    "final_url": raw.resolved_uri,
                    "export_format": "markdown",
                    **doc.metadata,
                },
            )
            for doc in raw_docs
            if doc.page_content.strip()
        ]

        if options:
            maybe_persist_output(docs, options)

        return docs

    def _resolve_path(
        self, raw: RawContent, options: LoaderOptions | None
    ) -> tuple[Path, bool]:
        """Return (path_to_use, is_temp).  is_temp=True means caller must unlink."""
        if raw.local_path is not None:
            return raw.local_path, False
        if raw.persisted_path is not None:
            return raw.persisted_path, False
        # Must write a temp file so Docling has a real path.
        opts = options or LoaderOptions()
        if not opts.allow_temp_files:
            raise ValueError(
                f"Docling requires a file path but allow_temp_files=False: {raw.source_uri}"
            )
        if not raw.data:
            raise ValueError(f"No content available for Docling: {raw.source_uri}")
        ext = Path(raw.source_uri).suffix if raw.source_uri else ".html"
        with tempfile.NamedTemporaryFile(mode="wb", suffix=ext or ".html", delete=False) as tmp:
            tmp.write(raw.data)
            return Path(tmp.name), True


# Backward-compatible alias.
DoclingDocumentLoader = DoclingLoader
