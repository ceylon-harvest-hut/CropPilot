from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.shared.document.content import ExtractOptions, LoaderOptions, RawContent
from app.shared.document.pipeline import DocumentPipeline
from app.shared.document.source_types import SOURCE_TYPE_FILE, SOURCE_TYPE_WEB_URL
from app.infrastructure.extractors.registry import ExtractorRegistry, build_all_extractors
from app.infrastructure.loaders.registry import DocumentLoaderRegistry, build_all_loaders
from app.infrastructure.loaders.validation import LoaderValidationError

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures"


@pytest.fixture
def pipeline() -> DocumentPipeline:
    return DocumentPipeline(
        extractors=ExtractorRegistry(build_all_extractors()),
        loaders=DocumentLoaderRegistry(build_all_loaders()),
    )


def test_pipeline_loads_txt_file(pipeline: DocumentPipeline) -> None:
    source_uri = str(FIXTURES_DIR / "pepper.txt")
    docs = pipeline.load_documents(source_uri, SOURCE_TYPE_FILE, "text")

    assert len(docs) == 1
    assert docs[0].metadata["loader"] == "text"
    assert docs[0].metadata["media_type"] == "text/plain"
    assert docs[0].text.startswith("Pepper")


def test_pipeline_extract_returns_raw_content(pipeline: DocumentPipeline) -> None:
    source_uri = str(FIXTURES_DIR / "pepper.txt")
    raw = pipeline.extract(source_uri, SOURCE_TYPE_FILE)

    assert raw.media_type == "text/plain"
    assert raw.source_type == SOURCE_TYPE_FILE
    assert len(raw.data) > 0


def test_pipeline_load_from_raw(pipeline: DocumentPipeline) -> None:
    source_uri = str(FIXTURES_DIR / "pepper.txt")
    raw = pipeline.extract(source_uri, SOURCE_TYPE_FILE)
    docs = pipeline.load_from_raw(raw, "text")

    assert len(docs) == 1
    assert "Pepper" in docs[0].text


def test_pipeline_unknown_loader_raises(pipeline: DocumentPipeline) -> None:
    source_uri = str(FIXTURES_DIR / "pepper.txt")
    with pytest.raises(ValueError, match="Unknown loader"):
        pipeline.load_documents(source_uri, SOURCE_TYPE_FILE, "pdf")


def test_pipeline_loader_media_type_mismatch_raises(pipeline: DocumentPipeline) -> None:
    """html_plain loader does not support text/plain from a .txt file."""
    source_uri = str(FIXTURES_DIR / "pepper.txt")
    with pytest.raises(LoaderValidationError) as exc_info:
        pipeline.load_documents(source_uri, SOURCE_TYPE_FILE, "html_plain")
    assert exc_info.value.context["loader"] == "html_plain"
    assert "text/plain" in exc_info.value.context["media_type"]


def test_pipeline_text_loader_persist(pipeline: DocumentPipeline, tmp_path: Path) -> None:
    source_uri = str(FIXTURES_DIR / "pepper.txt")
    out_path = tmp_path / "output.txt"
    docs = pipeline.load_documents(
        source_uri,
        SOURCE_TYPE_FILE,
        "text",
        loader_options=LoaderOptions(persist=True, output_path=out_path),
    )

    assert out_path.is_file()
    assert out_path.read_text(encoding="utf-8") == docs[0].text
