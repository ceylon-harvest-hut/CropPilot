from __future__ import annotations

from app.domains.ingestion.loader import DocumentLoader

class DocumentLoaderRegistry:
    def __init__(self, loaders: list[DocumentLoader]) -> None:
        self._loaders = loaders

    def resolve(self, source_uri: str) -> DocumentLoader:
        for loader in self._loaders:
            if loader.supports(source_uri):
                return loader
        raise ValueError(f"No loader for: {source_uri}")