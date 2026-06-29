from __future__ import annotations

import pytest

from app.shared.document.content import RawContent
from app.shared.document.source_types import SOURCE_TYPE_FILE, SOURCE_TYPE_WEB_URL
from app.infrastructure.loaders.html_plain_loader import HtmlPlainLoader


@pytest.fixture
def loader() -> HtmlPlainLoader:
    return HtmlPlainLoader()


def _raw(
    html: str,
    source_uri: str = "https://example.com/page",
    source_type: str = SOURCE_TYPE_WEB_URL,
    media_type: str = "text/html",
) -> RawContent:
    return RawContent(
        source_uri=source_uri,
        resolved_uri=source_uri,
        source_type=source_type,
        media_type=media_type,
        data=html.encode("utf-8"),
    )


def test_supports_html_media_type(loader: HtmlPlainLoader) -> None:
    assert loader.supports(_raw("<html/>", media_type="text/html")) is True
    assert loader.supports(_raw("<html/>", media_type="application/xhtml+xml")) is True


def test_does_not_support_plain_text(loader: HtmlPlainLoader) -> None:
    raw = RawContent(
        source_uri="file.txt",
        resolved_uri="file.txt",
        source_type=SOURCE_TYPE_FILE,
        media_type="text/plain",
        data=b"hello",
    )
    assert loader.supports(raw) is False


def test_does_not_support_pdf(loader: HtmlPlainLoader) -> None:
    raw = RawContent(
        source_uri="report.pdf",
        resolved_uri="report.pdf",
        source_type=SOURCE_TYPE_FILE,
        media_type="application/pdf",
        data=b"",
    )
    assert loader.supports(raw) is False


def test_load_extracts_text_from_html(loader: HtmlPlainLoader) -> None:
    html = "<html><body><h1>Pepper</h1><p>Cultivation guide</p><script>ignored()</script></body></html>"
    raw = _raw(html)

    docs = loader.load(raw)

    assert len(docs) == 1
    assert "Pepper" in docs[0].text
    assert "Cultivation guide" in docs[0].text
    assert "ignored" not in docs[0].text
    assert docs[0].metadata["loader"] == "html_plain"
    assert docs[0].metadata["source_type"] == SOURCE_TYPE_WEB_URL
    assert docs[0].metadata["media_type"] == "text/html"


def test_load_html_file_via_local_path(loader: HtmlPlainLoader, tmp_path) -> None:
    html_file = tmp_path / "page.html"
    html_file.write_text("<html><body><p>From file</p></body></html>", encoding="utf-8")
    raw = RawContent(
        source_uri=str(html_file),
        resolved_uri=str(html_file),
        source_type=SOURCE_TYPE_FILE,
        media_type="text/html",
        data=b"",
        local_path=html_file,
    )

    docs = loader.load(raw)
    assert "From file" in docs[0].text


def test_load_empty_html_raises(loader: HtmlPlainLoader) -> None:
    raw = _raw("<html><body></body></html>")
    with pytest.raises(ValueError, match="No text content"):
        loader.load(raw)
