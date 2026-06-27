"""Symmetric FastEmbed embedder using BAAI/bge-small-en-v1.5.

Both document and query embeddings use the same .embed() call — appropriate
for models that do not distinguish between passage and query representations.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastembed import TextEmbedding

from app.domains.ingestion.data import ChunkEmbedding, KnowledgeChunk
from app.infrastructure.embedders.base import BaseEmbedder
from app.infrastructure.embedders.cache import ModelCacheError, validate_model_cache
from app.infrastructure.embedders.catalog import get_embedder_option

_OPTION_NAME = "bge_small"


class FastEmbedBGEEmbedder(BaseEmbedder):
    """Symmetric FastEmbed embedder for English text (BGE small).

    Uses the same embedding path for both passages (ingest) and queries (retrieval),
    which is correct for models without query/passage prefix requirements.

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
                    "FastEmbedBGEEmbedder requires an explicit cache_dir.\n"
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

        vectors = self._model.embed(chunk.text_content for chunk in chunks)
        for chunk, vector in zip(chunks, vectors):
            chunk.update_embedding(ChunkEmbedding(vector=vector.tolist()))

        return chunks

    def embed_text(self, text: str) -> list[float]:
        return list(self._model.embed([text]))[0].tolist()
