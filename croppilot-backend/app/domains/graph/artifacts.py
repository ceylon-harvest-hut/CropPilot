from __future__ import annotations

import json
import shutil
from pathlib import Path

from app.domains.graph.schemas import ExtractedCropKnowledge


def save_extraction_json(extracted: ExtractedCropKnowledge, json_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    payload = extracted.model_dump(mode="json")
    json_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def copy_file_html_to_artifact(source_uri: str, html_output_path: Path) -> bool:
    source_path = Path(source_uri)
    if source_path.suffix.lower() not in (".html", ".htm"):
        return False
    if not source_path.is_file():
        return False
    html_output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, html_output_path)
    return True
