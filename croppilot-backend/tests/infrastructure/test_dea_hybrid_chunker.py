"""Tests for DeaHybridChunker."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.shared.document.content import RawContent
from app.shared.document.loader import KnowledgeDocument
from app.shared.document.source_types import SOURCE_TYPE_FILE
from app.infrastructure.chunkers.dea_hybrid_chunker import DeaHybridChunker
from app.infrastructure.chunkers.dea_markdown import partition_prose_and_tables
from app.infrastructure.loaders.dea_gov_lk_loader import DeaGovLkLoader

PEPPER_HTML = (
    Path(__file__).parent.parent.parent
    / "data/web_collection/html/dea-gov-lk-pepper.html"
)


@pytest.fixture
def chunker() -> DeaHybridChunker:
    return DeaHybridChunker(max_chunk_size=800, chunk_overlap=50)


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


def test_short_section_unchanged(chunker: DeaHybridChunker) -> None:
    text = "Pepper is native to the Malabar Coast of India."
    doc = _make_doc(text, "History")
    chunks = chunker.chunk([doc], crop_tag="pepper")
    assert len(chunks) == 1
    assert chunks[0].text_content == text


def test_long_prose_without_bold_headers_is_recursively_split(chunker: DeaHybridChunker) -> None:
    text = "Long paragraph without any bold markers. " * 40
    assert len(text) > 800
    doc = _make_doc(text, "History")
    chunks = chunker.chunk([doc], crop_tag="pepper")
    assert len(chunks) > 1
    assert all(len(c.text_content) <= 800 for c in chunks)
    assert all(c.metadata["section_name"].startswith("History") for c in chunks)
    assert chunks[0].metadata["crop_name"] == "Pepper"


def test_table_block_kept_intact(chunker: DeaHybridChunker) -> None:
    table = (
        "| Variety | Yield |\n"
        "| --- | --- |\n"
        "| SL-1 | 2.5 |\n"
        "| SL-2 | 3.0 |\n"
    )
    long_para = "More context after the table. " * 50
    text = "**Varieties:**\n" + table + "\n\n" + long_para
    doc = _make_doc(text, "Varieties")
    chunks = chunker.chunk([doc], crop_tag="pepper")

    table_chunks = [c for c in chunks if "|" in c.text_content and "Variety" in c.text_content]
    assert len(table_chunks) == 1
    table_text = table_chunks[0].text_content
    assert "| SL-1 | 2.5 |" in table_text
    assert "| SL-2 | 3.0 |" in table_text
    assert len(table_text.splitlines()) == 4


def test_prose_and_table_emitted_as_separate_chunks(chunker: DeaHybridChunker) -> None:
    table = "| A | B |\n| --- | --- |\n| 1 | 2 |\n"
    prose = "Short intro before table."
    text = prose + "\n\n" + table
    doc = _make_doc(text, "Data")
    chunks = chunker.chunk([doc], crop_tag="pepper")
    assert len(chunks) == 2
    assert "|" not in chunks[0].text_content
    assert "|" in chunks[1].text_content


def test_partition_prose_and_tables() -> None:
    text = (
        "Intro line.\n\n"
        "| Col |\n"
        "| --- |\n"
        "| x |\n"
        "\n"
        "After table."
    )
    blocks = partition_prose_and_tables(text)
    assert len(blocks) == 3
    assert blocks[0][0] == "prose"
    assert blocks[1][0] == "table"
    assert "| x |" in blocks[1][1]
    assert blocks[2][0] == "prose"
    assert "After table" in blocks[2][1]


@pytest.mark.skipif(not PEPPER_HTML.exists(), reason="pepper.html fixture not present")
def test_loader_hybrid_integration_pepper() -> None:
    loader = DeaGovLkLoader()
    chunker = DeaHybridChunker(max_chunk_size=800, chunk_overlap=50)

    raw = RawContent(
        source_uri=str(PEPPER_HTML),
        resolved_uri=str(PEPPER_HTML),
        source_type=SOURCE_TYPE_FILE,
        media_type="text/html",
        data=PEPPER_HTML.read_bytes(),
    )
    docs = loader.load(raw)
    chunks = chunker.chunk(docs, crop_tag="pepper")

    assert len(chunks) >= 8
    for chunk in chunks:
        assert chunk.text_content.strip()
        assert chunk.metadata["crop_name"] == "Pepper"
        if "|" not in chunk.text_content:
            assert len(chunk.text_content) <= 800
