import sys
from types import ModuleType
from unittest.mock import MagicMock

import pytest

from app.domains.ingestion.loader import KnowledgeDocument
from app.domains.ingestion.source_types import SOURCE_TYPE_FILE, SOURCE_TYPE_WEB_URL
from app.infrastructure.loaders.docling_loader import DoclingDocumentLoader


@pytest.fixture
def loader() -> DoclingDocumentLoader:
    return DoclingDocumentLoader()


def test_supports_docling_formats(loader: DoclingDocumentLoader) -> None:
    assert loader.supports("report.pdf", SOURCE_TYPE_FILE) is True
    assert loader.supports("page.html", SOURCE_TYPE_FILE) is True
    assert loader.supports("page.htm", SOURCE_TYPE_FILE) is True
    assert loader.supports("notes.docx", SOURCE_TYPE_FILE) is True
    assert loader.supports("pepper.txt", SOURCE_TYPE_FILE) is True
    assert loader.supports("report.pdf", SOURCE_TYPE_WEB_URL) is False


def test_load_returns_list_of_knowledge_documents(monkeypatch: pytest.MonkeyPatch) -> None:
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

    mock_docling_loader_cls = MagicMock(return_value=mock_loader_instance)

    mock_export_type = ModuleType("langchain_docling.loader")
    mock_export_type.ExportType = MagicMock(MARKDOWN="markdown")

    mock_docling_pkg = ModuleType("langchain_docling")
    mock_docling_pkg.DoclingLoader = mock_docling_loader_cls

    monkeypatch.setitem(sys.modules, "langchain_docling", mock_docling_pkg)
    monkeypatch.setitem(sys.modules, "langchain_docling.loader", mock_export_type)

    result = DoclingDocumentLoader().load("/path/to/report.pdf", SOURCE_TYPE_FILE)

    assert isinstance(result, list)
    assert len(result) == 2
    assert all(isinstance(d, KnowledgeDocument) for d in result)
    assert result[0].text == "# Section One\n\nContent one."
    assert result[0].metadata["source_uri"] == "/path/to/report.pdf"
    assert result[1].text == "## Section Two\n\nContent two."


def test_load_html_media_type(monkeypatch: pytest.MonkeyPatch) -> None:
    raw_doc = MagicMock()
    raw_doc.page_content = "Hello"
    raw_doc.metadata = {}

    mock_loader_instance = MagicMock()
    mock_loader_instance.load.return_value = [raw_doc]

    mock_docling_loader_cls = MagicMock(return_value=mock_loader_instance)
    mock_export_type = ModuleType("langchain_docling.loader")
    mock_export_type.ExportType = MagicMock(MARKDOWN="markdown")
    mock_docling_pkg = ModuleType("langchain_docling")
    mock_docling_pkg.DoclingLoader = mock_docling_loader_cls

    monkeypatch.setitem(sys.modules, "langchain_docling", mock_docling_pkg)
    monkeypatch.setitem(sys.modules, "langchain_docling.loader", mock_export_type)

    result = DoclingDocumentLoader().load("/path/to/pepper.html", SOURCE_TYPE_FILE)

    assert len(result) == 1
    assert result[0].text == "Hello"
    assert result[0].metadata["source_uri"] == "/path/to/pepper.html"
