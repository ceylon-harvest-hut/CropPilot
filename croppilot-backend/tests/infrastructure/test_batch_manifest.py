from __future__ import annotations

from pathlib import Path

import pytest

from app.infrastructure.ingestion.batch_manifest import (
    crop_name_from_dea_html_filename,
    entries_from_html_dir,
    parse_manifest,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MANIFEST = REPO_ROOT / "data" / "web_collection" / "ingest_manifest.txt"
HTML_DIR = REPO_ROOT / "data" / "web_collection" / "html"


def test_crop_name_from_dea_html_filename() -> None:
    assert crop_name_from_dea_html_filename("dea-gov-lk-pepper.html") == "Pepper"
    assert crop_name_from_dea_html_filename("dea-gov-lk-areca-nut.html") == "Areca Nut"
    assert crop_name_from_dea_html_filename("dea-gov-lk-lemon-grass.html") == "Lemon Grass"


def test_parse_manifest_resolves_relative_paths(tmp_path: Path) -> None:
    doc = tmp_path / "docs" / "pepper.txt"
    doc.parent.mkdir()
    doc.write_text("Pepper crop guide.", encoding="utf-8")

    manifest = tmp_path / "batch.txt"
    manifest.write_text(f"docs/pepper.txt,Pepper,file\n", encoding="utf-8")

    entries = parse_manifest(manifest)
    assert len(entries) == 1
    assert entries[0].source_uri == str(doc.resolve())
    assert entries[0].crop_name == "Pepper"
    assert entries[0].resolved_source_type() == "file"


def test_parse_manifest_supports_web_urls(tmp_path: Path) -> None:
    manifest = tmp_path / "batch.txt"
    manifest.write_text("https://dea.gov.lk/pepper/,Pepper,web_url\n", encoding="utf-8")

    entries = parse_manifest(manifest)
    assert entries[0].source_uri == "https://dea.gov.lk/pepper/"
    assert entries[0].resolved_source_type() == "web_url"


def test_parse_manifest_ignores_comments_and_blank_lines(tmp_path: Path) -> None:
    doc = tmp_path / "a.txt"
    doc.write_text("text", encoding="utf-8")
    manifest = tmp_path / "batch.txt"
    manifest.write_text(
        "# comment\n\na.txt,Crop A\n# another\n",
        encoding="utf-8",
    )

    entries = parse_manifest(manifest)
    assert len(entries) == 1
    assert entries[0].crop_name == "Crop A"


@pytest.mark.skipif(not MANIFEST.exists(), reason="ingest_manifest.txt fixture not present")
def test_project_ingest_manifest_parses() -> None:
    entries = parse_manifest(MANIFEST)
    assert len(entries) >= 10
    assert any(e.crop_name == "Pepper" for e in entries)


@pytest.mark.skipif(not HTML_DIR.exists(), reason="html collection not present")
def test_entries_from_html_dir() -> None:
    entries = entries_from_html_dir(HTML_DIR)
    assert len(entries) >= 10
    pepper = next(e for e in entries if e.crop_name == "Pepper")
    assert pepper.source_uri.endswith("dea-gov-lk-pepper.html")
    assert pepper.resolved_source_type() == "file"
