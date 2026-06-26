from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import pytest

from app.infrastructure.loaders.web_snapshot import (
    MANIFEST_FILENAME,
    SnapshotFiles,
    entry_for_snapshot,
    load_manifest,
    parse_urls_file,
    save_manifest,
    slug_from_url,
)


def test_slug_from_url() -> None:
    assert slug_from_url("https://dea.gov.lk/pepper/") == "dea-gov-lk-pepper"
    assert slug_from_url("https://example.com/") == "example-com"


def test_parse_urls_file_ignores_comments_and_blanks(tmp_path: Path) -> None:
    urls_file = tmp_path / "urls.txt"
    urls_file.write_text(
        "# comment\n\nhttps://example.com/a\n  \nhttps://example.com/b\n",
        encoding="utf-8",
    )
    assert parse_urls_file(urls_file) == [
        "https://example.com/a",
        "https://example.com/b",
    ]


def test_manifest_roundtrip(tmp_path: Path) -> None:
    collection_dir = tmp_path / "collection"
    collection_dir.mkdir()
    manifest_path = collection_dir / MANIFEST_FILENAME

    snapshot = SnapshotFiles(
        url="https://example.com/pepper",
        final_url="https://example.com/pepper/",
        content_type="text/html",
        html_path=collection_dir / "html" / "example-com-pepper.html",
        md_path=collection_dir / "md" / "example-com-pepper.md",
        markdown_text="# Pepper",
        char_count=8,
    )
    entry = entry_for_snapshot(
        snapshot,
        collection_dir,
        entry_id="example-com-pepper",
        fetched_at="2026-06-26T12:00:00+00:00",
    )
    save_manifest(manifest_path, collection_dir, [entry])

    loaded = load_manifest(manifest_path)
    assert loaded["version"] == 1
    assert len(loaded["entries"]) == 1
    assert loaded["entries"][0]["url"] == "https://example.com/pepper"
    assert loaded["entries"][0]["html_path"] == "html/example-com-pepper.html"
    assert loaded["entries"][0]["md_path"] == "md/example-com-pepper.md"


def test_snapshot_url_to_files_writes_html_and_md(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from app.infrastructure.extractors import http_extractor as http_mod

    html_bytes = b"<html><body><h1>Pepper</h1></body></html>"

    mock_response = MagicMock()
    mock_response.geturl.return_value = "https://example.com/pepper/"
    mock_response.headers.get_content_type.return_value = "text/html"
    mock_response.headers.get_content_charset.return_value = "utf-8"
    mock_response.read.return_value = html_bytes
    mock_response.__enter__.return_value = mock_response
    mock_response.__exit__.return_value = False

    monkeypatch.setattr(
        "app.infrastructure.extractors.http_extractor.urlopen",
        lambda *a, **kw: mock_response,
    )

    doc = MagicMock()
    doc.page_content = "# Pepper"
    doc.metadata = {}

    mock_loader_instance = MagicMock()
    mock_loader_instance.load.return_value = [doc]
    mock_cls = MagicMock(return_value=mock_loader_instance)

    mock_export_type = ModuleType("langchain_docling.loader")
    mock_export_type.ExportType = MagicMock(MARKDOWN="markdown")
    mock_pkg = ModuleType("langchain_docling")
    mock_pkg.DoclingLoader = mock_cls

    monkeypatch.setitem(sys.modules, "langchain_docling", mock_pkg)
    monkeypatch.setitem(sys.modules, "langchain_docling.loader", mock_export_type)

    html_path = tmp_path / "html" / "example-com-pepper.html"
    md_path = tmp_path / "md" / "example-com-pepper.md"

    from app.infrastructure.loaders.web_snapshot import snapshot_url_to_files

    result = snapshot_url_to_files(
        "https://example.com/pepper",
        html_path,
        md_path,
    )

    assert html_path.is_file()
    assert html_path.read_bytes() == html_bytes
    assert md_path.read_text(encoding="utf-8") == "# Pepper"
    assert result.char_count == len("# Pepper")
    assert result.final_url == "https://example.com/pepper/"
