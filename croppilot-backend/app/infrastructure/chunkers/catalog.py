from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChunkerOption:
    name: str
    label: str


_CHUNKER_OPTIONS: tuple[ChunkerOption, ...] = (
    ChunkerOption(name="section", label="Section headers"),
    ChunkerOption(name="recursive", label="Recursive (size / overlap)"),
    ChunkerOption(name="dea_gov_lk", label="DEA gov.lk crop page"),
    ChunkerOption(name="manual", label="Manual selection"),
)


def list_chunker_options() -> list[ChunkerOption]:
    return list(_CHUNKER_OPTIONS)


def list_chunker_names() -> list[str]:
    return [option.name for option in _CHUNKER_OPTIONS]
