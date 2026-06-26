from unittest.mock import MagicMock
from urllib.error import URLError

import pytest

from app.domains.ingestion.source_types import SOURCE_TYPE_FILE, SOURCE_TYPE_WEB_URL
from app.infrastructure.loaders.html_text import html_to_text
from app.infrastructure.loaders.validation import LoaderValidationError, validate_loader_selection
from app.infrastructure.loaders.web_url_loader import WebUrlLoader
from app.infrastructure.loaders.text_loader import TextDocumentLoader


def test_html_to_text_strips_tags() -> None:
    html = "<html><body><h1>Title</h1><p>Hello <b>world</b></p><script>ignore()</script></body></html>"
    text = html_to_text(html)
    assert "Title" in text
    assert "Hello world" in text
    assert "ignore" not in text


def test_web_loader_supports_http_urls() -> None:
    loader = WebUrlLoader()
    assert loader.supports("https://example.com/page", SOURCE_TYPE_WEB_URL) is True
    assert loader.supports("/path/file.txt", SOURCE_TYPE_FILE) is False


def test_validate_loader_rejects_type_mismatch() -> None:
    loader = TextDocumentLoader()
    with pytest.raises(LoaderValidationError) as exc:
        validate_loader_selection(loader, "https://example.com", SOURCE_TYPE_WEB_URL)
    assert exc.value.context["allowed_loaders"] == ["web"]


def test_validate_loader_rejects_file_path_for_web_type() -> None:
    loader = WebUrlLoader()
    with pytest.raises(ValueError, match="must be an http"):
        validate_loader_selection(loader, "/path/pepper.txt", SOURCE_TYPE_WEB_URL)


def test_web_loader_load_fetches_html(monkeypatch: pytest.MonkeyPatch) -> None:
    html = b"<html><body><p>Pepper cultivation guide</p></body></html>"
    mock_response = MagicMock()
    mock_response.geturl.return_value = "https://example.com/pepper"
    mock_response.headers.get_content_type.return_value = "text/html"
    mock_response.headers.get_content_charset.return_value = "utf-8"
    mock_response.read.return_value = html
    mock_response.__enter__.return_value = mock_response
    mock_response.__exit__.return_value = False

    monkeypatch.setattr(
        "app.infrastructure.loaders.web_url_loader.urlopen",
        lambda *args, **kwargs: mock_response,
    )

    docs = WebUrlLoader().load("https://example.com/pepper", SOURCE_TYPE_WEB_URL)

    assert len(docs) == 1
    assert "Pepper cultivation guide" in docs[0].text
    assert docs[0].metadata["source_type"] == SOURCE_TYPE_WEB_URL
    assert docs[0].metadata["loader"] == "web"


def test_web_loader_timeout_raises_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_timeout(*args: object, **kwargs: object) -> None:
        raise TimeoutError("The read operation timed out")

    monkeypatch.setattr(
        "app.infrastructure.loaders.web_url_loader.urlopen",
        raise_timeout,
    )

    with pytest.raises(ValueError, match="timed out after 30s"):
        WebUrlLoader().load("https://example.com/slow", SOURCE_TYPE_WEB_URL)


def test_web_loader_urlerror_timeout_raises_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_url_error(*args: object, **kwargs: object) -> None:
        raise URLError(TimeoutError("timed out"))

    monkeypatch.setattr(
        "app.infrastructure.loaders.web_url_loader.urlopen",
        raise_url_error,
    )

    with pytest.raises(ValueError, match="timed out after 30s"):
        WebUrlLoader().load("https://example.com/slow", SOURCE_TYPE_WEB_URL)
