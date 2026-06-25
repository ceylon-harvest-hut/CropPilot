import pytest
from pathlib import Path

from app.infrastructure.extractors.text_extractor import TextFileExtractor

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"

def test_read_real_pepper_sample(extractor):
    file_path = FIXTURES_DIR / "pepper.txt"
    text = extractor.read(str(file_path))

    assert text.startswith("Pepper")
    assert "Piper nigrum" in text


@pytest.fixture
def extractor() -> TextFileExtractor:
    return TextFileExtractor()


def test_read_returns_file_contents(extractor: TextFileExtractor, tmp_path) -> None:
    file_path = tmp_path / "pepper.txt"
    file_path.write_text("Pepper\nPiper nigrum L.\n", encoding="utf-8")

    result = extractor.read(str(file_path))

    assert result == "Pepper\nPiper nigrum L.\n"


def test_read_raises_when_file_not_found(extractor: TextFileExtractor) -> None:
    with pytest.raises(FileNotFoundError, match="File not found"):
        extractor.read("/path/that/does/not/exist.txt")


def test_read_raises_when_path_is_directory(extractor: TextFileExtractor, tmp_path) -> None:
    with pytest.raises(ValueError, match="Path is not a file"):
        extractor.read(str(tmp_path))