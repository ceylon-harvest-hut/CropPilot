#!/usr/bin/env python3
"""Ingest a single document into the Neo4j crop knowledge graph."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.domains.graph.persistence import SourceAlreadyGraphIngestedError  # noqa: E402
from app.infrastructure.config import get_settings  # noqa: E402
from app.infrastructure.extractors.http_extractor import DEFAULT_TIMEOUT_SECONDS  # noqa: E402
from app.infrastructure.factories import build_graph_ingestion_service  # noqa: E402
from app.infrastructure.graph.graph_collection import (  # noqa: E402
    ensure_graph_collection_dirs,
    record_graph_manifest_error,
    record_graph_manifest_success,
    resolve_graph_artifacts,
)
from app.infrastructure.loaders.catalog import list_loader_options  # noqa: E402
from app.infrastructure.repositories.db import (  # noqa: E402
    Base,
    KNOWLEDGE_SOURCE_STATUS_GRAPH_INDEXED,
    init_db,
)
from app.infrastructure.repositories.knowledge_source_repo import (  # noqa: E402
    SqlKnowledgeSourceRepository,
)
from app.shared.document.content import ExtractOptions  # noqa: E402
from app.shared.document.source_types import infer_source_type  # noqa: E402

DEFAULT_COLLECTION_DIR = REPO_ROOT / "data" / "web_collection"


def build_parser() -> argparse.ArgumentParser:
    loader_names = [opt.name for opt in list_loader_options()]
    parser = argparse.ArgumentParser(
        description="Graph ingest a document: extract → load → LLM extract → Neo4j.",
    )
    parser.add_argument(
        "--source-uri",
        required=True,
        help="File path or http(s) URL of the source document",
    )
    parser.add_argument(
        "--crop-name",
        required=True,
        help="Crop name (canonical key for the graph Crop node)",
    )
    parser.add_argument(
        "--loader",
        required=True,
        choices=loader_names,
        help="Document loader to use",
    )
    parser.add_argument(
        "--source-type",
        choices=["file", "web_url"],
        default=None,
        help="Override inferred source type",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace existing graph data when source URI was already graph-ingested",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Exit 0 without changes when source is already GRAPH_INDEXED",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        metavar="SECONDS",
        help=f"HTTP fetch timeout for web URLs (default: {DEFAULT_TIMEOUT_SECONDS})",
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


def main() -> int:
    args = build_parser().parse_args()

    if args.replace and args.skip_existing:
        print("Use only one of --replace or --skip-existing.", file=sys.stderr)
        return 1

    settings = get_settings()
    init_db()

    engine = create_engine(settings.database_url)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()

    source_repository = SqlKnowledgeSourceRepository(session)
    service = None

    try:
        if args.skip_existing and not args.replace:
            existing = source_repository.find_by_origin_url(args.source_uri)
            if existing is not None and existing.status == KNOWLEDGE_SOURCE_STATUS_GRAPH_INDEXED:
                print(
                    json.dumps(
                        {
                            "outcome": "skipped",
                            "source_id": existing.source_id,
                            "status": existing.status,
                            "message": "already graph-ingested",
                        },
                        indent=2,
                    )
                )
                return 0

        service = build_graph_ingestion_service(settings, session)
        extract_options = ExtractOptions(timeout_seconds=args.timeout)
        artifacts = None
        if args.save_artifacts:
            ensure_graph_collection_dirs(args.collection_dir)
            artifacts = resolve_graph_artifacts(args.collection_dir, args.source_uri)

        result = service.ingest(
            args.source_uri,
            args.crop_name,
            source_type=args.source_type,
            loader=args.loader,
            replace_existing=args.replace,
            extract_options=extract_options,
            artifacts=artifacts,
        )

        if args.save_artifacts:
            record_graph_manifest_success(
                args.collection_dir,
                source_uri=args.source_uri,
                crop_name=args.crop_name,
                loader=args.loader,
                html_path=result.html_path,
                json_path=result.json_path,
                source_id=result.source_id,
                graph_status=result.status,
            )

        payload = {
            "outcome": "ok",
            "source_id": result.source_id,
            "crop_name": result.crop_name,
            "status": result.status,
            "replaced": result.replaced,
            "source_type": args.source_type or infer_source_type(args.source_uri),
        }
        if args.save_artifacts:
            payload["html_path"] = str(result.html_path or "")
            payload["json_path"] = str(result.json_path or "")
        print(json.dumps(payload, indent=2))
        return 0
    except SourceAlreadyGraphIngestedError as exc:
        print(
            json.dumps(
                {
                    "outcome": "error",
                    "message": str(exc),
                    "source_id": exc.source_id,
                    "status": exc.status,
                },
                indent=2,
            ),
            file=sys.stderr,
        )
        return 2
    except Exception as exc:
        if args.save_artifacts:
            artifacts = resolve_graph_artifacts(args.collection_dir, args.source_uri)
            record_graph_manifest_error(
                args.collection_dir,
                source_uri=args.source_uri,
                crop_name=args.crop_name,
                loader=args.loader,
                error=str(exc),
                html_path=artifacts.html_output_path,
                json_path=artifacts.json_output_path,
            )
        print(json.dumps({"outcome": "error", "message": str(exc)}, indent=2), file=sys.stderr)
        return 2
    finally:
        if service is not None:
            service.close()
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
