"""Unit tests for the embedder catalog."""

from app.infrastructure.embedders.catalog import (
    EmbedderOption,
    get_embedder_option,
    list_embedder_names,
    list_embedder_options,
)


def test_catalog_contains_both_embedders() -> None:
    names = list_embedder_names()
    assert "bge_small" in names
    assert "e5_multilingual" in names


def test_catalog_options_are_embedder_option_instances() -> None:
    options = list_embedder_options()
    assert all(isinstance(o, EmbedderOption) for o in options)


def test_bge_small_dimensions() -> None:
    options = {o.name: o for o in list_embedder_options()}
    assert options["bge_small"].dimensions == 384
    assert "bge-small" in options["bge_small"].model_name.lower()


def test_e5_multilingual_dimensions() -> None:
    options = {o.name: o for o in list_embedder_options()}
    assert options["e5_multilingual"].dimensions == 1024
    assert "e5" in options["e5_multilingual"].model_name.lower()


def test_all_options_have_hf_cache_repo() -> None:
    for opt in list_embedder_options():
        assert opt.hf_cache_repo, f"{opt.name} missing hf_cache_repo"


def test_all_options_have_required_files() -> None:
    for opt in list_embedder_options():
        assert opt.required_files, f"{opt.name} missing required_files"


def test_e5_required_files_include_onnx_data() -> None:
    opt = get_embedder_option("e5_multilingual")
    assert "model.onnx_data" in opt.required_files


def test_get_embedder_option_unknown_raises() -> None:
    import pytest

    with pytest.raises(ValueError, match="Unknown embedder"):
        get_embedder_option("nonexistent")

