from pathlib import Path

import pytest

from app.domains.ingestion.loader import KnowledgeDocument
from app.infrastructure.chunkers.section_chunker import SectionChunker
from pathlib import Path as _Path

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures"


@pytest.fixture
def chunker() -> SectionChunker:
    return SectionChunker()



def _doc(text: str) -> KnowledgeDocument:
    return KnowledgeDocument(text=text, metadata={"source_uri": "test", "media_type": "text/plain"})


def test_section_chunker_strips_whitespace(chunker: SectionChunker) -> None:
    chunks = chunker.chunk([_doc("   History\n\nSome content.\n   ")], crop_tag="Pepper")
    assert len(chunks) == 1
    assert chunks[0].metadata["section_name"] == "History"


def test_chunk_splits_inline_sections(chunker: SectionChunker) -> None:
    text = (
        "History\n"
        "\n"
        "Pepper is the most widely used spice in the world.\n"
        "\n"
        "Products and Uses\n"
        "\n"
        "Pepper is largely produced as black pepper.\n"
    )

    chunks = chunker.chunk([_doc(text)], crop_tag="Pepper")

    assert len(chunks) == 2
    assert chunks[0].metadata["section_name"] == "History"
    assert chunks[0].metadata["crop_tag"] == "Pepper"
    assert "most widely used spice" in chunks[0].text_content
    assert chunks[1].metadata["section_name"] == "Products and Uses"
    assert "black pepper" in chunks[1].text_content


def test_chunk_creates_introduction_for_document_header(chunker: SectionChunker) -> None:
    text = (
        "Pepper\n"
        "Piper nigrum L.\n"
        "Family : Piperaceae\n"
        "History\n"
        "\n"
        "Pepper is the most widely used spice in the world.\n"
    )

    chunks = chunker.chunk([_doc(text)], crop_tag="Pepper")

    assert chunks[0].metadata["section_name"] == "Introduction"
    assert "Piper nigrum L." in chunks[0].text_content
    assert chunks[1].metadata["section_name"] == "History"


def test_chunk_pepper_fixture(chunker: SectionChunker) -> None:
    text = (FIXTURES_DIR / "pepper.txt").read_text(encoding="utf-8")
    doc = KnowledgeDocument(
        text=text,
        metadata={"source_uri": str(FIXTURES_DIR / "pepper.txt"), "media_type": "text/plain"},
    )
    chunks = chunker.chunk([doc], crop_tag="Pepper")

    section_names = [chunk.metadata["section_name"] for chunk in chunks]

    assert len(chunks) >= 10
    assert "History" in section_names
    assert "Dingi Rala" in section_names
    assert "Crop establishment" in section_names

    dingi_rala = next(chunk for chunk in chunks if chunk.metadata["section_name"] == "Dingi Rala")
    assert "Yield: 2,245 g/year/vine" in dingi_rala.text_content

    crop_establishment = next(
        chunk for chunk in chunks if chunk.metadata["section_name"] == "Crop establishment"
    )
    assert "2.4m x 2.4m" in crop_establishment.text_content
