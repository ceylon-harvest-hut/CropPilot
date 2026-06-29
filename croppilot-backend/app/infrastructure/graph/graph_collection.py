"""Graph ingestion artifact paths and manifest_graph.json bookkeeping."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from app.domains.graph.data import GraphIngestArtifacts
from app.infrastructure.loaders.web_snapshot import slug_from_url, utc_now_iso
from app.shared.document.source_types import SOURCE_TYPE_WEB_URL, infer_source_type

GRAPH_MANIFEST_VERSION = 1
GRAPH_MANIFEST_FILENAME = "manifest_graph.json"
GRAPH_HTML_DIR = "graph_html"
GRAPH_JSON_DIR = "graph_json"


@dataclass
class GraphManifestEntry:
    id: str
    url: str
    crop_name: str
    loader: str
    html_path: str
    json_path: str
    extracted_at: str
    status: str
    error: str | None = None
    source_id: int | None = None
    graph_status: str | None = None


def entry_id_from_source_uri(source_uri: str) -> str:
    if infer_source_type(source_uri) == SOURCE_TYPE_WEB_URL:
        return slug_from_url(source_uri)
    return Path(source_uri).stem


def graph_manifest_path(collection_dir: Path) -> Path:
    return collection_dir / GRAPH_MANIFEST_FILENAME


def graph_html_path(collection_dir: Path, source_uri: str) -> Path:
    entry_id = entry_id_from_source_uri(source_uri)
    return collection_dir / GRAPH_HTML_DIR / f"{entry_id}.html"


def graph_json_path(collection_dir: Path, source_uri: str) -> Path:
    entry_id = entry_id_from_source_uri(source_uri)
    return collection_dir / GRAPH_JSON_DIR / f"{entry_id}.json"


def resolve_graph_artifacts(
    collection_dir: Path,
    source_uri: str,
    *,
    save_html: bool = True,
    save_json: bool = True,
) -> GraphIngestArtifacts:
    collection_dir = collection_dir.resolve()
    return GraphIngestArtifacts(
        html_output_path=graph_html_path(collection_dir, source_uri) if save_html else None,
        json_output_path=graph_json_path(collection_dir, source_uri) if save_json else None,
    )


def ensure_graph_collection_dirs(collection_dir: Path) -> None:
    collection_dir = collection_dir.resolve()
    collection_dir.mkdir(parents=True, exist_ok=True)
    (collection_dir / GRAPH_HTML_DIR).mkdir(exist_ok=True)
    (collection_dir / GRAPH_JSON_DIR).mkdir(exist_ok=True)


def relative_collection_path(path: Path | None, collection_dir: Path) -> str:
    if path is None:
        return ""
    try:
        return str(path.resolve().relative_to(collection_dir.resolve()))
    except ValueError:
        return str(path)


def load_graph_manifest(manifest_path: Path) -> dict[str, Any]:
    if not manifest_path.is_file():
        return {
            "version": GRAPH_MANIFEST_VERSION,
            "collection_dir": str(manifest_path.parent),
            "updated_at": utc_now_iso(),
            "entries": [],
        }
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if "entries" not in data:
        data["entries"] = []
    return data


def save_graph_manifest(
    manifest_path: Path,
    collection_dir: Path,
    entries: list[GraphManifestEntry],
) -> None:
    payload = {
        "version": GRAPH_MANIFEST_VERSION,
        "collection_dir": str(collection_dir.resolve()),
        "updated_at": utc_now_iso(),
        "entries": [asdict(entry) for entry in entries],
    }
    manifest_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def entries_by_url(entries: list[dict[str, Any]]) -> dict[str, GraphManifestEntry]:
    return {entry["url"]: GraphManifestEntry(**entry) for entry in entries}


def upsert_graph_manifest_entry(
    manifest_path: Path,
    collection_dir: Path,
    entry: GraphManifestEntry,
) -> None:
    manifest = load_graph_manifest(manifest_path)
    updated = entries_by_url(manifest.get("entries", []))
    updated[entry.url] = entry
    save_graph_manifest(manifest_path, collection_dir, list(updated.values()))


def graph_manifest_entry_for_success(
    *,
    source_uri: str,
    crop_name: str,
    loader: str,
    collection_dir: Path,
    html_path: Path | None,
    json_path: Path | None,
    source_id: int,
    graph_status: str,
    extracted_at: str | None = None,
) -> GraphManifestEntry:
    return GraphManifestEntry(
        id=entry_id_from_source_uri(source_uri),
        url=source_uri,
        crop_name=crop_name,
        loader=loader,
        html_path=relative_collection_path(html_path, collection_dir),
        json_path=relative_collection_path(json_path, collection_dir),
        extracted_at=extracted_at or utc_now_iso(),
        status="ok",
        source_id=source_id,
        graph_status=graph_status,
    )


def graph_manifest_entry_for_error(
    *,
    source_uri: str,
    crop_name: str,
    loader: str,
    collection_dir: Path,
    error: str,
    html_path: Path | None = None,
    json_path: Path | None = None,
    extracted_at: str | None = None,
) -> GraphManifestEntry:
    resolved_json = json_path if json_path is not None and json_path.is_file() else None
    return GraphManifestEntry(
        id=entry_id_from_source_uri(source_uri),
        url=source_uri,
        crop_name=crop_name,
        loader=loader,
        html_path=relative_collection_path(html_path, collection_dir),
        json_path=relative_collection_path(resolved_json, collection_dir),
        extracted_at=extracted_at or utc_now_iso(),
        status="error",
        error=error,
    )


def record_graph_manifest_success(
    collection_dir: Path,
    *,
    source_uri: str,
    crop_name: str,
    loader: str,
    html_path: Path | None,
    json_path: Path | None,
    source_id: int,
    graph_status: str,
) -> None:
    collection_dir = collection_dir.resolve()
    ensure_graph_collection_dirs(collection_dir)
    upsert_graph_manifest_entry(
        graph_manifest_path(collection_dir),
        collection_dir,
        graph_manifest_entry_for_success(
            source_uri=source_uri,
            crop_name=crop_name,
            loader=loader,
            collection_dir=collection_dir,
            html_path=html_path,
            json_path=json_path,
            source_id=source_id,
            graph_status=graph_status,
        ),
    )


def record_graph_manifest_error(
    collection_dir: Path,
    *,
    source_uri: str,
    crop_name: str,
    loader: str,
    error: str,
    html_path: Path | None = None,
    json_path: Path | None = None,
) -> None:
    collection_dir = collection_dir.resolve()
    ensure_graph_collection_dirs(collection_dir)
    upsert_graph_manifest_entry(
        graph_manifest_path(collection_dir),
        collection_dir,
        graph_manifest_entry_for_error(
            source_uri=source_uri,
            crop_name=crop_name,
            loader=loader,
            collection_dir=collection_dir,
            error=error,
            html_path=html_path if html_path is not None and html_path.is_file() else None,
            json_path=json_path,
        ),
    )
