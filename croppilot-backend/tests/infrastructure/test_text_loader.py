from pathlib import Path

import pytest

from app.infrastructure.loaders.text_loader import TextDocumentLoader

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def loader() -> TextDocumentLoader:
    return TextDocumentLoader()


def test_supports_txt_files(loader: TextDocumentLoader) -> None:
    assert loader.supports("pepper.txt") is True
    assert loader.supports("pepper.pdf") is False


def test_load_returns_list_of_knowledge_documents(loader: TextDocumentLoader) -> None:
    path = str(FIXTURES_DIR / "pepper.txt")
    docs = loader.load(path)

    assert isinstance(docs, list)
    assert len(docs) == 1
    doc = docs[0]
    assert doc.metadata["source_uri"] == path
    assert doc.metadata["media_type"] == "text/plain"
    assert doc.text.startswith("Pepper")