"""Tests for DeaGovLkLoader using real fixture HTML files."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.domains.ingestion.content import RawContent
from app.domains.ingestion.source_types import SOURCE_TYPE_FILE, SOURCE_TYPE_WEB_URL
from app.infrastructure.loaders.dea_gov_lk_loader import (
    DeaGovLkLoader,
    _extract_crop_name,
    _extract_scientific,
    _table_to_markdown,
)

PEPPER_HTML = (
    Path(__file__).parent.parent.parent
    / "data/web_collection/html/dea-gov-lk-pepper.html"
)

COCOA_HTML = (
    Path(__file__).parent.parent.parent
    / "data/web_collection/html/dea-gov-lk-cocoa.html"
)


@pytest.fixture
def loader() -> DeaGovLkLoader:
    return DeaGovLkLoader()


def _raw_from_file(html_path: Path, source_type: str = SOURCE_TYPE_FILE) -> RawContent:
    return RawContent(
        source_uri=str(html_path),
        resolved_uri=str(html_path),
        source_type=source_type,
        media_type="text/html",
        data=html_path.read_bytes(),
    )


# ---------------------------------------------------------------------------
# supports()
# ---------------------------------------------------------------------------


def test_supports_text_html_media_type(loader: DeaGovLkLoader) -> None:
    raw = RawContent(
        source_uri="https://dea.gov.lk/pepper/",
        resolved_uri="https://dea.gov.lk/pepper/",
        source_type=SOURCE_TYPE_WEB_URL,
        media_type="text/html",
        data=b"",
    )
    assert loader.supports(raw) is True


def test_supports_html_file_extension(loader: DeaGovLkLoader) -> None:
    raw = RawContent(
        source_uri="/data/crop.html",
        resolved_uri="/data/crop.html",
        source_type=SOURCE_TYPE_FILE,
        media_type="application/octet-stream",
        data=b"",
    )
    assert loader.supports(raw) is True


def test_does_not_support_pdf(loader: DeaGovLkLoader) -> None:
    raw = RawContent(
        source_uri="report.pdf",
        resolved_uri="report.pdf",
        source_type=SOURCE_TYPE_FILE,
        media_type="application/pdf",
        data=b"",
    )
    assert loader.supports(raw) is False


def test_does_not_support_plain_text(loader: DeaGovLkLoader) -> None:
    raw = RawContent(
        source_uri="notes.txt",
        resolved_uri="notes.txt",
        source_type=SOURCE_TYPE_FILE,
        media_type="text/plain",
        data=b"",
    )
    assert loader.supports(raw) is False


# ---------------------------------------------------------------------------
# Load pepper.html
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not PEPPER_HTML.exists(), reason="pepper.html fixture not present")
def test_load_pepper_returns_multiple_sections(loader: DeaGovLkLoader) -> None:
    docs = loader.load(_raw_from_file(PEPPER_HTML))
    section_names = [d.metadata["section_name"] for d in docs]
    assert len(docs) >= 6
    assert any("History" in s for s in section_names)
    assert any("Varieties" in s for s in section_names)
    assert any("Soil" in s or "Climatic" in s for s in section_names)
    assert any("Harvest" in s for s in section_names)


@pytest.mark.skipif(not PEPPER_HTML.exists(), reason="pepper.html fixture not present")
def test_load_pepper_crop_metadata(loader: DeaGovLkLoader) -> None:
    docs = loader.load(_raw_from_file(PEPPER_HTML))
    for doc in docs:
        assert doc.metadata["crop_name"] == "Pepper"
        assert "Piper nigrum" in doc.metadata["scientific_name"]
        assert doc.metadata["family"] != ""


@pytest.mark.skipif(not PEPPER_HTML.exists(), reason="pepper.html fixture not present")
def test_load_pepper_tables_are_markdown(loader: DeaGovLkLoader) -> None:
    docs = loader.load(_raw_from_file(PEPPER_HTML))
    all_text = "\n".join(d.text for d in docs)
    # At least one table should be rendered as markdown
    assert "|" in all_text, "Expected at least one Markdown table"
    assert "---" in all_text, "Expected table separator row"


@pytest.mark.skipif(not PEPPER_HTML.exists(), reason="pepper.html fixture not present")
def test_load_pepper_no_nav_noise(loader: DeaGovLkLoader) -> None:
    docs = loader.load(_raw_from_file(PEPPER_HTML))
    all_text = "\n".join(d.text for d in docs)
    assert "Home" not in all_text.splitlines()[:5]
    assert "Contact" not in all_text.splitlines()[:5]


@pytest.mark.skipif(not PEPPER_HTML.exists(), reason="pepper.html fixture not present")
def test_load_pepper_bold_subheadings_preserved(loader: DeaGovLkLoader) -> None:
    docs = loader.load(_raw_from_file(PEPPER_HTML))
    climatic_doc = next(
        (d for d in docs if "Soil" in d.metadata["section_name"] or "Climatic" in d.metadata["section_name"]),
        None,
    )
    assert climatic_doc is not None, "Soils and Climatic needs section not found"
    assert "**" in climatic_doc.text, "Expected bold sub-heading markers in section text"


# ---------------------------------------------------------------------------
# Load cocoa.html (structural cross-check)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not COCOA_HTML.exists(), reason="cocoa.html fixture not present")
def test_load_cocoa_crop_metadata(loader: DeaGovLkLoader) -> None:
    docs = loader.load(_raw_from_file(COCOA_HTML))
    for doc in docs:
        assert doc.metadata["crop_name"] == "Cocoa"
        assert "Theobroma" in doc.metadata["scientific_name"]


# ---------------------------------------------------------------------------
# Table helper
# ---------------------------------------------------------------------------


def test_table_to_markdown_with_header_row() -> None:
    from bs4 import BeautifulSoup

    html = """
    <table>
      <tr><th>Variety</th><th>Yield</th></tr>
      <tr><td>SL-1</td><td>2.5 t/ha</td></tr>
    </table>
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    md = _table_to_markdown(table)
    lines = md.splitlines()
    assert lines[0] == "| Variety | Yield |"
    assert lines[1] == "| --- | --- |"
    assert lines[2] == "| SL-1 | 2.5 t/ha |"


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


def test_load_raises_when_no_entry_content(loader: DeaGovLkLoader) -> None:
    html = "<html><body><p>No entry-content div here</p></body></html>"
    raw = RawContent(
        source_uri="https://example.com/page",
        resolved_uri="https://example.com/page",
        source_type=SOURCE_TYPE_WEB_URL,
        media_type="text/html",
        data=html.encode("utf-8"),
    )
    with pytest.raises(ValueError, match="No entry-content div found"):
        loader.load(raw)


def test_load_raises_when_no_data_and_no_path(loader: DeaGovLkLoader) -> None:
    raw = RawContent(
        source_uri="https://example.com/page",
        resolved_uri="https://example.com/page",
        source_type=SOURCE_TYPE_WEB_URL,
        media_type="text/html",
        data=b"",
    )
    with pytest.raises(ValueError, match="No content available"):
        loader.load(raw)
