from __future__ import annotations

from pathlib import Path

import pytest

from app.shared.document.source_types import SOURCE_TYPE_FILE, SOURCE_TYPE_WEB_URL
from app.infrastructure.extractors.file_extractor import FileExtractor

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def extractor() -> FileExtractor:
    return FileExtractor()


def test_supports_file_paths(extractor: FileExtractor) -> None:
    assert extractor.supports("/path/to/file.txt", SOURCE_TYPE_FILE) is True
    assert extractor.supports("relative/path.pdf", SOURCE_TYPE_FILE) is True
    assert extractor.supports("https://example.com/page", SOURCE_TYPE_WEB_URL) is False
    assert extractor.supports("https://example.com/page", SOURCE_TYPE_FILE) is False


def test_extract_txt_reads_bytes(extractor: FileExtractor) -> None:
    path = str(FIXTURES_DIR / "pepper.txt")
    raw = extractor.extract(path, SOURCE_TYPE_FILE)

    assert raw.media_type == "text/plain"
    assert raw.source_uri == path
    assert raw.resolved_uri == path
    assert raw.source_type == SOURCE_TYPE_FILE
    assert raw.local_path == Path(path)
    assert len(raw.data) > 0


def test_extract_md_file(tmp_path: Path, extractor: FileExtractor) -> None:
    md_file = tmp_path / "notes.md"
    md_file.write_text("# Title\n\nContent.", encoding="utf-8")
    raw = extractor.extract(str(md_file), SOURCE_TYPE_FILE)

    assert raw.media_type == "text/markdown"
    assert raw.data == b"# Title\n\nContent."


def test_extract_html_file(tmp_path: Path, extractor: FileExtractor) -> None:
    html_file = tmp_path / "page.html"
    html_file.write_text("<html><body>Test</body></html>", encoding="utf-8")
    raw = extractor.extract(str(html_file), SOURCE_TYPE_FILE)

    assert raw.media_type == "text/html"
    assert b"Test" in raw.data


def test_extract_pdf_leaves_data_empty(tmp_path: Path, extractor: FileExtractor) -> None:
    pdf_file = tmp_path / "report.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 fake")
    raw = extractor.extract(str(pdf_file), SOURCE_TYPE_FILE)

    assert raw.media_type == "application/pdf"
    assert raw.data == b""
    assert raw.local_path == pdf_file


def test_extract_missing_file_raises(extractor: FileExtractor) -> None:
    with pytest.raises(FileNotFoundError):
        extractor.extract("/nonexistent/path/file.txt", SOURCE_TYPE_FILE)
