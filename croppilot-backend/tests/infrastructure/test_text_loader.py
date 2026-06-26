from pathlib import Path

import pytest

from app.domains.ingestion.source_types import SOURCE_TYPE_FILE, SOURCE_TYPE_WEB_URL
from app.infrastructure.loaders.text_loader import TextDocumentLoader

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def loader() -> TextDocumentLoader:
    return TextDocumentLoader()


def test_supports_txt_files(loader: TextDocumentLoader) -> None:
    assert loader.supports("pepper.txt", SOURCE_TYPE_FILE) is True
    assert loader.supports("pepper.pdf", SOURCE_TYPE_FILE) is False
    assert loader.supports("pepper.txt", SOURCE_TYPE_WEB_URL) is False


def test_load_returns_list_of_knowledge_documents(loader: TextDocumentLoader) -> None:
    path = str(FIXTURES_DIR / "pepper.txt")
    docs = loader.load(path, SOURCE_TYPE_FILE)

    assert isinstance(docs, list)
    assert len(docs) == 1
    doc = docs[0]
    assert doc.metadata["source_uri"] == path
    assert doc.metadata["source_type"] == SOURCE_TYPE_FILE
    assert doc.metadata["loader"] == "text"
    assert doc.metadata["media_type"] == "text/plain"
    assert doc.text.startswith("Pepper")
