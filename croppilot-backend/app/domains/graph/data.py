from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GraphIngestArtifacts:
    """Optional on-disk artifacts produced during graph ingestion."""

    html_output_path: Path | None = None
    json_output_path: Path | None = None


@dataclass
class GraphIngestResult:
    source_id: int
    crop_name: str
    status: str
    replaced: bool = False
    html_path: Path | None = None
    json_path: Path | None = None
