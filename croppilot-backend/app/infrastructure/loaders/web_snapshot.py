from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.domains.ingestion.content import ExtractOptions, LoaderOptions
from app.domains.ingestion.source_types import SOURCE_TYPE_FILE, SOURCE_TYPE_WEB_URL

MANIFEST_VERSION = 1
MANIFEST_FILENAME = "manifest.json"


@dataclass(frozen=True)
class SnapshotFiles:
    url: str
    final_url: str
    content_type: str
    html_path: Path
    md_path: Path
    markdown_text: str
    char_count: int


@dataclass
class ManifestEntry:
    id: str
    url: str
    final_url: str
    content_type: str
    html_path: str
    md_path: str
    fetched_at: str
    status: str
    error: str | None = None
    char_count: int | None = None


def slug_from_url(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.replace(".", "-")
    path_part = parsed.path.strip("/").replace("/", "-")
    slug = f"{host}-{path_part}" if path_part else host
    slug = slug.lower()
    slug = re.sub(r"[^\w\-]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "index"


def snapshot_url_to_files(
    url: str,
    html_path: Path,
    md_path: Path,
    *,
    fetch: bool = True,
    final_url: str | None = None,
    content_type: str | None = None,
    timeout_seconds: int | None = None,
) -> SnapshotFiles:
    from app.infrastructure.extractors.http_extractor import DEFAULT_TIMEOUT_SECONDS
    from app.infrastructure.extractors.registry import ExtractorRegistry, build_all_extractors
    from app.infrastructure.loaders.registry import DocumentLoaderRegistry, build_all_loaders
    from app.domains.ingestion.pipeline import DocumentPipeline

    pipeline = DocumentPipeline(
        extractors=ExtractorRegistry(build_all_extractors()),
        loaders=DocumentLoaderRegistry(build_all_loaders()),
    )

    loader_opts = LoaderOptions(persist=True, output_path=md_path)

    if fetch:
        timeout = timeout_seconds if timeout_seconds is not None else DEFAULT_TIMEOUT_SECONDS
        extract_opts = ExtractOptions(
            persist_raw=True,
            raw_output_path=html_path,
            timeout_seconds=timeout,
        )
        raw = pipeline.extract(url, SOURCE_TYPE_WEB_URL, extract_opts)
        resolved_final_url = raw.resolved_uri
        resolved_content_type = raw.media_type
    else:
        if not html_path.is_file():
            raise FileNotFoundError(f"HTML file not found: {html_path}")
        raw = pipeline.extract(str(html_path), SOURCE_TYPE_FILE)
        resolved_final_url = final_url or url
        resolved_content_type = content_type or "text/html"

    docs = pipeline.load_from_raw(raw, "docling", loader_opts)

    md_text = "\n\n".join(d.text for d in docs)

    return SnapshotFiles(
        url=url,
        final_url=resolved_final_url,
        content_type=resolved_content_type,
        html_path=html_path,
        md_path=md_path,
        markdown_text=md_text,
        char_count=len(md_text),
    )


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def parse_urls_file(path: Path) -> list[str]:
    urls: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        urls.append(stripped)
    return urls


def load_manifest(manifest_path: Path) -> dict[str, Any]:
    if not manifest_path.is_file():
        return {
            "version": MANIFEST_VERSION,
            "collection_dir": str(manifest_path.parent),
            "updated_at": utc_now_iso(),
            "entries": [],
        }
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if "entries" not in data:
        data["entries"] = []
    return data


def save_manifest(
    manifest_path: Path,
    collection_dir: Path,
    entries: list[ManifestEntry],
) -> None:
    payload = {
        "version": MANIFEST_VERSION,
        "collection_dir": str(collection_dir.resolve()),
        "updated_at": utc_now_iso(),
        "entries": [asdict(entry) for entry in entries],
    }
    manifest_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def entry_for_snapshot(
    snapshot: SnapshotFiles,
    collection_dir: Path,
    *,
    entry_id: str,
    fetched_at: str,
) -> ManifestEntry:
    return ManifestEntry(
        id=entry_id,
        url=snapshot.url,
        final_url=snapshot.final_url,
        content_type=snapshot.content_type,
        html_path=str(snapshot.html_path.relative_to(collection_dir)),
        md_path=str(snapshot.md_path.relative_to(collection_dir)),
        fetched_at=fetched_at,
        status="ok",
        char_count=snapshot.char_count,
    )


def error_entry(
    url: str,
    *,
    entry_id: str,
    fetched_at: str,
    error: str,
) -> ManifestEntry:
    return ManifestEntry(
        id=entry_id,
        url=url,
        final_url=url,
        content_type="",
        html_path="",
        md_path="",
        fetched_at=fetched_at,
        status="error",
        error=error,
    )
