from __future__ import annotations

from typing import Literal
from urllib.parse import urlparse

SOURCE_TYPE_FILE = "file"
SOURCE_TYPE_WEB_URL = "web_url"

SourceType = Literal["file", "web_url"]

ALL_SOURCE_TYPES: tuple[str, ...] = (SOURCE_TYPE_FILE, SOURCE_TYPE_WEB_URL)


def infer_source_type(source_uri: str) -> SourceType:
    parsed = urlparse(source_uri)
    if parsed.scheme in ("http", "https"):
        return SOURCE_TYPE_WEB_URL
    return SOURCE_TYPE_FILE


def validate_source_uri_shape(source_uri: str, source_type: str) -> None:
    parsed = urlparse(source_uri)
    if source_type == SOURCE_TYPE_WEB_URL:
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError(
                f"source_uri must be an http(s) URL when source_type is {SOURCE_TYPE_WEB_URL!r}"
            )
        return

    if source_type == SOURCE_TYPE_FILE:
        if parsed.scheme in ("http", "https"):
            raise ValueError(
                f"source_uri must be a file path when source_type is {SOURCE_TYPE_FILE!r}"
            )
        return

    raise ValueError(f"Unknown source_type: {source_type!r}")
