from __future__ import annotations

from app.domains.ingestion.loader import DocumentLoader
from app.infrastructure.loaders.docling_loader import DoclingDocumentLoader
from app.infrastructure.loaders.text_loader import TextDocumentLoader
from app.infrastructure.loaders.validation import validate_loader_selection
from app.infrastructure.loaders.web_url_loader import WebUrlLoader


def build_all_loaders() -> list[DocumentLoader]:
    return [TextDocumentLoader(), DoclingDocumentLoader(), WebUrlLoader()]


class DocumentLoaderRegistry:
    def __init__(self, loaders: list[DocumentLoader]) -> None:
        self._loaders_by_name = {loader.name: loader for loader in loaders}

    def resolve(self, loader_name: str, source_uri: str, source_type: str) -> DocumentLoader:
        loader = self._loaders_by_name.get(loader_name)
        if loader is None:
            known = ", ".join(sorted(self._loaders_by_name))
            raise ValueError(f"Unknown loader: {loader_name!r}. Available: {known}")

        validate_loader_selection(loader, source_uri, source_type)
        return loader
