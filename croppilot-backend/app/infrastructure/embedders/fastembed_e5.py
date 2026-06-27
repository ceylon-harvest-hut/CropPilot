"""Asymmetric FastEmbed embedder for E5 multilingual models.

E5 models are trained with distinct passage and query prefixes:
  - Documents (ingest): ``passage_embed()``
  - Questions  (retrieval): ``query_embed()``

Using the correct path for each role produces meaningfully better retrieval
scores compared to calling plain ``.embed()`` for both.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastembed import TextEmbedding

from app.domains.ingestion.data import ChunkEmbedding, KnowledgeChunk
from app.infrastructure.embedders.base import BaseEmbedder
from app.infrastructure.embedders.cache import ModelCacheError, validate_model_cache
from app.infrastructure.embedders.catalog import get_embedder_option

_OPTION_NAME = "e5_multilingual"


class FastEmbedE5Embedder(BaseEmbedder):
    """Asymmetric FastEmbed embedder for E5 multilingual-large.

    Uses ``passage_embed`` for chunk ingest and ``query_embed`` for retrieval
    to match the training regime of E5 models.

    Args:
        cache_dir: Permanent directory where the ONNX model lives.
            Must have been populated by ``bootstrap_models.py`` before the
            app starts.  Never defaults to ``/tmp``.
        offline: When ``True`` (production default) the embedder will NOT
            fetch from Hugging Face at runtime.  If the cache is absent the
            constructor raises ``ModelCacheError`` immediately.
        allow_download: Override flag used exclusively by
            ``bootstrap_models.py`` to permit the initial download.
    """

    def __init__(
        self,
        cache_dir: Path | str | None = None,
        *,
        offline: bool = True,
        allow_download: bool = False,
    ) -> None:
        option = get_embedder_option(_OPTION_NAME)

        resolved = Path(cache_dir).resolve() if cache_dir else None

        if not allow_download:
            if resolved is None:
                raise ModelCacheError(
                    "FastEmbedE5Embedder requires an explicit cache_dir.\n"
                    "Set FASTEMBED_CACHE_DIR in .env or run "
                    "scripts/bootstrap_models.py --download first."
                )
            validate_model_cache(resolved, option)

        if offline:
            os.environ["HF_HUB_OFFLINE"] = "1"

        self._model = TextEmbedding(
            model_name=option.model_name,
            cache_dir=str(resolved) if resolved else None,
            local_files_only=offline and not allow_download,
        )

    def embed(self, chunks: list[KnowledgeChunk]) -> list[KnowledgeChunk]:
        if not chunks:
            return chunks

        texts = [chunk.text_content for chunk in chunks]
        vectors = self._model.passage_embed(texts)
        for chunk, vector in zip(chunks, vectors):
            chunk.update_embedding(ChunkEmbedding(vector=vector.tolist()))

        return chunks

    def embed_text(self, text: str) -> list[float]:
        return next(iter(self._model.query_embed([text]))).tolist()
