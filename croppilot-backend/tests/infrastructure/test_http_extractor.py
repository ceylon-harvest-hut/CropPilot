from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock
from urllib.error import URLError

import pytest

from app.shared.document.content import ExtractOptions
from app.shared.document.source_types import SOURCE_TYPE_FILE, SOURCE_TYPE_WEB_URL
from app.infrastructure.extractors.http_extractor import HttpExtractor


@pytest.fixture
def extractor() -> HttpExtractor:
    return HttpExtractor()


def _mock_urlopen(body: bytes, *, content_type: str = "text/html", charset: str = "utf-8"):
    mock_response = MagicMock()
    mock_response.geturl.return_value = "https://example.com/pepper"
    mock_response.headers.get_content_type.return_value = content_type
    mock_response.headers.get_content_charset.return_value = charset
    mock_response.read.return_value = body
    mock_response.__enter__.return_value = mock_response
    mock_response.__exit__.return_value = False
    return mock_response


def test_supports_http_urls(extractor: HttpExtractor) -> None:
    assert extractor.supports("https://example.com/page", SOURCE_TYPE_WEB_URL) is True
    assert extractor.supports("http://example.com/page", SOURCE_TYPE_WEB_URL) is True
    assert extractor.supports("/path/file.txt", SOURCE_TYPE_FILE) is False
    assert extractor.supports("https://example.com", SOURCE_TYPE_FILE) is False


def test_extract_html(monkeypatch: pytest.MonkeyPatch, extractor: HttpExtractor) -> None:
    html = b"<html><body><p>Pepper cultivation guide</p></body></html>"
    monkeypatch.setattr(
        "app.infrastructure.extractors.http_extractor.urlopen",
        lambda *a, **kw: _mock_urlopen(html),
    )

    raw = extractor.extract("https://example.com/pepper", SOURCE_TYPE_WEB_URL)

    assert raw.data == html
    assert raw.media_type == "text/html"
    assert raw.source_uri == "https://example.com/pepper"
    assert raw.resolved_uri == "https://example.com/pepper"
    assert raw.source_type == SOURCE_TYPE_WEB_URL
    assert raw.local_path is None
    assert raw.persisted_path is None


def test_extract_pdf_bytes(monkeypatch: pytest.MonkeyPatch, extractor: HttpExtractor) -> None:
    """Binary responses (PDF) must not be blocked."""
    pdf_bytes = b"%PDF-1.4 fake pdf content"
    monkeypatch.setattr(
        "app.infrastructure.extractors.http_extractor.urlopen",
        lambda *a, **kw: _mock_urlopen(pdf_bytes, content_type="application/pdf"),
    )

    raw = extractor.extract("https://example.com/guide.pdf", SOURCE_TYPE_WEB_URL)

    assert raw.data == pdf_bytes
    assert raw.media_type == "application/pdf"


def test_extract_persist_raw(
    monkeypatch: pytest.MonkeyPatch, extractor: HttpExtractor, tmp_path: Path
) -> None:
    html = b"<html><body>test</body></html>"
    monkeypatch.setattr(
        "app.infrastructure.extractors.http_extractor.urlopen",
        lambda *a, **kw: _mock_urlopen(html),
    )

    out_path = tmp_path / "html" / "test.html"
    opts = ExtractOptions(persist_raw=True, raw_output_path=out_path)
    raw = extractor.extract("https://example.com/test", SOURCE_TYPE_WEB_URL, opts)

    assert out_path.is_file()
    assert out_path.read_bytes() == html
    assert raw.persisted_path == out_path


def test_extract_timeout_raises_clear_error(
    monkeypatch: pytest.MonkeyPatch, extractor: HttpExtractor
) -> None:
    monkeypatch.setattr(
        "app.infrastructure.extractors.http_extractor.urlopen",
        lambda *a, **kw: (_ for _ in ()).throw(TimeoutError("timed out")),
    )
    with pytest.raises(ValueError, match="timed out after 30s"):
        extractor.extract("https://example.com/slow", SOURCE_TYPE_WEB_URL)


def test_extract_custom_timeout(monkeypatch: pytest.MonkeyPatch, extractor: HttpExtractor) -> None:
    seen: dict[str, int] = {}

    def mock_urlopen(request, timeout=None, context=None):
        seen["timeout"] = timeout
        raise TimeoutError("timed out")

    monkeypatch.setattr("app.infrastructure.extractors.http_extractor.urlopen", mock_urlopen)

    with pytest.raises(ValueError, match="timed out after 90s"):
        extractor.extract(
            "https://example.com/slow",
            SOURCE_TYPE_WEB_URL,
            ExtractOptions(timeout_seconds=90),
        )

    assert seen["timeout"] == 90


def test_extract_urlerror_timeout(monkeypatch: pytest.MonkeyPatch, extractor: HttpExtractor) -> None:
    monkeypatch.setattr(
        "app.infrastructure.extractors.http_extractor.urlopen",
        lambda *a, **kw: (_ for _ in ()).throw(URLError(TimeoutError("timed out"))),
    )
    with pytest.raises(ValueError, match="timed out"):
        extractor.extract("https://example.com/slow", SOURCE_TYPE_WEB_URL)
