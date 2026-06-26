from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class KnowledgeDocument:
    """Domain object representing a loaded document part.

    Required metadata keys: source_uri, source_type, loader, media_type.
    Optional: page (Docling page number).
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
    def supported_source_types(self) -> frozenset[str]: ...

    @abstractmethod
    def supports(self, source_uri: str, source_type: str) -> bool: ...

    @abstractmethod
    def load(self, source_uri: str, source_type: str) -> list[KnowledgeDocument]: ...
