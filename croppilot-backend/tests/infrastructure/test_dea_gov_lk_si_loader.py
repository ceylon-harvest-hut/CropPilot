"""Tests for DeaGovLkSiLoader (Sinhala DEA gov.lk crop pages)."""

from __future__ import annotations

from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from app.domains.ingestion.content import RawContent
from app.domains.ingestion.source_types import SOURCE_TYPE_FILE
from app.infrastructure.chunkers.dea_gov_lk_si_chunker import DeaGovLkSiChunker
from app.infrastructure.loaders.dea_gov_lk_si_loader import (
    DeaGovLkSiLoader,
    _extract_crop_name,
    _extract_scientific,
    _is_section_header,
)

PEPPER_SI_HTML = Path("/home/jayaprabath/harvest_hut/crop_documents/ගම්මිරිස්.html")

MINIMAL_SI_HTML = """<!DOCTYPE html>
<html lang="si-LK"><body>
<article><div class="entry-content clearfix">
<h2 class="has-text-align-center wp-block-heading">ගම්මිරිස්</h2>
<h4 class="has-text-align-center wp-block-heading"><em>Piper nigrum L.</em>කුලය: Piperaceae</h4>
<h3 class="wp-block-heading">ඉතිහාසය</h3>
<p>කුළුබඩු වල රජ ලෙස හැඳින්වෙන ගම්මිරිස්.</p>
<h3 class="wp-block-heading">පාංශු සහ දේශගුණික අවශ්‍යතා</h3>
<h4 class="wp-block-heading">පස</h4>
<p>ලෝම පසෙහි ගම්මිරිස් වඩාත් හොඳින් වැඩේ.</p>
</div></article>
</body></html>
"""


@pytest.fixture
def loader() -> DeaGovLkSiLoader:
    return DeaGovLkSiLoader()


def _raw_from_html(html: str, uri: str = "/test/si.html") -> RawContent:
    return RawContent(
        source_uri=uri,
        resolved_uri=uri,
        source_type=SOURCE_TYPE_FILE,
        media_type="text/html",
        data=html.encode("utf-8"),
    )


def test_extract_crop_name_from_h2() -> None:
    entry = BeautifulSoup(MINIMAL_SI_HTML, "html.parser").select_one("div.entry-content")
    assert _extract_crop_name(entry) == "ගම්මිරිස්"


def test_extract_scientific_and_family_sinhala_label() -> None:
    entry = BeautifulSoup(MINIMAL_SI_HTML, "html.parser").select_one("div.entry-content")
    scientific, family = _extract_scientific(entry)
    assert "Piper nigrum" in scientific
    assert family == "Piperaceae"


def test_section_header_is_h3_not_h4() -> None:
    soup = BeautifulSoup(MINIMAL_SI_HTML, "html.parser")
    h3 = soup.find("h3", class_="wp-block-heading")
    h4 = soup.find("h4", class_="wp-block-heading", string=lambda t: t and "පස" in t)
    assert _is_section_header(h3) is True
    assert _is_section_header(h4) is False


def test_load_minimal_splits_at_h3_sections(loader: DeaGovLkSiLoader) -> None:
    docs = loader.load(_raw_from_html(MINIMAL_SI_HTML))
    section_names = [d.metadata["section_name"] for d in docs]
    assert "ඉතිහාසය" in section_names
    assert "පාංශු සහ දේශගුණික අවශ්‍යතා" in section_names
    assert docs[0].metadata["crop_name"] == "ගම්මිරිස්"


def test_h4_subsection_rendered_as_bold_in_section_body(loader: DeaGovLkSiLoader) -> None:
    docs = loader.load(_raw_from_html(MINIMAL_SI_HTML))
    soil_section = next(d for d in docs if "පාංශු" in d.metadata["section_name"])
    assert "**පස**" in soil_section.text
    assert "ලෝම පසෙහි" in soil_section.text


def test_si_chunker_delegates_to_dea_chunker_logic() -> None:
    chunker = DeaGovLkSiChunker()
    assert chunker.name == "dea_gov_lk_si"
    docs = DeaGovLkSiLoader().load(_raw_from_html(MINIMAL_SI_HTML))
    chunks = chunker.chunk(docs, crop_tag="ගම්මිරිස්")
    assert len(chunks) >= 2
    assert all(c.metadata["crop_tag"] == "ගම්මිරිස්" for c in chunks)


@pytest.mark.skipif(not PEPPER_SI_HTML.exists(), reason="Sinhala pepper HTML not present")
def test_load_pepper_si_full_page(loader: DeaGovLkSiLoader) -> None:
    raw = RawContent(
        source_uri=str(PEPPER_SI_HTML),
        resolved_uri=str(PEPPER_SI_HTML),
        source_type=SOURCE_TYPE_FILE,
        media_type="text/html",
        data=PEPPER_SI_HTML.read_bytes(),
    )
    docs = loader.load(raw)
    section_names = [d.metadata["section_name"] for d in docs]
    assert len(docs) >= 6
    assert docs[0].metadata["crop_name"] == "ගම්මිරිස්"
    assert "Piper nigrum" in docs[0].metadata["scientific_name"]
    assert docs[0].metadata["family"] == "Piperaceae"
    assert any("ඉතිහාසය" in s for s in section_names)
    assert any("ප්‍රභේද" in s for s in section_names)
