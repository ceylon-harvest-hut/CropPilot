from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.shared.document.content import LoaderOptions, RawContent


class KnowledgeDocument:
    """Domain object representing a loaded document part.

    Required metadata keys: source_uri, source_type, loader, media_type.
    Optional: page (Docling page number), final_url, export_format.
    """

    def __init__(self, text: str, metadata: dict[str, Any]) -> None:
        self.text = text
        self.metadata = metadata

    @classmethod
    def from_payload(cls, text: str, metadata: dict[str, Any]) -> KnowledgeDocument:
        """Rehydrate from a lab API JSON payload."""
        return cls(text=text, metadata=metadata)


class DocumentLoader(ABC):
    name: str

    @abstractmethod
    def supports(self, raw: RawContent) -> bool: ...

    def supported_media_types(self) -> frozenset[str] | None:
        """MIME types this loader can parse, or None if media type is not the discriminator."""
        return None

    def supported_extensions(self) -> frozenset[str] | None:
        """File extensions this loader handles, used for validation messages."""
        return None

    @abstractmethod
    def load(
        self,
        raw: RawContent,
        options: LoaderOptions | None = None,
    ) -> list[KnowledgeDocument]: ...
