"""Unit tests for the E5 embedder, asserting asymmetric path usage.

FastEmbed's TextEmbedding and validate_model_cache are mocked so no model
download or real cache directory is required.
We only care that:
  - embed() calls passage_embed()
  - embed_text() calls query_embed()
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.domains.ingestion.data import KnowledgeChunk
from app.infrastructure.embedders.fastembed_e5 import FastEmbedE5Embedder


def _make_chunk(text: str) -> KnowledgeChunk:
    return KnowledgeChunk(
        text_content=text,
        metadata={"section_name": "Test", "page_number": 0, "crop_tag": "Crop"},
    )


@pytest.fixture
def e5_embedder_with_mock():
    """Return an E5 embedder whose inner TextEmbedding is a fully mocked model."""
    with patch("app.infrastructure.embedders.fastembed_e5.validate_model_cache"), \
         patch("app.infrastructure.embedders.fastembed_e5.TextEmbedding") as MockTextEmbedding:
        mock_model = MagicMock()
        MockTextEmbedding.return_value = mock_model

        vector = np.zeros(1024, dtype=np.float32)
        mock_model.passage_embed.return_value = iter([vector, vector])
        mock_model.query_embed.return_value = iter([vector])

        embedder = FastEmbedE5Embedder(cache_dir=Path("/fake/cache"))
        yield embedder, mock_model


def test_embed_uses_passage_embed(e5_embedder_with_mock) -> None:
    embedder, mock_model = e5_embedder_with_mock
    chunks = [_make_chunk("text a"), _make_chunk("text b")]
    embedder.embed(chunks)
    mock_model.passage_embed.assert_called_once()
    mock_model.query_embed.assert_not_called()


def test_embed_text_uses_query_embed(e5_embedder_with_mock) -> None:
    embedder, mock_model = e5_embedder_with_mock
    result = embedder.embed_text("What is the planting density?")
    mock_model.query_embed.assert_called_once()
    mock_model.passage_embed.assert_not_called()
    assert len(result) == 1024


def test_embed_empty_list_returns_empty(e5_embedder_with_mock) -> None:
    embedder, mock_model = e5_embedder_with_mock
    result = embedder.embed([])
    assert result == []
    mock_model.passage_embed.assert_not_called()
