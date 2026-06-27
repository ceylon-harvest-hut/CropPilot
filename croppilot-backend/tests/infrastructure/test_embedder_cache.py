"""Unit tests for validate_model_cache and resolve_cache_dir."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.infrastructure.embedders.cache import (
    ModelCacheError,
    resolve_cache_dir,
    validate_model_cache,
)
from app.infrastructure.embedders.catalog import get_embedder_option


@pytest.fixture
def e5_option():
    return get_embedder_option("e5_multilingual")


# ── resolve_cache_dir ────────────────────────────────────────────────────────

def test_resolve_cache_dir_absolute_unchanged(tmp_path: Path) -> None:
    result = resolve_cache_dir(str(tmp_path))
    assert result == tmp_path


def test_resolve_cache_dir_relative_returns_absolute(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = resolve_cache_dir("./models/fastembed")
    assert result.is_absolute()
    assert result == (tmp_path / "models" / "fastembed").resolve()


# ── validate_model_cache — error cases ──────────────────────────────────────

def test_raises_when_cache_dir_missing(tmp_path: Path, e5_option) -> None:
    missing = tmp_path / "nonexistent"
    with pytest.raises(ModelCacheError, match="does not exist"):
        validate_model_cache(missing, e5_option)


def test_raises_when_repo_dir_missing(tmp_path: Path, e5_option) -> None:
    tmp_path.mkdir(exist_ok=True)
    with pytest.raises(ModelCacheError, match="not been bootstrapped"):
        validate_model_cache(tmp_path, e5_option)


def test_raises_when_no_snapshot(tmp_path: Path, e5_option) -> None:
    repo = tmp_path / "models--qdrant--multilingual-e5-large-onnx"
    repo.mkdir(parents=True)
    (repo / "blobs").mkdir()
    with pytest.raises(ModelCacheError, match="no completed snapshot"):
        validate_model_cache(tmp_path, e5_option)


def test_raises_when_required_file_missing(tmp_path: Path, e5_option) -> None:
    revision = "abc123"
    snapshot = tmp_path / "models--qdrant--multilingual-e5-large-onnx" / "snapshots" / revision
    snapshot.mkdir(parents=True)
    refs = tmp_path / "models--qdrant--multilingual-e5-large-onnx" / "refs"
    refs.mkdir()
    (refs / "main").write_text(revision)
    # Write only model.onnx — model.onnx_data is missing
    (snapshot / "model.onnx").write_bytes(b"fake")
    with pytest.raises(ModelCacheError, match="missing required file"):
        validate_model_cache(tmp_path, e5_option)


def test_raises_when_required_file_empty(tmp_path: Path, e5_option) -> None:
    revision = "abc123"
    snapshot = tmp_path / "models--qdrant--multilingual-e5-large-onnx" / "snapshots" / revision
    snapshot.mkdir(parents=True)
    refs = tmp_path / "models--qdrant--multilingual-e5-large-onnx" / "refs"
    refs.mkdir()
    (refs / "main").write_text(revision)
    (snapshot / "model.onnx").write_bytes(b"fake")
    (snapshot / "model.onnx_data").write_bytes(b"")  # zero-byte
    with pytest.raises(ModelCacheError, match="zero-byte"):
        validate_model_cache(tmp_path, e5_option)


# ── validate_model_cache — success path ─────────────────────────────────────

def test_returns_snapshot_when_valid(tmp_path: Path, e5_option) -> None:
    revision = "abc123"
    snapshot = tmp_path / "models--qdrant--multilingual-e5-large-onnx" / "snapshots" / revision
    snapshot.mkdir(parents=True)
    refs = tmp_path / "models--qdrant--multilingual-e5-large-onnx" / "refs"
    refs.mkdir()
    (refs / "main").write_text(revision)
    (snapshot / "model.onnx").write_bytes(b"fake_onnx")
    (snapshot / "model.onnx_data").write_bytes(b"fake_data_bytes" * 100)
    result = validate_model_cache(tmp_path, e5_option)
    assert result == snapshot


def test_falls_back_to_latest_snapshot_when_no_refs(tmp_path: Path, e5_option) -> None:
    revision = "deadbeef"
    snapshot = tmp_path / "models--qdrant--multilingual-e5-large-onnx" / "snapshots" / revision
    snapshot.mkdir(parents=True)
    # No refs/main file — should still find snapshot by directory scan
    (snapshot / "model.onnx").write_bytes(b"fake_onnx")
    (snapshot / "model.onnx_data").write_bytes(b"fake_data" * 100)
    result = validate_model_cache(tmp_path, e5_option)
    assert result == snapshot


def test_skips_validation_when_no_hf_cache_repo(tmp_path: Path) -> None:
    from app.infrastructure.embedders.catalog import EmbedderOption

    bare_option = EmbedderOption(
        name="custom",
        label="Custom",
        model_name="some/model",
        dimensions=768,
        hf_cache_repo="",
        required_files=(),
    )
    result = validate_model_cache(tmp_path, bare_option)
    assert result == tmp_path
