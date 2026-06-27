"""Tests for DoaHordiLoader (DOA gov.lk HORDI Elementor crop pages)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.domains.ingestion.content import RawContent
from app.domains.ingestion.source_types import SOURCE_TYPE_FILE
from app.infrastructure.chunkers.doa_hordi_chunker import DoaHordiChunker
from app.infrastructure.loaders.doa_hordi_loader import DoaHordiLoader

CABBAGE_HTML = Path("/home/jayaprabath/harvest_hut/crop_documents/cabbage.html")

MINIMAL_HTML = """<!DOCTYPE html>
<html><body>
<article><div class="entry-content">
<div data-elementor-type="wp-page" class="elementor elementor-1">
  <div class="elementor-element" data-widget_type="heading.default">
    <div class="elementor-widget-container">
      <h2 class="elementor-heading-title">ගෝවා</h2>
    </div>
  </div>
  <div class="elementor-element" data-widget_type="heading.default">
    <div class="elementor-widget-container">
      <h2 class="elementor-heading-title"><em>Brassica oleraceae</em> Capitata group</h2>
    </div>
  </div>
  <div class="elementor-element" data-widget_type="text-editor.default">
    <div class="elementor-widget-container">
      <p>ගෝවා බ්‍රැසිකේසියේ කුලයට අයත් බෝගයකි.</p>
    </div>
  </div>
  <div class="elementor-element" data-widget_type="heading.default">
    <div class="elementor-widget-container">
      <h2 class="elementor-heading-title">නිකුත් කරන ලද ප්‍රභේද</h2>
    </div>
  </div>
  <div class="elementor-element" data-widget_type="icon-list.default">
    <div class="elementor-widget-container">
      <ul class="elementor-icon-list-items">
        <li class="elementor-icon-list-item"><span class="elementor-icon-list-text">ග්‍රීන් කොර්නටි</span></li>
      </ul>
    </div>
  </div>
  <div class="elementor-element" data-widget_type="heading.default">
    <div class="elementor-widget-container">
      <h2 class="elementor-heading-title">පොහොර</h2>
    </div>
  </div>
  <div class="elementor-element" data-widget_type="text-editor.default">
    <div class="elementor-widget-container">
      <p>කාබනික පොහොර හෙක්ටයාරයට ටොන් 10</p>
      <table><tbody>
        <tr><td>යුරියා</td><td>110</td></tr>
        <tr><td>මුලික පොහොර</td><td>110</td></tr>
      </tbody></table>
    </div>
  </div>
  <div class="elementor-element" data-widget_type="heading.default">
    <div class="elementor-widget-container">
      <h2 class="elementor-heading-title">පළිබෝධ කළමනාකරණය</h2>
    </div>
  </div>
  <div class="elementor-element" data-widget_type="toggle.default">
    <div class="elementor-widget-container">
      <div class="elementor-toggle">
        <div class="elementor-toggle-item">
          <a class="elementor-toggle-title">1. දියමන්ති පිට සළඹයා</a>
          <div class="elementor-tab-content"><p><strong>හානිය</strong></p><ul><li>පත්‍ර කා දමයි</li></ul></div>
        </div>
      </div>
    </div>
  </div>
</div>
</div></article>
</body></html>
"""


@pytest.fixture
def loader() -> DoaHordiLoader:
    return DoaHordiLoader()


def _raw_from_html(html: str, uri: str = "/test/cabbage.html") -> RawContent:
    return RawContent(
        source_uri=uri,
        resolved_uri=uri,
        source_type=SOURCE_TYPE_FILE,
        media_type="text/html",
        data=html.encode("utf-8"),
    )


def test_load_minimal_crop_metadata(loader: DoaHordiLoader) -> None:
    docs = loader.load(_raw_from_html(MINIMAL_HTML))
    assert docs[0].metadata["crop_name"] == "ගෝවා"
    assert "Brassica oleraceae" in docs[0].metadata["scientific_name"]


def test_load_minimal_section_headings(loader: DoaHordiLoader) -> None:
    docs = loader.load(_raw_from_html(MINIMAL_HTML))
    section_names = [d.metadata["section_name"] for d in docs]
    assert "නිකුත් කරන ලද ප්‍රභේද" in section_names
    assert "පොහොර" in section_names
    assert any("පළිබෝධ කළමනාකරණය" in s for s in section_names)


def test_load_minimal_icon_list_and_table(loader: DoaHordiLoader) -> None:
    docs = loader.load(_raw_from_html(MINIMAL_HTML))
    varieties = next(d for d in docs if d.metadata["section_name"] == "නිකුත් කරන ලද ප්‍රභේද")
    assert "ග්‍රීන් කොර්නටි" in varieties.text

    fertilizer = next(d for d in docs if d.metadata["section_name"] == "පොහොර")
    assert "|" in fertilizer.text
    assert "යුරියා" in fertilizer.text


def test_toggle_becomes_separate_document(loader: DoaHordiLoader) -> None:
    docs = loader.load(_raw_from_html(MINIMAL_HTML))
    pest = next(d for d in docs if "දියමන්ති පිට සළඹයා" in d.metadata["section_name"])
    assert "**දියමන්ති පිට සළඹයා**" in pest.text or "දියමන්ති පිට සළඹයා" in pest.text
    assert "හානිය" in pest.text


def test_doa_hordi_chunker_produces_chunks() -> None:
    docs = DoaHordiLoader().load(_raw_from_html(MINIMAL_HTML))
    chunks = DoaHordiChunker().chunk(docs, crop_tag="ගෝවා")
    assert len(chunks) >= 3
    assert all(c.metadata["crop_tag"] == "ගෝවා" for c in chunks)


@pytest.mark.skipif(not CABBAGE_HTML.exists(), reason="cabbage.html fixture not present")
def test_load_cabbage_full_page(loader: DoaHordiLoader) -> None:
    raw = RawContent(
        source_uri=str(CABBAGE_HTML),
        resolved_uri=str(CABBAGE_HTML),
        source_type=SOURCE_TYPE_FILE,
        media_type="text/html",
        data=CABBAGE_HTML.read_bytes(),
    )
    docs = loader.load(raw)
    section_names = [d.metadata["section_name"] for d in docs]

    assert len(docs) >= 10
    assert docs[0].metadata["crop_name"] == "ගෝවා"
    assert "Brassica" in docs[0].metadata["scientific_name"]
    assert any("පළිබෝධ කළමනාකරණය" in s for s in section_names)
    assert any("Plutella" in s or "දියමන්ති" in s for s in section_names)
    assert any("පොහොර" in s for s in section_names)

    chunks = DoaHordiChunker().chunk(docs, crop_tag="ගෝවා")
    assert len(chunks) >= 10
