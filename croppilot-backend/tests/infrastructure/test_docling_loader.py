import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import pytest

from app.shared.document.content import RawContent
from app.shared.document.loader import KnowledgeDocument
from app.shared.document.source_types import SOURCE_TYPE_FILE, SOURCE_TYPE_WEB_URL
from app.infrastructure.loaders.docling_loader import DoclingLoader
from app.infrastructure.loaders.validation import LoaderValidationError, validate_loader_selection


@pytest.fixture
def loader() -> DoclingLoader:
    return DoclingLoader()


def _raw(
    path: str = "/path/to/report.pdf",
    media_type: str = "application/pdf",
    source_type: str = SOURCE_TYPE_FILE,
    data: bytes = b"%PDF fake",
    local_path: Path | None = None,
) -> RawContent:
    return RawContent(
        source_uri=path,
        resolved_uri=path,
        source_type=source_type,
        media_type=media_type,
        data=data,
        local_path=local_path,
    )


def _mock_docling(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    doc1 = MagicMock()
    doc1.page_content = "# Section One\n\nContent one."
    doc1.metadata = {"page": 0}
    doc2 = MagicMock()
    doc2.page_content = "## Section Two\n\nContent two."
    doc2.metadata = {"page": 1}
    doc3 = MagicMock()
    doc3.page_content = "   "
    doc3.metadata = {}

    mock_loader_instance = MagicMock()
    mock_loader_instance.load.return_value = [doc1, doc2, doc3]
    mock_cls = MagicMock(return_value=mock_loader_instance)

    mock_export_type = ModuleType("langchain_docling.loader")
    mock_export_type.ExportType = MagicMock(MARKDOWN="markdown")
    mock_pkg = ModuleType("langchain_docling")
    mock_pkg.DoclingLoader = mock_cls

    monkeypatch.setitem(sys.modules, "langchain_docling", mock_pkg)
    monkeypatch.setitem(sys.modules, "langchain_docling.loader", mock_export_type)
    return mock_cls


def test_supports_docling_formats(loader: DoclingLoader) -> None:
    assert loader.supports(_raw("/f.pdf", "application/pdf")) is True
    assert loader.supports(_raw("/f.html", "text/html")) is True
    assert loader.supports(_raw("/f.txt", "text/plain")) is True
    assert loader.supports(_raw("/f.md", "text/markdown")) is True


def test_supports_web_html(loader: DoclingLoader) -> None:
    raw = _raw("/https://dea.gov.lk/pepper", "text/html", SOURCE_TYPE_WEB_URL)
    assert loader.supports(raw) is True


def test_validate_loader_reports_unsupported_media(loader: DoclingLoader) -> None:
    raw = _raw("/path/report.xyz", "application/octet-stream")
    with pytest.raises(LoaderValidationError) as exc:
        validate_loader_selection(loader, raw)
    assert "application/octet-stream" in exc.value.message


def test_load_returns_list_of_knowledge_documents(
    monkeypatch: pytest.MonkeyPatch, loader: DoclingLoader, tmp_path: Path
) -> None:
    _mock_docling(monkeypatch)
    # Use a real temp file so DoclingLoader has a local_path (avoids Docling temp logic in test)
    pdf_file = tmp_path / "report.pdf"
    pdf_file.write_bytes(b"%PDF fake")
    raw = _raw(str(pdf_file), "application/pdf", local_path=pdf_file, data=b"")

    result = loader.load(raw)

    assert isinstance(result, list)
    assert len(result) == 2
    assert all(isinstance(d, KnowledgeDocument) for d in result)
    assert result[0].text == "# Section One\n\nContent one."
    assert result[0].metadata["source_uri"] == str(pdf_file)
    assert result[1].text == "## Section Two\n\nContent two."


def test_load_html_from_web(
    monkeypatch: pytest.MonkeyPatch, loader: DoclingLoader
) -> None:
    doc = MagicMock()
    doc.page_content = "Hello"
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

    raw = RawContent(
        source_uri="https://example.com/pepper",
        resolved_uri="https://example.com/pepper",
        source_type=SOURCE_TYPE_WEB_URL,
        media_type="text/html",
        data=b"<html><body>Hello</body></html>",
    )

    result = loader.load(raw)
    assert len(result) == 1
    assert result[0].text == "Hello"
    assert result[0].metadata["source_uri"] == "https://example.com/pepper"
    assert result[0].metadata["loader"] == "docling"
    assert result[0].metadata["export_format"] == "markdown"
