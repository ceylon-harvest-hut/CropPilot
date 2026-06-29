"""Tests for DeaGovLkChunker."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.shared.document.loader import KnowledgeDocument
from app.infrastructure.chunkers.dea_gov_lk_chunker import (
    LONG_SECTION_THRESHOLD,
    DeaGovLkChunker,
    _split_at_bold_headers,
)
from app.infrastructure.loaders.dea_gov_lk_loader import DeaGovLkLoader
from app.shared.document.content import RawContent
from app.shared.document.source_types import SOURCE_TYPE_FILE

PEPPER_HTML = (
    Path(__file__).parent.parent.parent
    / "data/web_collection/html/dea-gov-lk-pepper.html"
)


@pytest.fixture
def chunker() -> DeaGovLkChunker:
    return DeaGovLkChunker()


def _make_doc(text: str, section_name: str = "Test Section") -> KnowledgeDocument:
    return KnowledgeDocument(
        text=text,
        metadata={
            "section_name": section_name,
            "crop_name": "Pepper",
            "scientific_name": "Piper nigrum L.",
            "family": "Piperaceae",
        },
    )


# ---------------------------------------------------------------------------
# Short section → single chunk
# ---------------------------------------------------------------------------


def test_short_section_becomes_single_chunk(chunker: DeaGovLkChunker) -> None:
    text = "Pepper is native to the Malabar Coast of India."
    doc = _make_doc(text, "History")
    chunks = chunker.chunk([doc], crop_tag="pepper")
    assert len(chunks) == 1
    assert chunks[0].text_content == text
    assert chunks[0].metadata["section_name"] == "History"
    assert chunks[0].metadata["crop_name"] == "Pepper"


def test_chunk_metadata_populated(chunker: DeaGovLkChunker) -> None:
    doc = _make_doc("Some text.", "Overview")
    chunks = chunker.chunk([doc], crop_tag="pepper")
    meta = chunks[0].metadata
    assert meta["crop_tag"] == "pepper"
    assert meta["scientific_name"] == "Piper nigrum L."
    assert meta["family"] == "Piperaceae"
    assert meta["page_number"] == 0


# ---------------------------------------------------------------------------
# Long section → split at bold headers
# ---------------------------------------------------------------------------


def test_long_section_split_at_bold_headers(chunker: DeaGovLkChunker) -> None:
    soil_text = "Soil detail " * 50  # > threshold
    climate_text = "Climate detail " * 50
    text = (
        "**Soil:**\n"
        + soil_text
        + "\n\n"
        + "**Climate:**\n"
        + climate_text
    )
    assert len(text) > LONG_SECTION_THRESHOLD
    doc = _make_doc(text, "Soils and Climatic needs")
    chunks = chunker.chunk([doc], crop_tag="pepper")
    assert len(chunks) == 2
    section_names = [c.metadata["section_name"] for c in chunks]
    assert "Soil:" in section_names
    assert "Climate:" in section_names


def test_long_section_without_bold_headers_stays_single_chunk(chunker: DeaGovLkChunker) -> None:
    text = "Long paragraph without any bold markers. " * 40
    assert len(text) > LONG_SECTION_THRESHOLD
    doc = _make_doc(text, "History")
    chunks = chunker.chunk([doc], crop_tag="pepper")
    assert len(chunks) == 1


# ---------------------------------------------------------------------------
# Table atomicity
# ---------------------------------------------------------------------------


def test_table_not_split(chunker: DeaGovLkChunker) -> None:
    """A Markdown table block should never be broken across chunks."""
    table = (
        "| Variety | Yield |\n"
        "| --- | --- |\n"
        "| SL-1 | 2.5 |\n"
        "| SL-2 | 3.0 |\n"
    )
    # Bold header before table, then a long paragraph
    long_para = "More context after the table. " * 50
    text = "**Varieties:**\n" + table + "\n\n" + long_para
    assert len(text) > LONG_SECTION_THRESHOLD
    doc = _make_doc(text, "Varieties")
    chunks = chunker.chunk([doc], crop_tag="pepper")
    # The chunk containing the table must hold it entirely
    table_chunk = next((c for c in chunks if "|" in c.text_content), None)
    assert table_chunk is not None
    assert "Variety" in table_chunk.text_content
    assert "SL-2" in table_chunk.text_content


# ---------------------------------------------------------------------------
# _split_at_bold_headers helper
# ---------------------------------------------------------------------------


def test_split_at_bold_headers_single_sub_section() -> None:
    text = "Intro line\n\n**Sub:**\nDetail about sub."
    parts = _split_at_bold_headers(text, "Parent")
    assert len(parts) == 2
    names = [p[0] for p in parts]
    assert "Parent" in names
    assert "Sub:" in names


def test_split_at_bold_headers_no_headers_returns_original() -> None:
    text = "Just plain text, no headers at all."
    parts = _split_at_bold_headers(text, "Section")
    assert len(parts) == 1
    assert parts[0][0] == "Section"
    assert parts[0][1] == text


def test_split_at_bold_headers_table_kept_intact() -> None:
    text = (
        "**First:**\n"
        "Some text.\n\n"
        "| A | B |\n"
        "| --- | --- |\n"
        "| 1 | 2 |\n"
        "\n"
        "**Second:**\n"
        "After table."
    )
    parts = _split_at_bold_headers(text, "Root")
    # Table lines should remain with First: (or Root if First was empty)
    table_part = next((p for p in parts if "|" in p[1]), None)
    assert table_part is not None, "Table must be present in one of the parts"
    # Ensure both rows are in the same chunk
    assert "| 1 | 2 |" in table_part[1]


# ---------------------------------------------------------------------------
# Integration: loader + chunker on pepper.html
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not PEPPER_HTML.exists(), reason="pepper.html fixture not present")
def test_loader_chunker_integration_pepper() -> None:
    loader = DeaGovLkLoader()
    chunker = DeaGovLkChunker()

    raw = RawContent(
        source_uri=str(PEPPER_HTML),
        resolved_uri=str(PEPPER_HTML),
        source_type=SOURCE_TYPE_FILE,
        media_type="text/html",
        data=PEPPER_HTML.read_bytes(),
    )
    docs = loader.load(raw)
    chunks = chunker.chunk(docs, crop_tag="pepper")

    assert len(chunks) >= 8, "Expected at least 8 chunks from pepper page"
    for chunk in chunks:
        assert chunk.text_content.strip(), "No empty chunks expected"
        assert chunk.metadata["crop_name"] == "Pepper"
        assert chunk.metadata["crop_tag"] == "pepper"
        assert "section_name" in chunk.metadata
