#!/usr/bin/env python
"""Bootstrap FastEmbed ONNX models into the permanent cache.

Run this ONCE after clone (local dev) or during ``docker build`` (production).
The app will refuse to start if the required files are absent.

Usage
-----
Download the model(s) configured in .env / Settings::

    conda activate rag_env
    python scripts/bootstrap_models.py --download

Verify an existing cache without downloading::

    python scripts/bootstrap_models.py --verify-only

Restrict to a single backend::

    python scripts/bootstrap_models.py --download --backend e5_multilingual

Docker build example
---------------------
    ENV FASTEMBED_CACHE_DIR=/app/models/fastembed
    ENV ALLOW_MODEL_DOWNLOAD=true
    RUN python scripts/bootstrap_models.py --download
    ENV ALLOW_MODEL_DOWNLOAD=false
    ENV HF_HUB_OFFLINE=true

Or copy a pre-downloaded cache and only verify::

    COPY models/fastembed/ /app/models/fastembed/
    RUN python scripts/bootstrap_models.py --verify-only
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Resolve the package root so this script can be run from any working directory.
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from app.infrastructure.embedders.cache import ModelCacheError, resolve_cache_dir, validate_model_cache  # noqa: E402
from app.infrastructure.embedders.catalog import EmbedderOption, get_embedder_option, list_embedder_options  # noqa: E402
from app.infrastructure.config import get_settings  # noqa: E402


def _download_model(option: EmbedderOption, cache_dir: Path) -> None:
    """Trigger FastEmbed to download *option* into *cache_dir*."""
    from fastembed import TextEmbedding

    print(f"  Downloading {option.model_name!r} → {cache_dir} …")
    TextEmbedding(
        model_name=option.model_name,
        cache_dir=str(cache_dir),
    )
    print(f"  Done: {option.model_name!r}")


def _verify(option: EmbedderOption, cache_dir: Path) -> None:
    snapshot = validate_model_cache(cache_dir, option)
    sizes = {
        f: (snapshot / f).stat().st_size
        for f in option.required_files
        if (snapshot / f).exists()
    }
    total_mb = sum(sizes.values()) / (1024 ** 2)
    print(f"  OK  {option.model_name!r}  ({total_mb:.0f} MB in snapshot)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--download", action="store_true", help="Download model(s) then verify.")
    group.add_argument("--verify-only", action="store_true", help="Only verify; never download.")
    parser.add_argument(
        "--backend",
        default=None,
        help=(
            "Restrict to a single backend name (e.g. e5_multilingual). "
            "Defaults to the backend configured in .env / Settings."
        ),
    )
    args = parser.parse_args()

    settings = get_settings()
    cache_dir = resolve_cache_dir(settings.fastembed_cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    print(f"FastEmbed cache directory: {cache_dir}")

    if args.backend:
        try:
            options = [get_embedder_option(args.backend)]
        except ValueError as exc:
            parser.error(str(exc))
    else:
        # Default: only bootstrap the backend that is currently configured.
        options = [get_embedder_option(settings.embedding_backend)]

    failed: list[str] = []

    for option in options:
        print(f"\n[{option.name}] {option.model_name}")

        if args.download:
            try:
                _download_model(option, cache_dir)
            except Exception as exc:  # noqa: BLE001
                print(f"  ERROR during download: {exc}", file=sys.stderr)
                failed.append(option.name)
                continue

        try:
            _verify(option, cache_dir)
        except ModelCacheError as exc:
            print(f"  FAIL: {exc}", file=sys.stderr)
            failed.append(option.name)

    print()
    if failed:
        print(f"Bootstrap FAILED for: {', '.join(failed)}", file=sys.stderr)
        sys.exit(1)
    else:
        print("Bootstrap complete. All model(s) verified.")


if __name__ == "__main__":
    main()
