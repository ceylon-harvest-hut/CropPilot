from unittest.mock import MagicMock

import pytest

from app.domains.graph.persistence import (
    SourceAlreadyGraphIngestedError,
    persist_crop_graph,
)
from app.domains.graph.schemas import ExtractedCropKnowledge
from app.domains.ingestion.repositories import ExistingSourceInfo
from app.infrastructure.repositories.db import (
    KNOWLEDGE_SOURCE_STATUS_GRAPH_INDEXED,
    KNOWLEDGE_SOURCE_STATUS_INDEXED,
    KNOWLEDGE_SOURCE_STATUS_PROCESSING,
)


def _extracted() -> ExtractedCropKnowledge:
    return ExtractedCropKnowledge(name="Pepper", scientific_name="Piper nigrum")


def test_persist_crop_graph_creates_new_source() -> None:
    graph_store = MagicMock()
    graph_store.count_by_source_uri.return_value = 0
    source_repo = MagicMock()
    source_repo.find_by_origin_url.return_value = None
    source_repo.create_pending.return_value = 42

    result = persist_crop_graph(
        source_uri="pepper.html",
        extracted=_extracted(),
        graph_store=graph_store,
        source_repository=source_repo,
        replace_existing=False,
        manifest_crop_name="Pepper",
    )

    assert result.source_id == 42
    assert result.crop_name == "Pepper"
    assert result.status == KNOWLEDGE_SOURCE_STATUS_GRAPH_INDEXED
    source_repo.create_pending.assert_called_once_with("pepper.html", "Pepper")
    graph_store.upsert_crop.assert_called_once()
    upsert_kwargs = graph_store.upsert_crop.call_args.kwargs
    assert upsert_kwargs["manifest_crop_name"] == "Pepper"
    source_repo.update_status.assert_any_call(42, KNOWLEDGE_SOURCE_STATUS_PROCESSING)
    source_repo.update_status.assert_any_call(42, KNOWLEDGE_SOURCE_STATUS_GRAPH_INDEXED)


def test_persist_crop_graph_allows_vector_indexed_source() -> None:
    graph_store = MagicMock()
    graph_store.count_by_source_uri.return_value = 0
    source_repo = MagicMock()
    source_repo.find_by_origin_url.return_value = ExistingSourceInfo(
        source_id=7,
        status=KNOWLEDGE_SOURCE_STATUS_INDEXED,
        crop_names=["Pepper"],
    )

    result = persist_crop_graph(
        source_uri="pepper.html",
        extracted=_extracted(),
        graph_store=graph_store,
        source_repository=source_repo,
        replace_existing=False,
    )

    assert result.source_id == 7
    assert result.replaced is False
    source_repo.create_pending.assert_not_called()
    source_repo.ensure_crop_link.assert_called_once_with(7, "Pepper")


def test_persist_crop_graph_raises_when_already_graph_indexed() -> None:
    graph_store = MagicMock()
    graph_store.count_by_source_uri.return_value = 1
    source_repo = MagicMock()
    source_repo.find_by_origin_url.return_value = ExistingSourceInfo(
        source_id=9,
        status=KNOWLEDGE_SOURCE_STATUS_GRAPH_INDEXED,
        crop_names=["Pepper"],
    )

    with pytest.raises(SourceAlreadyGraphIngestedError) as exc_info:
        persist_crop_graph(
            source_uri="pepper.html",
            extracted=_extracted(),
            graph_store=graph_store,
            source_repository=source_repo,
            replace_existing=False,
        )

    assert exc_info.value.source_id == 9
    graph_store.upsert_crop.assert_not_called()


def test_persist_crop_graph_replace_deletes_existing_graph() -> None:
    graph_store = MagicMock()
    graph_store.count_by_source_uri.return_value = 1
    source_repo = MagicMock()
    source_repo.find_by_origin_url.return_value = ExistingSourceInfo(
        source_id=9,
        status=KNOWLEDGE_SOURCE_STATUS_GRAPH_INDEXED,
        crop_names=["Pepper"],
    )

    result = persist_crop_graph(
        source_uri="pepper.html",
        extracted=_extracted(),
        graph_store=graph_store,
        source_repository=source_repo,
        replace_existing=True,
    )

    graph_store.delete_by_source_uri.assert_called_once_with("pepper.html")
    assert result.replaced is True
    graph_store.upsert_crop.assert_called_once()
