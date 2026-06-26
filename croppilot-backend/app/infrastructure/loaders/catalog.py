from __future__ import annotations

from dataclasses import dataclass

from app.domains.ingestion.source_types import ALL_SOURCE_TYPES


@dataclass(frozen=True)
class LoaderOption:
    name: str
    label: str
    source_types: tuple[str, ...]


_LOADER_OPTIONS: tuple[LoaderOption, ...] = (
    LoaderOption(
        name="text",
        label="Plain text / Markdown",
        source_types=("file", "web_url"),
    ),
    LoaderOption(
        name="docling",
        label="Docling (PDF, HTML, DOCX, …)",
        source_types=("file", "web_url"),
    ),
    LoaderOption(
        name="html_plain",
        label="HTML (plain text)",
        source_types=("file", "web_url"),
    ),
    LoaderOption(
        name="dea_gov_lk",
        label="DEA gov.lk crop page",
        source_types=("file", "web_url"),
    ),
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
