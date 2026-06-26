from __future__ import annotations

import mimetypes
from pathlib import Path
from urllib.parse import urlparse

from app.domains.ingestion.content import ExtractOptions, RawContent
from app.domains.ingestion.extractor import ContentExtractor
from app.domains.ingestion.source_types import SOURCE_TYPE_FILE

_EXTENSION_MEDIA_TYPES: dict[str, str] = {
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".html": "text/html",
    ".htm": "text/html",
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}

# Binary types where we skip reading bytes into memory; loaders use local_path instead.
_BINARY_MEDIA_TYPES = frozenset({
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
})


class FileExtractor(ContentExtractor):
    """Read a local file into a RawContent object.

    For binary files (PDF, DOCX, PPTX) ``data`` is left as empty bytes and
    loaders should read content via ``local_path`` instead.
    """

    name = "file"

    def supports(self, source_uri: str, source_type: str) -> bool:
        if source_type != SOURCE_TYPE_FILE:
            return False
        parsed = urlparse(source_uri)
        return parsed.scheme not in ("http", "https")

    def extract(
        self,
        source_uri: str,
        source_type: str,
        options: ExtractOptions | None = None,
    ) -> RawContent:
        path = Path(source_uri)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {source_uri}")
        if not path.is_file():
            raise ValueError(f"Path is not a file: {source_uri}")

        ext = path.suffix.lower()
        media_type = (
            _EXTENSION_MEDIA_TYPES.get(ext)
            or mimetypes.guess_type(str(path))[0]
            or "application/octet-stream"
        )

        if media_type in _BINARY_MEDIA_TYPES:
            return RawContent(
                source_uri=source_uri,
                resolved_uri=source_uri,
                source_type=source_type,
                media_type=media_type,
                data=b"",
                charset="utf-8",
                local_path=path,
                persisted_path=None,
            )

        data = path.read_bytes()
        return RawContent(
            source_uri=source_uri,
            resolved_uri=source_uri,
            source_type=source_type,
            media_type=media_type,
            data=data,
            charset="utf-8",
            local_path=path,
            persisted_path=None,
        )
