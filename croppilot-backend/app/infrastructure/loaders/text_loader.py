from __future__ import annotations

from pathlib import Path

from app.shared.document.content import LoaderOptions, RawContent
from app.shared.document.loader import DocumentLoader, KnowledgeDocument
from app.infrastructure.loaders.persist import maybe_persist_output

_SUPPORTED_MEDIA_TYPES = frozenset({"text/plain", "text/markdown"})
_SUPPORTED_EXTENSIONS = frozenset({".txt", ".md", ".markdown"})


class TextLoader(DocumentLoader):
    name = "text"

    def supported_media_types(self) -> frozenset[str]:
        return _SUPPORTED_MEDIA_TYPES

    def supported_extensions(self) -> frozenset[str]:
        return _SUPPORTED_EXTENSIONS

    def supports(self, raw: RawContent) -> bool:
        ext = Path(raw.source_uri).suffix.lower() if raw.source_uri else ""
        return raw.media_type in _SUPPORTED_MEDIA_TYPES or ext in _SUPPORTED_EXTENSIONS

    def load(
        self,
        raw: RawContent,
        options: LoaderOptions | None = None,
    ) -> list[KnowledgeDocument]:
        if raw.local_path is not None:
            text = raw.local_path.read_text(encoding="utf-8")
        elif raw.data:
            text = raw.data.decode(raw.charset, errors="replace")
        else:
            raise ValueError(f"No content available for: {raw.source_uri}")

        if not text.strip():
            raise ValueError(f"Empty content: {raw.source_uri}")

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


# Backward-compatible alias used by existing imports (e.g. test factories).
TextDocumentLoader = TextLoader
