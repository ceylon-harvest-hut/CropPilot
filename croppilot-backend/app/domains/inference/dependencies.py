from fastapi import Depends

from app.domains.inference.service import InferenceService
from app.infrastructure.config import Settings, get_settings
from app.infrastructure.factories import build_inference_service


def get_inference_service(
    settings: Settings = Depends(get_settings),
) -> InferenceService:
    return build_inference_service(settings)
