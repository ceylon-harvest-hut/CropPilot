from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from app.domains.graph.data import ExtractedCropKnowledge


def _to_json_value(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if is_dataclass(value) and not isinstance(value, type):
        return {key: _to_json_value(item) for key, item in asdict(value).items()}
    if isinstance(value, list):
        return [_to_json_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_json_value(item) for key, item in value.items()}
    return value


def extracted_crop_knowledge_to_dict(extracted: ExtractedCropKnowledge) -> dict[str, Any]:
    return _to_json_value(extracted)
