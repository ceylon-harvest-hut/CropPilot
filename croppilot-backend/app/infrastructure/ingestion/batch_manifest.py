"""Parse batch-ingest manifest files and build entries from HTML directories."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from app.shared.document.source_types import SOURCE_TYPE_FILE, infer_source_type


@dataclass(frozen=True)
class ManifestEntry:
    source_uri: str
    crop_name: str
    source_type: str | None = None

    def resolved_source_type(self) -> str:
        return self.source_type or infer_source_type(self.source_uri)


def crop_name_from_dea_html_filename(filename: str) -> str:
    """Derive a display crop name from a DEA snapshot HTML filename."""
    stem = Path(filename).stem
    slug = stem.removeprefix("dea-gov-lk-") if stem.startswith("dea-gov-lk-") else stem
    return " ".join(part.capitalize() for part in slug.split("-") if part)


def parse_manifest(manifest_path: Path) -> list[ManifestEntry]:
    """Parse a manifest file: ``path_or_uri,crop_name[,source_type]`` per line."""
    manifest_path = manifest_path.resolve()
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    entries: list[ManifestEntry] = []
    for line_no, raw_line in enumerate(manifest_path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 2:
            raise ValueError(
                f"{manifest_path}:{line_no}: expected path_or_uri,crop_name[,source_type]"
            )

        source_uri = _resolve_source_uri(parts[0], base_dir=manifest_path.parent)
        crop_name = parts[1]
        if not crop_name:
            raise ValueError(f"{manifest_path}:{line_no}: crop_name is required")

        source_type = parts[2] if len(parts) > 2 and parts[2] else None
        entries.append(
            ManifestEntry(
                source_uri=source_uri,
                crop_name=crop_name,
                source_type=source_type,
            )
        )

    if not entries:
        raise ValueError(f"No entries found in manifest: {manifest_path}")

    return entries


def entries_from_html_dir(html_dir: Path) -> list[ManifestEntry]:
    """Build manifest entries from ``*.html`` files in a directory."""
    html_dir = html_dir.resolve()
    if not html_dir.is_dir():
        raise NotADirectoryError(f"HTML directory not found: {html_dir}")

    html_files = sorted(html_dir.glob("*.html"))
    if not html_files:
        raise ValueError(f"No HTML files found in: {html_dir}")

    return [
        ManifestEntry(
            source_uri=str(path.resolve()),
            crop_name=crop_name_from_dea_html_filename(path.name),
            source_type=SOURCE_TYPE_FILE,
        )
        for path in html_files
    ]


def _resolve_source_uri(raw_uri: str, base_dir: Path) -> str:
    parsed = urlparse(raw_uri)
    if parsed.scheme in ("http", "https"):
        return raw_uri

    path = Path(raw_uri)
    if not path.is_absolute():
        path = (base_dir / path).resolve()
    else:
        path = path.resolve()
    return str(path)
