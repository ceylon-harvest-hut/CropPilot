from __future__ import annotations

from dataclasses import dataclass

from app.domains.ingestion.source_types import ALL_SOURCE_TYPES


@dataclass(frozen=True)
class LoaderOption:
    name: str
    label: str
    source_types: tuple[str, ...]


_LOADER_OPTIONS: tuple[LoaderOption, ...] = (
    LoaderOption(name="text", label="Plain text file", source_types=("file",)),
    LoaderOption(
        name="docling",
        label="Docling (PDF, HTML, DOCX, TXT)",
        source_types=("file",),
    ),
    LoaderOption(name="web", label="Web page", source_types=("web_url",)),
)


def list_loader_options() -> list[LoaderOption]:
    return list(_LOADER_OPTIONS)


def list_source_types() -> list[str]:
    return list(ALL_SOURCE_TYPES)


def loaders_for_source_type(source_type: str) -> list[str]:
    return [
        option.name
        for option in _LOADER_OPTIONS
        if source_type in option.source_types
    ]
