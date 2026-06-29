from __future__ import annotations

from pathlib import Path

import pytest

from app.shared.document.content import RawContent
from app.shared.document.source_types import SOURCE_TYPE_FILE
from app.infrastructure.loaders.text_loader import TextLoader

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def loader() -> TextLoader:
    return TextLoader()


def _raw(path: str, media_type: str = "text/plain") -> RawContent:
    p = Path(path)
    return RawContent(
        source_uri=path,
        resolved_uri=path,
        source_type=SOURCE_TYPE_FILE,
        media_type=media_type,
        data=p.read_bytes() if p.exists() else b"",
        local_path=p if p.exists() else None,
    )


def test_supports_txt_and_markdown(loader: TextLoader) -> None:
    assert loader.supports(_raw("pepper.txt", "text/plain")) is True
    assert loader.supports(_raw("notes.md", "text/markdown")) is True
    assert loader.supports(_raw("notes.markdown", "text/markdown")) is True
    assert loader.supports(_raw("report.pdf", "application/pdf")) is False
    assert loader.supports(_raw("page.html", "text/html")) is False


def test_load_returns_knowledge_documents(loader: TextLoader) -> None:
    path = str(FIXTURES_DIR / "pepper.txt")
    raw = _raw(path)

    docs = loader.load(raw)

    assert isinstance(docs, list)
    assert len(docs) == 1
    doc = docs[0]
    assert doc.metadata["source_uri"] == path
    assert doc.metadata["source_type"] == SOURCE_TYPE_FILE
    assert doc.metadata["loader"] == "text"
    assert doc.metadata["media_type"] == "text/plain"
    assert doc.text.startswith("Pepper")
