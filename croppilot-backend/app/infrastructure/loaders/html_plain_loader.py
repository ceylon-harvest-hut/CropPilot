from __future__ import annotations

from pathlib import Path

from app.domains.ingestion.content import LoaderOptions, RawContent
from app.domains.ingestion.loader import DocumentLoader, KnowledgeDocument
from app.infrastructure.loaders.html_text import html_to_text
from app.infrastructure.loaders.persist import maybe_persist_output

_HTML_MEDIA_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_HTML_EXTENSIONS = frozenset({".html", ".htm"})


class HtmlPlainLoader(DocumentLoader):
    """Convert HTML to plain text, stripping all markup."""

    name = "html_plain"

    def supported_media_types(self) -> frozenset[str]:
        return _HTML_MEDIA_TYPES

    def supported_extensions(self) -> frozenset[str]:
        return _HTML_EXTENSIONS

    def supports(self, raw: RawContent) -> bool:
        ext = Path(raw.source_uri).suffix.lower() if raw.source_uri else ""
        return raw.media_type in _HTML_MEDIA_TYPES or ext in _HTML_EXTENSIONS

    def load(
        self,
        raw: RawContent,
        options: LoaderOptions | None = None,
    ) -> list[KnowledgeDocument]:
        if raw.data:
            html_str = raw.data.decode(raw.charset, errors="replace")
        elif raw.local_path is not None:
            html_str = raw.local_path.read_text(encoding="utf-8")
        else:
            raise ValueError(f"No content available for: {raw.source_uri}")

        text = html_to_text(html_str)
        if not text.strip():
            raise ValueError(f"No text content extracted from HTML: {raw.source_uri}")

        docs = [
            KnowledgeDocument(
                text=text,
                metadata={
                    "source_uri": raw.source_uri,
                    "source_type": raw.source_type,
                    "loader": self.name,
                    "media_type": raw.media_type,
                    "final_url": raw.resolved_uri,
                },
            )
        ]

        if options:
            maybe_persist_output(docs, options)

        return docs
