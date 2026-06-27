"""FastEmbed model cache validation.

Validates that required model files exist on disk before attempting to
construct a TextEmbedding instance.  Raises ``ModelCacheError`` with an
actionable message so failures are caught at startup rather than on the
first user request.

FastEmbed stores models in a Hugging Face hub-style layout::

    <cache_dir>/
      models--<org>--<repo>/
        snapshots/
          <revision-hash>/
            model.onnx
            model.onnx_data   ← also required for e5-large
            tokenizer.json
            …
        blobs/
          <sha256>            ← actual data; snapshots/ contain symlinks
        refs/
          main                ← points to current revision hash

The snapshot directory is what ONNX Runtime actually loads.  The ``blobs/``
directory holds the real bytes; ``snapshots/`` entries are normally symlinks.
If *only* ``blobs/`` exist (no ``snapshots/``), the download was incomplete.
"""

from __future__ import annotations

import os
from pathlib import Path

from app.infrastructure.embedders.catalog import EmbedderOption


class ModelCacheError(RuntimeError):
    """Raised when the local FastEmbed model cache is missing or incomplete.

    The message always includes the corrective action to take.
    """


def _hf_repo_dir(cache_dir: Path, hf_cache_repo: str) -> Path:
    """Return the HF-style repo directory name for *hf_cache_repo*."""
    slug = hf_cache_repo.replace("/", "--")
    return cache_dir / f"models--{slug}"


def _latest_snapshot(repo_dir: Path) -> Path | None:
    """Return the active snapshot directory (the one pointed to by refs/main)."""
    refs_main = repo_dir / "refs" / "main"
    if refs_main.exists():
        revision = refs_main.read_text().strip()
        snapshot = repo_dir / "snapshots" / revision
        if snapshot.exists():
            return snapshot

    snapshots_dir = repo_dir / "snapshots"
    if snapshots_dir.exists():
        children = sorted(snapshots_dir.iterdir())
        if children:
            return children[-1]

    return None


def validate_model_cache(cache_dir: Path, option: EmbedderOption) -> Path:
    """Validate that *option*'s ONNX files are present inside *cache_dir*.

    Returns the snapshot directory path on success.
    Raises ``ModelCacheError`` with a specific, actionable message otherwise.
    """
    if not option.hf_cache_repo:
        # No repo metadata — skip validation (useful for custom models).
        return cache_dir

    # 1. Cache root must exist.
    if not cache_dir.exists():
        raise ModelCacheError(
            f"FastEmbed cache directory does not exist: {cache_dir}\n"
            "Run:  python scripts/bootstrap_models.py --download"
        )

    # 2. Per-model repo directory must exist.
    repo_dir = _hf_repo_dir(cache_dir, option.hf_cache_repo)
    if not repo_dir.exists():
        raise ModelCacheError(
            f"Model '{option.name}' ({option.model_name}) has not been bootstrapped.\n"
            f"Expected directory: {repo_dir}\n"
            "Run:  python scripts/bootstrap_models.py --download"
        )

    # 3. A completed snapshot directory must exist.
    snapshot = _latest_snapshot(repo_dir)
    if snapshot is None:
        raise ModelCacheError(
            f"Model '{option.name}' has no completed snapshot in {repo_dir}.\n"
            "The download was likely interrupted.\n"
            f"Fix:  rm -rf {repo_dir}\n"
            "Then: python scripts/bootstrap_models.py --download"
        )

    # 4. All required files must be present and non-empty.
    missing: list[str] = []
    empty: list[str] = []
    for rel in option.required_files:
        # Resolve symlinks — snapshot entries are symlinks pointing into blobs/
        file_path = snapshot / rel
        if not file_path.exists():
            missing.append(rel)
            continue
        try:
            if file_path.stat().st_size == 0:
                empty.append(rel)
        except OSError:
            missing.append(rel)

    if missing:
        raise ModelCacheError(
            f"Model '{option.name}' is missing required file(s) in {snapshot}:\n"
            + "".join(f"  - {f}\n" for f in missing)
            + "The download was likely interrupted or the cache is corrupt.\n"
            f"Fix:  rm -rf {repo_dir}\n"
            "Then: python scripts/bootstrap_models.py --download"
        )

    if empty:
        raise ModelCacheError(
            f"Model '{option.name}' has zero-byte (corrupt) file(s) in {snapshot}:\n"
            + "".join(f"  - {f}\n" for f in empty)
            + f"Fix:  rm -rf {repo_dir}\n"
            "Then: python scripts/bootstrap_models.py --download"
        )

    return snapshot


def resolve_cache_dir(raw: str) -> Path:
    """Resolve *raw* (from ``Settings.fastembed_cache_dir``) to an absolute path.

    Relative paths are resolved from the current working directory, which for
    the backend is ``croppilot-backend/``.  Always use this helper instead of
    ``Path(raw)`` directly so Docker absolute paths and local relative paths
    both work correctly.
    """
    p = Path(raw)
    if not p.is_absolute():
        p = (Path(os.getcwd()) / p).resolve()
    return p
