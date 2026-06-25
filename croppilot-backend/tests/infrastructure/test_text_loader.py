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


def test_load_returns_loaded_document(loader: TextDocumentLoader) -> None:
    path = str(FIXTURES_DIR / "pepper.txt")
    doc = loader.load(path)

    assert doc.source_uri == path
    assert doc.media_type == "text/plain"
    assert doc.text.startswith("Pepper")