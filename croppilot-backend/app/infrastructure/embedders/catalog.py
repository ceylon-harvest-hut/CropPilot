"""Embedder option registry — mirrors loaders/catalog.py and chunkers/catalog.py."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class EmbedderOption:
    name: str
    label: str
    model_name: str
    dimensions: int
    # Hugging Face repo whose snapshot FastEmbed stores under cache_dir.
    # Used by cache validation to find the right subdirectory.
    hf_cache_repo: str = ""
    # Files that MUST exist inside the snapshot directory for the model to load.
    # Relative to the snapshot root (e.g. "model.onnx", "model.onnx_data").
    required_files: tuple[str, ...] = field(default_factory=tuple)


_EMBEDDER_OPTIONS: tuple[EmbedderOption, ...] = (
    EmbedderOption(
        name="bge_small",
        label="FastEmbed BGE small (EN, 384 dims)",
        model_name="BAAI/bge-small-en-v1.5",
        dimensions=384,
        hf_cache_repo="qdrant/bge-small-en-v1.5-onnx-q",
        required_files=("onnx/model.onnx",),
    ),
    EmbedderOption(
        name="e5_multilingual",
        label="FastEmbed E5 multilingual (1024 dims)",
        model_name="intfloat/multilingual-e5-large",
        dimensions=1024,
        hf_cache_repo="qdrant/multilingual-e5-large-onnx",
        required_files=("model.onnx", "model.onnx_data"),
    ),
)


def list_embedder_options() -> list[EmbedderOption]:
    return list(_EMBEDDER_OPTIONS)


def list_embedder_names() -> list[str]:
    return [option.name for option in _EMBEDDER_OPTIONS]


def get_embedder_option(name: str) -> EmbedderOption:
    for option in _EMBEDDER_OPTIONS:
        if option.name == name:
            return option
    raise ValueError(
        f"Unknown embedder: {name!r}. Available: {', '.join(list_embedder_names())}"
    )
