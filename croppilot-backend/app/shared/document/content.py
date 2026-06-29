from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class RawContent:
    """Raw bytes acquired from a URI, before any format-specific parsing.

    For binary file sources (PDF, DOCX) ``data`` may be empty bytes; loaders
    should read from ``local_path`` instead.  For web sources ``local_path`` is
    None unless ``persist_raw`` was enabled on the extractor.
    """

    source_uri: str
    resolved_uri: str
    source_type: str          # file | web_url
    media_type: str
    data: bytes
    charset: str = "utf-8"
    local_path: Path | None = None       # set for file sources
    persisted_path: Path | None = None   # set when extractor persist_raw ran


@dataclass(frozen=True)
class ExtractOptions:
    """Options for the acquisition stage (extractors)."""

    timeout_seconds: int = 30
    max_bytes: int = 5 * 1024 * 1024
    persist_raw: bool = False
    raw_output_path: Path | None = None


@dataclass(frozen=True)
class LoaderOptions:
    """Options for the parsing stage (loaders)."""

    persist: bool = False
    output_path: Path | None = None
    allow_temp_files: bool = True   # Docling needs a path; temp files are always cleaned up
