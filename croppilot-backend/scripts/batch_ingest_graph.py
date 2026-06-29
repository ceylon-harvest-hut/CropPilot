#!/usr/bin/env python3
"""Batch graph-ingest documents from a manifest file or HTML directory."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.shared.document.content import ExtractOptions  # noqa: E402
from app.infrastructure.config import get_settings  # noqa: E402
from app.infrastructure.extractors.http_extractor import DEFAULT_TIMEOUT_SECONDS  # noqa: E402
from app.infrastructure.factories import build_graph_ingestion_service  # noqa: E402
from app.infrastructure.graph.graph_collection import (  # noqa: E402
    GRAPH_MANIFEST_FILENAME,
    ensure_graph_collection_dirs,
)
from app.infrastructure.ingestion.batch_graph_runner import ingest_graph_manifest_entry  # noqa: E402
from app.infrastructure.ingestion.batch_manifest import (  # noqa: E402
    entries_from_html_dir,
    parse_manifest,
)
from app.infrastructure.loaders.catalog import list_loader_options  # noqa: E402
from app.infrastructure.repositories.db import Base, init_db  # noqa: E402
from app.infrastructure.repositories.knowledge_source_repo import SqlKnowledgeSourceRepository  # noqa: E402

DEFAULT_MANIFEST = REPO_ROOT / "data" / "web_collection" / "ingest_manifest_urls.txt"
DEFAULT_HTML_DIR = REPO_ROOT / "data" / "web_collection" / "html"
DEFAULT_COLLECTION_DIR = REPO_ROOT / "data" / "web_collection"


def build_parser() -> argparse.ArgumentParser:
    loader_names = [opt.name for opt in list_loader_options()]

    parser = argparse.ArgumentParser(
        description="Batch graph ingest: extract → load → LLM extract → Neo4j.",
    )
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--manifest",
        type=Path,
        help=f"Manifest file (e.g. {DEFAULT_MANIFEST})",
    )
    source_group.add_argument(
        "--html-dir",
        type=Path,
        nargs="?",
        const=DEFAULT_HTML_DIR,
        help=f"Ingest all *.html files (default dir: {DEFAULT_HTML_DIR})",
    )

    parser.add_argument(
        "--loader",
        required=True,
        choices=loader_names,
        help="Document loader to use for every entry",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace graph data when a source URI was already graph-ingested",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip entries that are already GRAPH_INDEXED instead of failing",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        metavar="SECONDS",
        help=f"HTTP fetch timeout per web URL entry (default: {DEFAULT_TIMEOUT_SECONDS})",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.0,
        help="Seconds to wait between entries when ingesting web URLs (default: 0)",
    )
    parser.add_argument(
        "--save-artifacts",
        action="store_true",
        help="Save fetched HTML and LLM JSON under the collection dir; update manifest_graph.json",
    )
    parser.add_argument(
        "--collection-dir",
        type=Path,
        default=DEFAULT_COLLECTION_DIR,
        help=f"Root for graph_html/, graph_json/, manifest_graph.json (default: {DEFAULT_COLLECTION_DIR})",
    )
    return parser


def resolve_entries(args: argparse.Namespace) -> list:
    if args.manifest is not None:
        return parse_manifest(args.manifest)

    html_dir = args.html_dir if args.html_dir is not None else DEFAULT_HTML_DIR
    return entries_from_html_dir(html_dir)


def main() -> int:
    args = build_parser().parse_args()

    if args.replace and args.skip_existing:
        print("Use only one of --replace or --skip-existing.", file=sys.stderr)
        return 1

    try:
        entries = resolve_entries(args)
    except (FileNotFoundError, NotADirectoryError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 1

    settings = get_settings()
    init_db()

    engine = create_engine(settings.database_url)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()

    service = build_graph_ingestion_service(settings, session)
    extract_options = ExtractOptions(timeout_seconds=args.timeout)
    source_repository = SqlKnowledgeSourceRepository(session)

    if args.save_artifacts:
        ensure_graph_collection_dirs(args.collection_dir)

    ok_count = 0
    skip_count = 0
    error_count = 0

    try:
        for index, entry in enumerate(entries, 1):
            print(f"[{index}/{len(entries)}] {entry.crop_name} ← {entry.source_uri}")
            result = ingest_graph_manifest_entry(
                entry,
                service=service,
                source_repository=source_repository,
                loader=args.loader,
                replace_existing=args.replace,
                skip_existing=args.skip_existing,
                extract_options=extract_options,
                collection_dir=args.collection_dir if args.save_artifacts else None,
                save_artifacts=args.save_artifacts,
            )

            if result.outcome == "ok":
                ok_count += 1
                detail = f"source_id={result.source_id}, {result.message}"
                if args.save_artifacts and (result.html_path or result.json_path):
                    detail += f", json={result.json_path or 'n/a'}"
                print(f"  -> graph indexed ({detail})")
            elif result.outcome == "skipped":
                skip_count += 1
                print(f"  [skip] {result.message}")
            else:
                error_count += 1
                print(f"  !! {result.message}", file=sys.stderr)

            if (
                args.delay > 0
                and index < len(entries)
                and entry.resolved_source_type() == "web_url"
            ):
                time.sleep(args.delay)

        print()
        print(f"Done: {ok_count} ok, {skip_count} skipped, {error_count} errors")
        if args.save_artifacts:
            print(f"Artifacts: {args.collection_dir / GRAPH_MANIFEST_FILENAME}")
        print(f"Neo4j:    {settings.neo4j_uri}")
        print(f"Database: {settings.database_url}")
        return 0 if error_count == 0 else 2
    finally:
        service.close()
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
