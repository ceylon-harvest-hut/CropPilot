from pathlib import Path

import pytest

from app.domains.ingestion.chunker import BaseChunker, SectionChunkingStrategy
from app.infrastructure.extractors.text_extractor import TextFileExtractor

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures"


@pytest.fixture
def chunker() -> BaseChunker:
    return BaseChunker(SectionChunkingStrategy())


@pytest.fixture
def extractor() -> TextFileExtractor:
    return TextFileExtractor()


def test_base_chunker_strips_whitespace(chunker: BaseChunker) -> None:
    text = "   History\n\nSome content.\n   "
    chunks = chunker.chunk(text, crop_tag="Pepper")
    assert len(chunks) == 1
    assert chunks[0].metadata.section_name == "History"


def test_chunk_splits_inline_sections(chunker: BaseChunker) -> None:
    text = (
        "History\n"
        "\n"
        "Pepper is the most widely used spice in the world.\n"
        "\n"
        "Products and Uses\n"
        "\n"
        "Pepper is largely produced as black pepper.\n"
    )

    chunks = chunker.chunk(text, crop_tag="Pepper")

    assert len(chunks) == 2
    assert chunks[0].metadata.section_name == "History"
    assert chunks[0].metadata.crop_tag == "Pepper"
    assert "most widely used spice" in chunks[0].text_content
    assert chunks[1].metadata.section_name == "Products and Uses"
    assert "black pepper" in chunks[1].text_content


def test_chunk_creates_introduction_for_document_header(chunker: BaseChunker) -> None:
    text = (
        "Pepper\n"
        "Piper nigrum L.\n"
        "Family : Piperaceae\n"
        "History\n"
        "\n"
        "Pepper is the most widely used spice in the world.\n"
    )

    chunks = chunker.chunk(text, crop_tag="Pepper")

    assert chunks[0].metadata.section_name == "Introduction"
    assert "Piper nigrum L." in chunks[0].text_content
    assert chunks[1].metadata.section_name == "History"


def test_chunk_pepper_fixture(chunker: BaseChunker, extractor: TextFileExtractor) -> None:
    text = extractor.read(str(FIXTURES_DIR / "pepper.txt"))

    chunks = chunker.chunk(text, crop_tag="Pepper")

    section_names = [chunk.metadata.section_name for chunk in chunks]

    assert len(chunks) >= 10
    assert "History" in section_names
    assert "Dingi Rala" in section_names
    assert "Crop establishment" in section_names

    dingi_rala = next(chunk for chunk in chunks if chunk.metadata.section_name == "Dingi Rala")
    assert "Yield: 2,245 g/year/vine" in dingi_rala.text_content

    crop_establishment = next(
        chunk for chunk in chunks if chunk.metadata.section_name == "Crop establishment"
    )
    assert "2.4m x 2.4m" in crop_establishment.text_content
