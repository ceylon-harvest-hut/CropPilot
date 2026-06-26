from __future__ import annotations

from app.domains.ingestion.content import ExtractOptions, LoaderOptions, RawContent
from app.domains.ingestion.loader import KnowledgeDocument


class DocumentPipeline:
    """Orchestrates extract → load without touching the chunker or embedder.

    Interactive callers (Lab, Ingest API) pass default options so no files are
    written.  The snapshot script passes ``ExtractOptions(persist_raw=True)``
    and ``LoaderOptions(persist=True)`` to cache content on disk.
    """

    def __init__(self, extractors: object, loaders: object) -> None:
        self._extractors = extractors  # ExtractorRegistry
        self._loaders = loaders        # DocumentLoaderRegistry

    def extract(
        self,
        source_uri: str,
        source_type: str,
        options: ExtractOptions | None = None,
    ) -> RawContent:
        return self._extractors.extract(source_uri, source_type, options)

    def load_from_raw(
        self,
        raw: RawContent,
        loader_name: str,
        options: LoaderOptions | None = None,
    ) -> list[KnowledgeDocument]:
        loader = self._loaders.resolve(loader_name, raw)
        return loader.load(raw, options)

    def load_documents(
        self,
        source_uri: str,
        source_type: str,
        loader_name: str,
        *,
        extract_options: ExtractOptions | None = None,
        loader_options: LoaderOptions | None = None,
    ) -> list[KnowledgeDocument]:
        raw = self.extract(source_uri, source_type, extract_options)
        return self.load_from_raw(raw, loader_name, loader_options)
