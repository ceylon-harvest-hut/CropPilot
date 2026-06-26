#!/usr/bin/env python3
"""Fetch URLs and save HTML + Markdown snapshots with a JSON manifest."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app.infrastructure.extractors.http_extractor import DEFAULT_TIMEOUT_SECONDS  # noqa: E402
from app.infrastructure.loaders.web_snapshot import (  # noqa: E402
    MANIFEST_FILENAME,
    ManifestEntry,
    entry_for_snapshot,
    error_entry,
    load_manifest,
    parse_urls_file,
    save_manifest,
    slug_from_url,
    snapshot_url_to_files,
    utc_now_iso,
)

DEFAULT_COLLECTION_DIR = REPO_ROOT / "data" / "web_collection"
DEFAULT_URLS_FILE = "urls.txt"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch web URLs and build an HTML + Markdown document collection.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_COLLECTION_DIR,
        help=f"Collection root directory (default: {DEFAULT_COLLECTION_DIR})",
    )
    parser.add_argument(
        "--urls-file",
        type=Path,
        default=None,
        help=f"File with one URL per line (default: <output-dir>/{DEFAULT_URLS_FILE})",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-fetch and overwrite existing HTML/Markdown files",
    )
    parser.add_argument(
        "--md-only",
        action="store_true",
        help="Skip fetch; regenerate Markdown from saved HTML files",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Seconds to wait between URL fetches (default: 1.0)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        metavar="SECONDS",
        help=f"HTTP fetch timeout per URL (default: {DEFAULT_TIMEOUT_SECONDS})",
    )
    return parser


def entries_by_url(entries: list[dict]) -> dict[str, dict]:
    return {entry["url"]: entry for entry in entries}


def should_skip(
    url: str,
    html_path: Path,
    md_path: Path,
    *,
    force: bool,
    md_only: bool,
) -> bool:
    if force:
        return False
    if md_only:
        return not html_path.is_file()
    return html_path.is_file() and md_path.is_file()


def main() -> int:
    args = build_parser().parse_args()
    collection_dir = args.output_dir.resolve()
    urls_file = args.urls_file or (collection_dir / DEFAULT_URLS_FILE)
    manifest_path = collection_dir / MANIFEST_FILENAME

    if not urls_file.is_file():
        print(f"URLs file not found: {urls_file}", file=sys.stderr)
        return 1

    collection_dir.mkdir(parents=True, exist_ok=True)
    (collection_dir / "html").mkdir(exist_ok=True)
    (collection_dir / "md").mkdir(exist_ok=True)

    urls = parse_urls_file(urls_file)
    if not urls:
        print(f"No URLs found in {urls_file}", file=sys.stderr)
        return 1

    manifest = load_manifest(manifest_path)
    existing = entries_by_url(manifest.get("entries", []))
    updated_entries: dict[str, ManifestEntry] = {
        url: ManifestEntry(**entry) for url, entry in existing.items()
    }

    ok_count = 0
    skip_count = 0
    error_count = 0

    for index, url in enumerate(urls):
        entry_id = slug_from_url(url)
        html_path = collection_dir / "html" / f"{entry_id}.html"
        md_path = collection_dir / "md" / f"{entry_id}.md"

        if should_skip(url, html_path, md_path, force=args.force, md_only=args.md_only):
            print(f"[skip] {url}")
            skip_count += 1
            continue

        fetched_at = utc_now_iso()
        print(f"[{index + 1}/{len(urls)}] {url}")

        prior = existing.get(url, {})
        try:
            snapshot = snapshot_url_to_files(
                url,
                html_path,
                md_path,
                fetch=not args.md_only,
                final_url=prior.get("final_url"),
                content_type=prior.get("content_type") or None,
                timeout_seconds=args.timeout,
            )
            updated_entries[url] = entry_for_snapshot(
                snapshot,
                collection_dir,
                entry_id=entry_id,
                fetched_at=fetched_at,
            )
            ok_count += 1
            print(f"  -> {updated_entries[url].md_path} ({snapshot.char_count} chars)")
        except Exception as exc:  # noqa: BLE001 — batch script records per-URL failures
            updated_entries[url] = error_entry(
                url,
                entry_id=entry_id,
                fetched_at=fetched_at,
                error=str(exc),
            )
            error_count += 1
            print(f"  !! {exc}", file=sys.stderr)

        save_manifest(manifest_path, collection_dir, list(updated_entries.values()))

        if not args.md_only and index < len(urls) - 1 and args.delay > 0:
            time.sleep(args.delay)

    print()
    print(f"Collection: {collection_dir}")
    print(f"Manifest:   {manifest_path}")
    print(f"Done: {ok_count} ok, {skip_count} skipped, {error_count} errors")
    return 0 if error_count == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
